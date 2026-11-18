"""留存矩阵的纯计算核心。

这里不读也不写数据仓库，只负责把「同期群定义 + 成员边界」换算成留存率。
历史留档、矩阵重建、新口径重算都走同一套函数，保证同一份输入永远得到同一份输出：

- 成员边界（成员基数 / 边界版本 / 边界种子）决定成员集合，重跑历史同期群时沿用原边界；
- 周期窗口由「时间基准 + 追踪周期 + 留存窗口」换算，不随调用方改变；
- 周期口径只有两个版本：``RET-V031`` 历史累计活跃、``RET-V032`` 滚动活跃。
"""
from __future__ import annotations

import hashlib
from datetime import date, timedelta
from typing import Any

HISTORICAL_CALIBER = "RET-V031"
CURRENT_CALIBER = "RET-V032"

CALIBER_ALGORITHMS = {
    HISTORICAL_CALIBER: "cumulative_active",
    CURRENT_CALIBER: "rolling_active",
}

UNIT_DAYS = {"日": 1, "天": 1, "week": 7, "周": 7, "month": 30, "月": 30}
DEFAULT_PERIODS = 4
MAX_PERIODS = 52


def period_unit(cohort: dict[str, Any]) -> str:
    """把追踪周期归一成 日/周/月，未知值按周处理，保持旧数据的宽松口径。"""
    raw = str(cohort.get("追踪周期") or "周").strip().lower()
    if raw in ("日", "天", "day"):
        return "日"
    if raw in ("月", "month"):
        return "月"
    return "周"


def period_days(cohort: dict[str, Any]) -> int:
    return UNIT_DAYS[period_unit(cohort)]


def period_count(cohort: dict[str, Any]) -> int:
    """留存窗口就是周期列数：解析失败时退回默认值，不改变原有输入边界。"""
    raw = cohort.get("留存窗口", DEFAULT_PERIODS)
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return DEFAULT_PERIODS
    return max(1, min(MAX_PERIODS, value))


def base_date(cohort: dict[str, Any]) -> date:
    raw = str(cohort.get("时间基准") or "").strip()
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return date(2026, 9, 1)


def period_window(cohort: dict[str, Any]) -> dict[str, Any]:
    """周期窗口的唯一换算入口：列名、日期偏移都从这里出来。"""
    unit = period_unit(cohort)
    days = period_days(cohort)
    start = base_date(cohort)
    periods = period_count(cohort)
    labels = [f"第{index}期" for index in range(1, periods + 1)]
    dates = [(start + timedelta(days=days * index)).isoformat() for index in range(1, periods + 1)]
    return {"unit": unit, "days": days, "periods": periods, "labels": labels, "dates": dates}


def member_boundary(cohort: dict[str, Any]) -> dict[str, Any]:
    """成员边界：重跑历史同期群时只认这份，不读取当前群组定义。"""
    raw_count = cohort.get("成员基数", cohort.get("样本基数", 100))
    try:
        count = max(1, min(500, int(str(raw_count).strip())))
    except (TypeError, ValueError):
        count = 100
    code = str(cohort.get("群组编号") or cohort.get("id") or "cohort")
    return {
        "成员基数": count,
        "边界版本": str(cohort.get("边界版本") or "B1"),
        "边界种子": str(cohort.get("边界种子") or f"{code}|B1"),
    }


def _bucket(seed: str, member: int, period: int) -> int:
    digest = hashlib.blake2b(f"{seed}|u{member}|p{period}".encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") % 10000


def _activity_probability(cohort_code: str, period: int) -> float:
    """同一群组同一周期的活跃概率固定，保证跨进程复现；不依赖 random。"""
    jitter = (int(hashlib.sha1(cohort_code.encode("utf-8")).hexdigest()[:4], 16) % 7 - 3) / 100
    probability = 0.74 - 0.055 * (period - 1) + jitter
    return max(0.12, min(0.9, probability))


def member_active(cohort_code: str, seed: str, member: int, period: int) -> bool:
    if period < 1:
        return False
    return _bucket(seed, member, period) / 10000 < _activity_probability(cohort_code, max(1, period))


def retained_count(
    cohort_code: str,
    seed: str,
    members: int,
    period: int,
    caliber: str,
) -> int:
    """按周期口径统计留存人数。

    历史口径 ``cumulative_active``：自首期起每个周期都活跃才算留存（旧列口径）。
    新口径 ``rolling_active``：当期或上一周期活跃即算留存（RET-V032 独立版本）。
    """
    if caliber == CURRENT_CALIBER:
        return sum(
            1
            for member in range(members)
            if member_active(cohort_code, seed, member, period)
            or member_active(cohort_code, seed, member, period - 1)
        )
    return sum(
        1
        for member in range(members)
        if all(member_active(cohort_code, seed, member, step) for step in range(1, period + 1))
    )


def retention_series(cohort: dict[str, Any], caliber: str = HISTORICAL_CALIBER) -> dict[str, Any]:
    """输出一行的留存矩阵数据：周期窗口 + 口径 + 每期留存率。"""
    window = period_window(cohort)
    boundary = member_boundary(cohort)
    code = str(cohort.get("群组编号") or cohort.get("id") or "cohort")
    values: dict[str, float] = {}
    for index, label in enumerate(window["labels"], start=1):
        count = retained_count(code, boundary["边界种子"], boundary["成员基数"], index, caliber)
        values[label] = round(count / boundary["成员基数"], 4)
    return {
        "群组编号": code,
        "群组名称": cohort.get("群组名称", ""),
        "时间基准": cohort.get("时间基准", ""),
        "追踪周期": period_unit(cohort),
        "留存窗口": window["periods"],
        "分析指标": cohort.get("分析指标", "留存率"),
        "周期口径": caliber,
        "算法": CALIBER_ALGORITHMS.get(caliber, "cumulative_active"),
        "成员边界": boundary,
        "周期列": values,
        "周期日期": dict(zip(window["labels"], window["dates"])),
    }


def historical_archive(cohorts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """构建历史留档：只算一次，作为「重构后仍复现历史结果」的基准。"""
    archive: dict[str, dict[str, Any]] = {}
    for cohort in cohorts:
        series = retention_series(cohort, HISTORICAL_CALIBER)
        archive[series["群组编号"]] = {
            "群组编号": series["群组编号"],
            "群组名称": series["群组名称"],
            "时间基准": series["时间基准"],
            "追踪周期": series["追踪周期"],
            "留存窗口": series["留存窗口"],
            "分析指标": series["分析指标"],
            "周期口径": HISTORICAL_CALIBER,
            "成员边界": series["成员边界"],
            "周期列": series["周期列"],
            "周期日期": series["周期日期"],
        }
    return archive


def matrix_row(series: dict[str, Any], *, residue: dict[str, float] | None = None) -> dict[str, Any]:
    """把留存序列摊平成矩阵数据表的一行（周期列直接作为列名）。"""
    row: dict[str, Any] = {
        "群组编号": series["群组编号"],
        "群组名称": series["群组名称"],
        "时间基准": series["时间基准"],
        "追踪周期": series["追踪周期"],
        "留存窗口": series["留存窗口"],
        "分析指标": series["分析指标"],
        "周期口径": series["周期口径"],
        "成员边界": series["成员边界"],
    }
    row.update(series["周期列"])
    if residue:
        row.update(residue)
    return row


def period_columns(row: dict[str, Any]) -> dict[str, float]:
    """只挑出真正的周期列，避免把元数据当成留存率。"""
    return {key: value for key, value in row.items() if key.startswith("第") and key.endswith("期")}


def column_period_index(column: str) -> int | None:
    text = column.strip()
    if not (text.startswith("第") and text.endswith("期")):
        return None
    try:
        return int(text[1:-1])
    except ValueError:
        return None


def find_residue(row: dict[str, Any], periods: int) -> list[str]:
    """找出超出当前留存窗口的周期列：上一次矩阵替换没清干净的残留。"""
    residue: list[str] = []
    for column in period_columns(row):
        index = column_period_index(column)
        if index is None or index < 1 or index > periods:
            residue.append(column)
    return sorted(residue, key=lambda c: column_period_index(c) or 0)


def diff_columns(
    historical: dict[str, float],
    current: dict[str, float],
) -> dict[str, dict[str, float]]:
    """同一周期列上新旧口径的差异，供「历史口径优先」方案附在矩阵行上。"""
    diff: dict[str, dict[str, float]] = {}
    for label, old in historical.items():
        if label not in current:
            continue
        diff[label] = {
            "历史口径": old,
            "新口径": current[label],
            "差异": round(current[label] - old, 4),
        }
    return diff
