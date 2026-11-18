"""归因分析 分析看板服务：汇总指标、运行分析并生成模拟结果。"""
from __future__ import annotations

from app.services.analysis_board import AnalysisBoardService

MODULE = "attr_analysis"
REQUIRED_FIELDS = ["任务编号", "目标指标", "候选因子"]
STATUS_ORDER = ["草稿", "计算中", "已完成", "已取消"]
ACTION_RULES = {"开始计算": "计算中", "确认完成": "已完成", "取消任务": "已取消"}
NEGATIVE_ACTIONS = []


class AttrAnalysisService(AnalysisBoardService):
    """列表汇总、参数运行与详情读取统一走 AnalysisBoardService，避免重复口径。"""

    MODULE = MODULE

