"""留存矩阵、口径版本、V032 留档与洞察结论的示例数据。

所有留存率都由 ``retention_core`` 按历史口径现算，不写死：
一旦算法或周期窗口被改动，历史留档对比会立刻失败，而不是悄悄漂移。
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from app.retention_core import (
    CURRENT_CALIBER,
    HISTORICAL_CALIBER,
    historical_archive,
    matrix_row,
    retention_series,
)
from app.retention_definitions import (
    COHORTS,
    CURRENT_CALIBER_EFFECTIVE_DATE,
    INSIGHTS,
    MATRIX_VERSION,
    RESIDUE_COHORT_ID,
    RESIDUE_PERIOD_INDEX,
    RESIDUE_REASON,
)

MATRIX_TABLE = "retention_matrix"
VERSION_TABLE = "retention_matrix_v032"
SNAPSHOT_TABLE = "retention_matrix_snapshot"
ARCHIVE_TABLE = "retention_v032_archive"
CONCLUSION_TABLE = "insight_conclusion"
HISTORY_TABLE = "retention_history"

STATUSES = ["草稿", "待校验", "已生效"]
PENDINGS = [True, True, False]
ABNORMALS = [False, True, False]


def matrix_fingerprint(rows: list[dict[str, Any]]) -> str:
    """矩阵指纹：留档核对用，按群组编号与周期列内容计算。"""
    payload = [
        {
            "群组编号": row.get("群组编号"),
            "周期列": {
                key: value
                for key, value in row.items()
                if key.startswith("第") and key.endswith("期")
            },
        }
        for row in sorted(rows, key=lambda item: str(item.get("群组编号")))
    ]
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def cohort_definition_row(cohort: dict[str, Any], index: int) -> dict[str, Any]:
    """同期群定义的展示行：字段与 cohort_track 页面保持一致，另带成员边界。"""
    return {
        "id": int(cohort["id"]),
        "status": STATUSES[index % len(STATUSES)],
        "pending": PENDINGS[index % len(PENDINGS)],
        "abnormal": ABNORMALS[index % len(ABNORMALS)],
        "群组编号": cohort["群组编号"],
        "群组名称": cohort["群组名称"],
        "首次行为": cohort["首次行为"],
        "时间基准": cohort["时间基准"],
        "追踪周期": cohort["追踪周期"],
        "留存窗口": cohort["留存窗口"],
        "分析指标": cohort["分析指标"],
        "对比群组": cohort["对比群组"],
        "成员基数": cohort["成员基数"],
        "边界版本": cohort["边界版本"],
        "边界种子": cohort["边界种子"],
    }


def _matrix_row(cohort: dict[str, Any], index: int) -> dict[str, Any]:
    series = retention_series(cohort, HISTORICAL_CALIBER)
    row = {
        "id": index,
        "status": "已生效",
        "pending": False,
        "abnormal": False,
        "群组编号": series["群组编号"],
        "口径": HISTORICAL_CALIBER,
        "口径版本": HISTORICAL_CALIBER,
        "矩阵版本": "V031",
        "是否历史": True,
        "残留": False,
        "生效时间": "2026-09-01",
    }
    row.update(matrix_row(series))
    return row


def _residue_row() -> dict[str, Any]:
    """V032 之前那次矩阵替换没清干净，留下的一行越界周期数据。"""
    cohort = COHORTS[RESIDUE_COHORT_ID - 1]
    row: dict[str, Any] = {
        "id": 100 + RESIDUE_COHORT_ID,
        "status": "已生效",
        "pending": False,
        "abnormal": True,
        "群组编号": cohort["群组编号"],
        "群组名称": cohort["群组名称"],
        "时间基准": cohort["时间基准"],
        "追踪周期": cohort["追踪周期"],
        "留存窗口": int(cohort["留存窗口"]),
        "分析指标": cohort["分析指标"],
        "口径": HISTORICAL_CALIBER,
        "口径版本": HISTORICAL_CALIBER,
        "矩阵版本": "V031",
        "是否历史": True,
        "残留": True,
        "残留原因": RESIDUE_REASON,
        "生效时间": "2026-10-28",
        "成员边界": {
            "成员基数": cohort["成员基数"],
            "边界版本": cohort["边界版本"],
            "边界种子": cohort["边界种子"],
        },
    }
    row[f"第{RESIDUE_PERIOD_INDEX}期"] = 0.0123
    return row


def matrix_rows() -> list[dict[str, Any]]:
    rows = [
        _matrix_row(cohort, index)
        for index, cohort in enumerate(COHORTS, start=1)
    ]
    rows.append(_residue_row())
    return rows


def version_rows() -> list[dict[str, Any]]:
    """新周期口径的独立版本表，与历史矩阵表分开存放，互不覆盖。"""
    rows: list[dict[str, Any]] = []
    for index, cohort in enumerate(COHORTS, start=1):
        series = retention_series(cohort, CURRENT_CALIBER)
        row = {
            "id": index,
            "status": "已生效",
            "pending": False,
            "abnormal": False,
            "群组编号": series["群组编号"],
            "口径": CURRENT_CALIBER,
            "口径版本": CURRENT_CALIBER,
            "矩阵版本": MATRIX_VERSION,
            "是否历史": False,
            "残留": False,
            "生效时间": CURRENT_CALIBER_EFFECTIVE_DATE,
        }
        row.update(matrix_row(series))
        rows.append(row)
    return rows


def conclusion_rows() -> list[dict[str, Any]]:
    """洞察结论数据表：报告样例的关键发现由历史留档 + 新口径版本共同核对。"""
    archive = historical_archive(COHORTS)
    current = {row["群组编号"]: row for row in version_rows()}
    rows: list[dict[str, Any]] = []
    for index, insight in enumerate(INSIGHTS, start=1):
        code = insight["关联群组编号"]
        period = int(insight["核对周期"])
        label = f"第{period}期"
        old = float(archive[code]["周期列"][label])
        new = float(current[code][label])
        diff = round(new - old, 4)
        direction = "高于" if diff >= 0 else "低于"
        rows.append({
            "id": index,
            "status": "已核对",
            "pending": False,
            "abnormal": False,
            "报告编号": insight["报告编号"],
            "分析主题": insight["分析主题"],
            "群组编号": code,
            "核对周期": period,
            "历史口径留存率": old,
            "新口径留存率": new,
            "差异": diff,
            "数据版本": MATRIX_VERSION,
            "结论": (
                f"{insight['分析主题']}：{code} 第{period}期历史口径留存率 {old:.2%}，"
                f"新口径 {new:.2%}，新口径{direction}历史 {abs(diff):.2%}。"
            ),
        })
    return rows


def insight_rows() -> list[dict[str, Any]]:
    """洞察报告数据表：报告样例的字段与报告页面一致，关键发现来自结论表。"""
    conclusions = {row["报告编号"]: row for row in conclusion_rows()}
    rows: list[dict[str, Any]] = []
    for index, insight in enumerate(INSIGHTS):
        conclusion = conclusions[insight["报告编号"]]
        rows.append({
            "id": int(insight["id"]),
            "status": STATUSES[index % len(STATUSES)],
            "pending": PENDINGS[index % len(PENDINGS)],
            "abnormal": ABNORMALS[index % len(ABNORMALS)],
            "报告编号": insight["报告编号"],
            "分析主题": insight["分析主题"],
            "数据来源": insight["数据来源"],
            "关键发现": conclusion["结论"],
            "建议措施": insight["建议措施"],
            "影响范围": insight["影响范围"],
            "生成时间": insight["生成时间"],
            "报告版本": insight["报告版本"],
            "关联群组编号": insight["关联群组编号"],
            "核对周期": insight["核对周期"],
        })
    return rows


def archive_rows() -> list[dict[str, Any]]:
    rows = matrix_rows()
    return [{
        "id": 1,
        "版本": MATRIX_VERSION,
        "操作": "矩阵替换",
        "群组编号": COHORTS[RESIDUE_COHORT_ID - 1]["群组编号"],
        "结果": "rolled_back",
        "原因": f"{RESIDUE_REASON}，事务已回滚",
        "明细": {"残留行": 1, "残留周期": RESIDUE_PERIOD_INDEX},
        "变更前指纹": matrix_fingerprint(rows),
        "变更后指纹": matrix_fingerprint(rows),
        "矩阵行数": len(rows),
        "时间": "2026-11-10T09:30:00",
    }]


def history_rows() -> list[dict[str, Any]]:
    """历史留档表：原成员边界 + 历史周期列，重跑与核对都以这里为准。"""
    archive = historical_archive(COHORTS)
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(archive.values(), start=1):
        rows.append({
            "id": index,
            "群组编号": item["群组编号"],
            "群组名称": item["群组名称"],
            "时间基准": item["时间基准"],
            "追踪周期": item["追踪周期"],
            "留存窗口": item["留存窗口"],
            "分析指标": item["分析指标"],
            "周期口径": item["周期口径"],
            "成员边界": dict(item["成员边界"]),
            "周期列": dict(item["周期列"]),
            "周期日期": dict(item["周期日期"]),
        })
    return rows


def cohort_rows() -> list[dict[str, Any]]:
    return [cohort_definition_row(cohort, i) for i, cohort in enumerate(COHORTS)]


def build_retention_tables() -> dict[str, list[dict[str, Any]]]:
    return {
        MATRIX_TABLE: matrix_rows(),
        VERSION_TABLE: version_rows(),
        SNAPSHOT_TABLE: [],
        ARCHIVE_TABLE: archive_rows(),
        CONCLUSION_TABLE: conclusion_rows(),
        HISTORY_TABLE: history_rows(),
    }
