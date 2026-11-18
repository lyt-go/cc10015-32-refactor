"""分析看板类模块的共用实现。

同期群追踪、洞察报告（以及其他看板页）原来各自维护一份列表汇总、参数运行、
详情读取和 KPI 摘要，周期窗口或指标口径一改就要改两遍。这里把它们收拢成一份：

- 模块只需要声明 ``MODULE`` 与可选的 ``DECORATE_FIELDS``；
- 详情读取、列表汇总、参数运行、摘要指标都走同一条路径；
- 业务模块仍然可以在子类里覆盖，但默认行为保持一致。
"""
from __future__ import annotations

import random
from typing import Any

from app.store import store

DEFAULT_RUN_SIZE = 6


class AnalysisBoardService:
    """分析看板服务的公共骨架，子类只声明模块名。"""

    MODULE: str = ""
    # 列表里额外展示的派生字段；子类可覆盖成常量字段来源。
    DECORATE_FIELDS: tuple[str, ...] = ()

    def rows(self) -> list[dict[str, Any]]:
        return store.rows(self.MODULE)

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(self.MODULE, entry_id)

    def decorate(self, row: dict[str, Any]) -> dict[str, Any]:
        """派生指标的统一入口：默认保持原有的指标值/对比基准/差异三元组。"""
        result = dict(row)
        result["指标值"] = round(random.uniform(0.65, 0.98), 3)
        result["对比基准"] = round(random.uniform(0.60, 0.92), 3)
        result["差异"] = round(result["指标值"] - result["对比基准"], 3)
        return result

    def list_results(self) -> list[dict[str, Any]]:
        return [self.decorate(row) for row in self.rows()]

    def run_analysis(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        count = int(params.get("样本范围", params.get("并行数量", str(DEFAULT_RUN_SIZE))))
        results: list[dict[str, Any]] = []
        for index in range(count):
            results.append({
                "id": index + 1,
                "分组": f"分组{(index % 3) + 1}",
                "指标值": round(random.uniform(0.62, 1.02), 3),
                "对比基准": round(random.uniform(0.58, 0.95), 3),
                "差异": round(random.uniform(-0.2, 0.3), 3),
            })
        return results


def summary_metrics() -> list[dict[str, Any]]:
    """KPI 摘要的单一实现，避免每个路由各写一份随机口径。"""
    return [
        {"label": "覆盖数据源", "value": random.randint(12, 45), "trend": random.randint(-12, 25)},
        {"label": "最新指标值", "value": round(random.uniform(0.72, 0.99), 3), "trend": random.randint(-8, 15)},
        {"label": "异常记录", "value": random.randint(0, 8), "trend": -random.randint(1, 10)},
    ]
