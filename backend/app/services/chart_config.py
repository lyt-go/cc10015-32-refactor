"""可视化配置 分析看板服务：汇总指标、运行分析并生成模拟结果。"""
from __future__ import annotations

from app.services.analysis_board import AnalysisBoardService

MODULE = "chart_config"
REQUIRED_FIELDS = ["图表编号", "图表类型", "数据来源"]
STATUS_ORDER = ["草稿", "待校验", "已发布", "已停用"]
ACTION_RULES = {"提交校验": "待校验", "确认发布": "已发布", "停用图表": "已停用"}
NEGATIVE_ACTIONS = ["停用图表"]


class ChartConfigService(AnalysisBoardService):
    """列表汇总、参数运行与详情读取统一走 AnalysisBoardService，避免重复口径。"""

    MODULE = MODULE

