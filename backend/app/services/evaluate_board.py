"""评估看板 分析看板服务：汇总指标、运行分析并生成模拟结果。"""
from __future__ import annotations

from app.services.analysis_board import AnalysisBoardService

MODULE = "evaluate_board"
REQUIRED_FIELDS = ["看板编号", "看板名称", "关联实验"]
STATUS_ORDER = ["草稿", "待校验", "已发布", "已停用"]
ACTION_RULES = {"提交校验": "待校验", "确认发布": "已发布", "停用看板": "已停用"}
NEGATIVE_ACTIONS = ["停用看板"]


class EvaluateBoardService(AnalysisBoardService):
    """列表汇总、参数运行与详情读取统一走 AnalysisBoardService，避免重复口径。"""

    MODULE = MODULE

