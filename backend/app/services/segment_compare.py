"""分群对比 分析看板服务：汇总指标、运行分析并生成模拟结果。"""
from __future__ import annotations

from app.services.analysis_board import AnalysisBoardService

MODULE = "segment_compare"
REQUIRED_FIELDS = ["任务编号", "分群A", "分群B"]
STATUS_ORDER = ["草稿", "计算中", "已完成", "已废弃"]
ACTION_RULES = {"开始计算": "计算中", "确认完成": "已完成", "废弃任务": "已废弃"}
NEGATIVE_ACTIONS = []


class SegmentCompareService(AnalysisBoardService):
    """列表汇总、参数运行与详情读取统一走 AnalysisBoardService，避免重复口径。"""

    MODULE = MODULE

