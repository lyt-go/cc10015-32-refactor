"""AB结果分析 分析看板服务：汇总指标、运行分析并生成模拟结果。"""
from __future__ import annotations

from app.services.analysis_board import AnalysisBoardService

MODULE = "ab_result"
REQUIRED_FIELDS = ["报告编号", "实验编号", "分析指标"]
STATUS_ORDER = ["待分析", "计算中", "已完成", "已归档"]
ACTION_RULES = {"开始计算": "计算中", "确认完成": "已完成", "归档报告": "已归档"}
NEGATIVE_ACTIONS = []


class AbResultService(AnalysisBoardService):
    """列表汇总、参数运行与详情读取统一走 AnalysisBoardService，避免重复口径。"""

    MODULE = MODULE

