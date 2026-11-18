"""同期群追踪业务规则：同一份周期窗口与指标口径，供工作台、详情页和洞察报告复用。"""
from __future__ import annotations

from typing import Any

from app.services.analysis_board import AnalysisBoardService
from app.services import retention

MODULE = "cohort_track"
REQUIRED_FIELDS = ["群组编号", "群组名称", "首次行为"]
STATUS_ORDER = ["草稿", "待校验", "已生效", "已停用"]
ACTION_RULES = {"提交校验": "待校验", "标记生效": "已生效", "停用群组": "已停用"}
NEGATIVE_ACTIONS = ["停用群组"]


class CohortTrackService(AnalysisBoardService):
    """同期群定义与留存矩阵的读取入口。

    周期窗口、成员边界、留存口径全部走 ``app.services.retention``，
    页面只做投影，不再各自维护一套计算。
    """

    MODULE = MODULE

    def list_results(self) -> list[dict[str, Any]]:
        """工作台列表：与详情页共用同一份投影，避免两边口径分叉。"""
        return self.workbench_rows()

    def workbench_rows(self, version: str = "V031") -> list[dict[str, Any]]:
        return retention.cohort_workbench(version)

    def get_entry(self, entry_id: int, version: str = "V031") -> dict[str, Any] | None:
        return retention.cohort_detail(entry_id, version)

    def rerun(self, cohort_code: str) -> dict[str, Any] | None:
        return retention.retention_series_from_history(cohort_code)
