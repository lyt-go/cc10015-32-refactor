"""洞察报告业务规则：报告读取与关键发现核对都走留存矩阵的共用路径。"""
from __future__ import annotations

from typing import Any

from app.services.analysis_board import AnalysisBoardService
from app.services import retention

MODULE = "insight_report"
REQUIRED_FIELDS = ["报告编号", "分析主题", "数据来源"]
STATUS_ORDER = ["草稿", "生成中", "已完成", "已归档"]
ACTION_RULES = {"开始生成": "生成中", "确认完成": "已完成", "归档报告": "已归档"}
NEGATIVE_ACTIONS = []


class InsightReportService(AnalysisBoardService):
    """洞察报告只读留存矩阵，不再自己维护周期窗口和指标口径。"""

    MODULE = MODULE

    def list_results(self) -> list[dict[str, Any]]:
        return self.workbench_rows()

    def workbench_rows(self, version: str = "V032") -> list[dict[str, Any]]:
        return retention.insight_workbench(version)

    def get_entry(self, entry_id: int, version: str = "V032") -> dict[str, Any] | None:
        return retention.insight_detail(entry_id, version)

    def conclusions(self) -> list[dict[str, Any]]:
        """洞察结论数据表：报告样例核对后的结论。"""
        return retention.conclusion_rows()

    def conclusion_for(self, report_code: str) -> dict[str, Any] | None:
        return retention.conclusion_for_report(report_code)

    def verify(self) -> dict[str, Any]:
        return retention.verify_insight_samples()
