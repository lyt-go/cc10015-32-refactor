"""留存矩阵与洞察结论的共用读取/重算路径。

同期群追踪和洞察报告原来各写一份「成员周期 + 指标口径」：
周期窗口、留存口径、汇总方式都重复维护，改一处要改两处。这里收拢成唯一实现，
两边只做视图投影，不再各自计算：

- 输入：同期群定义（成员边界固定）→ ``retention_core`` 周期窗口与口径；
- 输出：留存矩阵数据表（历史口径 ``RET-V031``）与 V032 独立版本表（新口径）；
- 洞察结论数据表从矩阵读取周期留存率，报告样例与关键发现都走这条读取路径。

V032 矩阵替换按事务处理：先校验未清残留，任何异常整笔回滚并进 V032 留档。
"""
from __future__ import annotations

import copy
from typing import Any

from app.retention_core import (
    CALIBER_ALGORITHMS,
    CURRENT_CALIBER,
    HISTORICAL_CALIBER,
    diff_columns,
    find_residue,
    historical_archive,
    matrix_row,
    period_columns,
    period_count,
    retention_series,
)
from app.retention_definitions import (
    COHORTS,
    CURRENT_CALIBER_EFFECTIVE_DATE,
    MATRIX_VERSION,
)
from app.retention_seed import (
    ARCHIVE_TABLE,
    CONCLUSION_TABLE,
    HISTORY_TABLE,
    MATRIX_TABLE,
    SNAPSHOT_TABLE,
    VERSION_TABLE,
    matrix_fingerprint,
)
from app.store import store

COHORT_MODULE = "cohort_track"
INSIGHT_MODULE = "insight_report"

POLICY_HISTORICAL_FIRST = "historical_first"
POLICY_RECOMPUTE = "recompute"
POLICIES = (POLICY_HISTORICAL_FIRST, POLICY_RECOMPUTE)


class RetentionError(RuntimeError):
    """留存矩阵操作被拒绝；调用方据此回滚并留档。"""


def _table(name: str) -> list[dict[str, Any]]:
    return store.rows(name)


def history_snapshot(cohorts: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """历史留档：按群组编号保存原成员边界与历史周期列，供重跑与核对使用。"""
    archive = historical_archive(cohorts or COHORTS)
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(archive.values(), start=1):
        row = {
            "id": index,
            "群组编号": item["群组编号"],
            "群组名称": item["群组名称"],
            "时间基准": item["时间基准"],
            "追踪周期": item["追踪周期"],
            "留存窗口": item["留存窗口"],
            "分析指标": item["分析指标"],
            "周期口径": HISTORICAL_CALIBER,
            "成员边界": copy.deepcopy(item["成员边界"]),
            "周期列": dict(item["周期列"]),
            "周期日期": dict(item["周期日期"]),
        }
        rows.append(row)
    return rows


def ensure_history() -> list[dict[str, Any]]:
    rows = _table(HISTORY_TABLE)
    if not rows:
        rows.extend(history_snapshot())
    return rows


def history_by_cohort() -> dict[str, dict[str, Any]]:
    return {str(row["群组编号"]): row for row in ensure_history()}


def cohort_definitions() -> list[dict[str, Any]]:
    return _table(COHORT_MODULE)


def _definition_for_history(entry: dict[str, Any]) -> dict[str, Any]:
    """用历史留档覆盖成员边界：重跑历史同期群不读取当前群组定义。"""
    return {
        "id": entry.get("id"),
        "群组编号": entry["群组编号"],
        "群组名称": entry.get("群组名称", ""),
        "时间基准": entry.get("时间基准", ""),
        "追踪周期": entry.get("追踪周期", "周"),
        "留存窗口": entry.get("留存窗口", 4),
        "分析指标": entry.get("分析指标", "留存率"),
        "成员基数": entry["成员边界"]["成员基数"],
        "边界版本": entry["成员边界"]["边界版本"],
        "边界种子": entry["成员边界"]["边界种子"],
    }


def _recompute_from_history(caliber: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, entry in enumerate(ensure_history(), start=1):
        series = retention_series(_definition_for_history(entry), caliber)
        row = {
            "id": index,
            "status": "已生效",
            "pending": False,
            "abnormal": False,
            "群组编号": series["群组编号"],
            "群组名称": series["群组名称"],
            "时间基准": series["时间基准"],
            "追踪周期": series["追踪周期"],
            "留存窗口": series["留存窗口"],
            "分析指标": series["分析指标"],
            "口径": caliber,
            "口径版本": caliber,
            "矩阵版本": MATRIX_VERSION if caliber == CURRENT_CALIBER else "V031",
            "是否历史": caliber == HISTORICAL_CALIBER,
            "残留": False,
            "生效时间": (
                CURRENT_CALIBER_EFFECTIVE_DATE
                if caliber == CURRENT_CALIBER
                else entry.get("生效时间", "2026-09-01")
            ),
        }
        row.update(matrix_row(series))
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# 读取路径：工作台（列表）与详情页都从这里取，保证同一份业务数据。
# ---------------------------------------------------------------------------


def matrix_rows(version: str = "V031", *, include_residue: bool = False) -> list[dict[str, Any]]:
    table = VERSION_TABLE if version.upper() == "V032" else MATRIX_TABLE
    rows = [copy.deepcopy(row) for row in _table(table)]
    if not include_residue:
        rows = [row for row in rows if not row.get("残留")]
    return rows


def matrix_row_for(cohort_code: str, version: str = "V031", *, include_residue: bool = False) -> dict[str, Any] | None:
    for row in matrix_rows(version, include_residue=include_residue):
        if str(row.get("群组编号")) == cohort_code:
            return row
    return None


def versions() -> list[dict[str, Any]]:
    return [
        {
            "版本": "V031",
            "口径": HISTORICAL_CALIBER,
            "算法": CALIBER_ALGORITHMS[HISTORICAL_CALIBER],
            "数据表": MATRIX_TABLE,
            "是否历史": True,
            "生效时间": "2026-09-01",
        },
        {
            "版本": MATRIX_VERSION,
            "口径": CURRENT_CALIBER,
            "算法": CALIBER_ALGORITHMS[CURRENT_CALIBER],
            "数据表": VERSION_TABLE,
            "是否历史": False,
            "生效时间": CURRENT_CALIBER_EFFECTIVE_DATE,
        },
    ]


def cohort_workbench_row(cohort: dict[str, Any], version: str = "V031") -> dict[str, Any]:
    """工作台列表行：群组定义 + 矩阵留存列，列表与详情共用。"""
    row = copy.deepcopy(cohort)
    historical = matrix_row_for(str(cohort.get("群组编号")), "V031", include_residue=False)
    if historical is not None:
        row["留存率"] = period_columns(historical)
        row["周期口径"] = historical.get("口径", HISTORICAL_CALIBER)
    if version.upper() == "V032":
        current = matrix_row_for(str(cohort.get("群组编号")), "V032")
        if current is not None:
            row["新口径留存率"] = period_columns(current)
            if historical is not None:
                row["口径差异"] = diff_columns(
                    period_columns(historical), period_columns(current)
                )
    return row


def cohort_workbench(version: str = "V031") -> list[dict[str, Any]]:
    return [cohort_workbench_row(row, version) for row in cohort_definitions()]


def cohort_detail(entry_id: int, version: str = "V031") -> dict[str, Any] | None:
    entry = store.find(COHORT_MODULE, entry_id)
    if entry is None:
        return None
    return cohort_workbench_row(entry, version)


# ---------------------------------------------------------------------------
# 洞察结论：只读矩阵，不再自行维护周期窗口与口径。
# ---------------------------------------------------------------------------


def conclusion_rows() -> list[dict[str, Any]]:
    return [copy.deepcopy(row) for row in _table(CONCLUSION_TABLE)]


def conclusion_for_report(report_code: str) -> dict[str, Any] | None:
    for row in conclusion_rows():
        if str(row.get("报告编号")) == report_code:
            return row
    return None


def historical_columns(cohort_code: str) -> dict[str, float]:
    """历史留档里的周期列：矩阵被整列替换后仍可追溯到原历史结果。"""
    entry = history_by_cohort().get(str(cohort_code))
    return dict(entry.get("周期列", {})) if entry else {}


def insight_workbench_row(report: dict[str, Any], version: str = "V032") -> dict[str, Any]:
    """报告列表行：报告字段 + 从留存矩阵读取的周期留存率 + 结论表结论。

    历史口径取历史留档（矩阵的原始结果），新口径取 V032 独立版本表；
    这样矩阵按策略整列替换后，报告两侧的口径标签仍然成立。
    """
    row = copy.deepcopy(report)
    code = str(report.get("关联群组编号") or "")
    period = int(report.get("核对周期") or 0)
    conclusion = conclusion_for_report(str(report.get("报告编号")))
    if code and period > 0:
        label = f"第{period}期"
        historical = historical_columns(code)
        current = matrix_row_for(code, "V032")
        if historical:
            row["历史口径留存率"] = float(historical.get(label, 0.0))
        if current is not None:
            row["新口径留存率"] = float(period_columns(current).get(label, 0.0))
    if conclusion is not None:
        row["核对结论"] = conclusion.get("结论", "")
        row["结论来源"] = CONCLUSION_TABLE
    return row


def insight_workbench(version: str = "V032") -> list[dict[str, Any]]:
    return [insight_workbench_row(row, version) for row in _table(INSIGHT_MODULE)]


def insight_detail(entry_id: int, version: str = "V032") -> dict[str, Any] | None:
    entry = store.find(INSIGHT_MODULE, entry_id)
    if entry is None:
        return None
    return insight_workbench_row(entry, version)


def verify_insight_samples() -> dict[str, Any]:
    """用原报告样例核对关键发现：样例结论必须与矩阵读取结果一致。"""
    mismatches: list[dict[str, Any]] = []
    for report in _table(INSIGHT_MODULE):
        code = str(report.get("关联群组编号") or "")
        period = int(report.get("核对周期") or 0)
        label = f"第{period}期"
        historical = historical_columns(code)
        current = matrix_row_for(code, "V032")
        if not historical or current is None:
            mismatches.append({"报告编号": report.get("报告编号"), "原因": "矩阵缺少群组行"})
            continue
        old = float(historical.get(label, 0.0))
        new = float(period_columns(current).get(label, 0.0))
        finding = str(report.get("关键发现", ""))
        if f"{old:.2%}" not in finding:
            mismatches.append({
                "报告编号": report.get("报告编号"),
                "原因": "历史口径留存率与关键发现不一致",
                "期望": old,
                "实际": finding,
            })
        if f"{new:.2%}" not in finding:
            mismatches.append({
                "报告编号": report.get("报告编号"),
                "原因": "新口径留存率与关键发现不一致",
                "期望": new,
                "实际": finding,
            })
    return {"ok": not mismatches, "checked": len(_table(INSIGHT_MODULE)), "mismatches": mismatches}


# ---------------------------------------------------------------------------
# 历史核对：重构前后必须复现同一份矩阵。
# ---------------------------------------------------------------------------


def verify_history() -> dict[str, Any]:
    """核对留存矩阵数据表是否仍复现历史结果。

    两边独立计算：一边是留档（原成员边界 + 原周期窗口），一边是现表。
    任何一处周期列漂移都会在这里暴露，而不是等到报告口径对不上。
    """
    expected_rows = _recompute_from_history(HISTORICAL_CALIBER)
    expected = {row["群组编号"]: row for row in expected_rows}
    actual = {
        str(row["群组编号"]): row
        for row in matrix_rows("V031", include_residue=False)
    }
    differences: list[dict[str, Any]] = []
    for code, expected_row in expected.items():
        actual_row = actual.get(code)
        if actual_row is None:
            differences.append({"群组编号": code, "原因": "矩阵缺少该群组"})
            continue
        expected_columns = period_columns(expected_row)
        actual_columns = period_columns(actual_row)
        if expected_columns != actual_columns:
            differences.append({
                "群组编号": code,
                "期望": expected_columns,
                "实际": actual_columns,
            })
        if expected_row.get("成员边界") != actual_row.get("成员边界"):
            differences.append({
                "群组编号": code,
                "原因": "成员边界不一致",
                "期望": expected_row.get("成员边界"),
                "实际": actual_row.get("成员边界"),
            })
    for code in actual:
        if code not in expected:
            differences.append({"群组编号": code, "原因": "历史留档中没有该群组"})
    # 残留按周期窗口逐行核对，不依赖残留标记，避免标记丢失后把越界列当成留存率。
    residue = _residue_in_table(matrix_rows("V031", include_residue=True))
    return {
        "ok": not differences,
        "版本": "V031",
        "口径": HISTORICAL_CALIBER,
        "核对群组数": len(expected),
        "差异": differences,
        "未清残留": residue,
        "矩阵指纹": matrix_fingerprint(matrix_rows("V031", include_residue=False)),
        "留档指纹": matrix_fingerprint(expected_rows),
    }


# ---------------------------------------------------------------------------
# 矩阵替换：V032 的事务化入口。
# ---------------------------------------------------------------------------


def _archive_event(
    *,
    action: str,
    result: str,
    reason: str,
    before: list[dict[str, Any]],
    after: list[dict[str, Any]],
    detail: dict[str, Any] | None = None,
    cohort_code: str | None = None,
) -> dict[str, Any]:
    event = {
        "id": store.next_id(ARCHIVE_TABLE),
        "版本": MATRIX_VERSION,
        "操作": action,
        "群组编号": cohort_code or COHORTS[0]["群组编号"],
        "结果": result,
        "原因": reason,
        "明细": detail or {},
        "变更前指纹": matrix_fingerprint(before),
        "变更后指纹": matrix_fingerprint(after),
        "矩阵行数": len([row for row in after if not row.get("残留")]),
        "时间": "2026-11-18T00:00:00",
    }
    return event


def _residue_in_table(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    residue: dict[str, list[str]] = {}
    for row in rows:
        window = int(row.get("留存窗口") or 0)
        if window <= 0:
            window = period_count(row)
        found = find_residue(row, window)
        if found:
            residue[str(row.get("群组编号"))] = found
    return residue


def replace_matrix(
    *,
    policy: str = POLICY_HISTORICAL_FIRST,
    caliber: str = CURRENT_CALIBER,
    operator: str = "V032",
) -> dict[str, Any]:
    """执行一次矩阵替换，返回结果并写入 V032 留档。

    事务边界覆盖三张表：矩阵表、V032 版本表、快照表。
    任何一步失败（含未清残留）都整笔回滚，留档里记录 ``rolled_back``。
    """
    if policy not in POLICIES:
        raise RetentionError(f"未知的矩阵替换策略：{policy}")
    if caliber not in (CURRENT_CALIBER, HISTORICAL_CALIBER):
        raise RetentionError(f"未知的周期口径：{caliber}")

    before_matrix = copy.deepcopy(_table(MATRIX_TABLE))
    before_version = copy.deepcopy(_table(VERSION_TABLE))
    before_snapshot = copy.deepcopy(_table(SNAPSHOT_TABLE))

    try:
        residue = _residue_in_table(before_matrix)
        if residue:
            detail = {"残留": residue, "处理": "阻断替换并回滚"}
            reason = "矩阵存在未清残留周期列，事务已回滚"
            event = _archive_event(
                action="矩阵替换",
                result="rolled_back",
                reason=reason,
                before=before_matrix,
                after=before_matrix,
                detail=detail,
                cohort_code=next(iter(residue), None),
            )
            _table(ARCHIVE_TABLE).append(event)
            return {
                "ok": False,
                "结果": "rolled_back",
                "原因": reason,
                "残留": residue,
                "留档": event,
                "矩阵": _public_matrix(before_matrix),
                "版本表": _public_matrix(before_version),
            }

        if policy == POLICY_RECOMPUTE:
            # 先给历史列拍快照，再整列替换为当前口径。
            snapshot = [
                {
                    "id": store.next_id(SNAPSHOT_TABLE) + index,
                    "矩阵版本": "V031",
                    "群组编号": row.get("群组编号"),
                    "周期口径": HISTORICAL_CALIBER,
                    "成员边界": copy.deepcopy(row.get("成员边界")),
                    "周期列": period_columns(row),
                    "周期日期": copy.deepcopy(row.get("周期日期", {})),
                    "来源指纹": matrix_fingerprint(before_matrix),
                }
                for index, row in enumerate(before_matrix)
                if not row.get("残留")
            ]
            _table(SNAPSHOT_TABLE).extend(snapshot)
            _table(MATRIX_TABLE)[:] = _recompute_from_history(caliber)
        else:
            # 历史口径优先：矩阵保留旧列，差异只作为附注，不覆盖历史结果。
            for row in _table(MATRIX_TABLE):
                if row.get("残留"):
                    continue
                code = str(row.get("群组编号"))
                entry = history_by_cohort().get(code)
                if entry is None:
                    continue
                current = retention_series(_definition_for_history(entry), caliber)
                row["新口径差异"] = diff_columns(period_columns(row), current["周期列"])
                row["口径"] = HISTORICAL_CALIBER
                row["矩阵版本"] = "V031"

        # 新周期口径始终落在独立版本表里，历史矩阵按策略决定是否保留旧列。
        target_rows = [dict(row, 接收方=operator) for row in _recompute_from_history(caliber)]
        _table(VERSION_TABLE)[:] = target_rows
        event = _archive_event(
            action="矩阵替换",
            result="succeeded",
            reason=f"按 {policy} 策略替换，结果写入 {VERSION_TABLE}",
            before=before_matrix,
            after=_table(MATRIX_TABLE),
            detail={"策略": policy, "口径": caliber, "接收方": operator},
        )
        _table(ARCHIVE_TABLE).append(event)
        return {
            "ok": True,
            "结果": "succeeded",
            "策略": policy,
            "口径": caliber,
            "接收方": operator,
            "留档": event,
            "矩阵": _public_matrix(_table(MATRIX_TABLE)),
            "版本表": _public_matrix(_table(VERSION_TABLE)),
        }
    except Exception as exc:  # noqa: BLE001 - 事务回滚必须覆盖所有异常
        _table(MATRIX_TABLE)[:] = before_matrix
        _table(VERSION_TABLE)[:] = before_version
        _table(SNAPSHOT_TABLE)[:] = before_snapshot
        event = _archive_event(
            action="矩阵替换",
            result="rolled_back",
            reason=f"替换失败，事务已回滚：{exc}",
            before=before_matrix,
            after=before_matrix,
        )
        _table(ARCHIVE_TABLE).append(event)
        raise


def _public_matrix(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [copy.deepcopy(row) for row in rows]


def archive_rows() -> list[dict[str, Any]]:
    return [copy.deepcopy(row) for row in _table(ARCHIVE_TABLE)]


def snapshot_rows() -> list[dict[str, Any]]:
    return [copy.deepcopy(row) for row in _table(SNAPSHOT_TABLE)]


def retention_series_from_history(cohort_code: str) -> dict[str, Any] | None:
    """按留档成员边界重跑单个历史同期群（历史口径），不读取当前群组定义。"""
    entry = history_by_cohort().get(cohort_code)
    if entry is None:
        return None
    return retention_series(_definition_for_history(entry), HISTORICAL_CALIBER)


def clean_residue(operator: str = "V032") -> dict[str, Any]:
    """清理未清残留周期列，并写入 V032 留档。"""
    before = copy.deepcopy(_table(MATRIX_TABLE))
    residue = _residue_in_table(before)
    if not residue:
        return {"ok": True, "清理": {}, "原因": "没有发现未清残留", "留档": None}
    kept = [row for row in before if not row.get("残留")]
    for row in kept:
        window = int(row.get("留存窗口") or period_count(row))
        for column in find_residue(row, window):
            row.pop(column, None)
    _table(MATRIX_TABLE)[:] = kept
    event = _archive_event(
        action="清理残留",
        result="succeeded",
        reason="按 V032 留档核对后清理旧矩阵残留行",
        before=before,
        after=kept,
        detail={"清理": residue, "接收方": operator},
    )
    _table(ARCHIVE_TABLE).append(event)
    return {"ok": True, "清理": residue, "留档": event, "矩阵": _public_matrix(kept)}


def restore_snapshot(operator: str = "V032") -> dict[str, Any]:
    """用快照恢复历史列：整列替换后仍能回到原历史周期口径。"""
    snapshots = _table(SNAPSHOT_TABLE)
    if not snapshots:
        return {"ok": False, "原因": "没有可恢复的历史列快照", "矩阵": _public_matrix(_table(MATRIX_TABLE))}
    latest = max(str(item.get("来源指纹", "")) for item in snapshots)
    before = copy.deepcopy(_table(MATRIX_TABLE))
    restored: list[dict[str, Any]] = []
    for item in snapshots:
        if str(item.get("来源指纹", "")) != latest:
            continue
        entry = history_by_cohort().get(str(item.get("群组编号")))
        if entry is None:
            continue
        # 以快照里的历史列为准恢复，必要时用留档补齐窗口边界。
        row = {
            "id": len(restored) + 1,
            "status": "已生效",
            "pending": False,
            "abnormal": False,
            "群组编号": item.get("群组编号"),
            "群组名称": entry.get("群组名称", ""),
            "时间基准": entry.get("时间基准", ""),
            "追踪周期": entry.get("追踪周期", "周"),
            "留存窗口": entry.get("留存窗口", len(item.get("周期列", {}))),
            "分析指标": entry.get("分析指标", "留存率"),
            "口径": HISTORICAL_CALIBER,
            "口径版本": HISTORICAL_CALIBER,
            "矩阵版本": "V031",
            "是否历史": True,
            "残留": False,
            "生效时间": "2026-09-01",
            "成员边界": copy.deepcopy(item.get("成员边界")),
            "周期日期": copy.deepcopy(item.get("周期日期", {})),
            "接收方": operator,
        }
        row.update(item.get("周期列", {}))
        restored.append(row)
    if not restored:
        return {"ok": False, "原因": "快照数据无法恢复", "矩阵": _public_matrix(before)}
    _table(MATRIX_TABLE)[:] = restored
    event = _archive_event(
        action="快照恢复",
        result="succeeded",
        reason="按历史列快照恢复留存矩阵",
        before=before,
        after=restored,
        detail={"快照指纹": latest, "接收方": operator},
    )
    _table(ARCHIVE_TABLE).append(event)
    return {"ok": True, "留档": event, "矩阵": _public_matrix(restored)}


class RetentionMatrixService:
    """留存矩阵数据表的读写门面：路由层只调这里，不自行组合口径。"""

    def matrix(self, *, version: str = "V031", include_residue: bool = False) -> dict[str, Any]:
        rows = matrix_rows(version, include_residue=include_residue)
        return {
            "version": version.upper(),
            "columns": self._columns(rows),
            "items": rows,
            "versions": versions(),
        }

    @staticmethod
    def _columns(rows: list[dict[str, Any]]) -> list[str]:
        columns: list[str] = []
        for row in rows:
            for key in row:
                if key.startswith("第") and key.endswith("期") and key not in columns:
                    columns.append(key)
        return sorted(columns, key=lambda item: int(item[1:-1]))

    def versions(self) -> list[dict[str, Any]]:
        return versions()

    def history_check(self) -> dict[str, Any]:
        return verify_history()

    def archive(self) -> list[dict[str, Any]]:
        return archive_rows()

    def snapshots(self) -> list[dict[str, Any]]:
        return snapshot_rows()

    def replace(
        self,
        *,
        policy: str = POLICY_HISTORICAL_FIRST,
        caliber: str = CURRENT_CALIBER,
        operator: str = "V032",
    ) -> dict[str, Any]:
        return replace_matrix(policy=policy, caliber=caliber, operator=operator)

    def clean_residue(self, operator: str = "V032") -> dict[str, Any]:
        return clean_residue(operator)

    def restore(self, operator: str = "V032") -> dict[str, Any]:
        return restore_snapshot(operator)

    def check_archive(self) -> dict[str, Any]:
        return check_archive()


def check_archive() -> dict[str, Any]:
    """按 V032 留档核对：最近一次留档的变更后指纹必须等于当前矩阵状态。"""
    events = archive_rows()
    if not events:
        return {"ok": False, "原因": "没有 V032 留档", "事件数": 0}
    latest = events[-1]
    current = matrix_fingerprint(matrix_rows("V031", include_residue=True))
    matched = str(latest.get("变更后指纹", "")) == current
    return {
        "ok": matched,
        "事件数": len(events),
        "最近留档": {
            "操作": latest.get("操作"),
            "结果": latest.get("结果"),
            "原因": latest.get("原因"),
            "群组编号": latest.get("群组编号"),
        },
        "留档指纹": latest.get("变更后指纹"),
        "当前矩阵指纹": current,
        "版本": MATRIX_VERSION,
    }
