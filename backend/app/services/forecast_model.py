"""预测模型 分析看板服务：汇总指标、运行分析并生成模拟结果。"""
from __future__ import annotations

from typing import Any

from app.store import store

from app.services.analysis_board import AnalysisBoardService

MODULE = "forecast_model"
REQUIRED_FIELDS = ["模型编号", "预测对象", "历史窗口"]
STATUS_ORDER = ["草稿", "训练中", "已就绪", "已废弃"]
ACTION_RULES = {"开始训练": "训练中", "确认就绪": "已就绪", "废弃模型": "已废弃"}
NEGATIVE_ACTIONS = []


class ForecastModelService(AnalysisBoardService):
    """列表汇总、参数运行与详情读取统一走 AnalysisBoardService，避免重复口径。"""

    MODULE = MODULE

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [f for f in REQUIRED_FIELDS if not str(values.get(f) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(MODULE)
        entry = {"id": max((int(r.get("id", 0)) for r in rows), default=0) + 1}
        for f in REQUIRED_FIELDS + ["预测周期", "模型类型", "参数配置", "训练批次", "评估误差"]:
            entry[f] = values.get(f, "")
        entry["status"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return entry, []

    def train_and_predict(self, entry_id: int, values: list[float]) -> dict[str, Any]:
        """对历史数据执行简单移动平均或线性回归预测。"""
        entry = self.get_entry(entry_id)
        if not entry:
            return {"ok": False, "message": "模型不存在"}
        model_type = entry.get("模型类型", "moving_average")
        try:
            predict_periods = int(entry.get("预测周期", "3"))
        except Exception:
            predict_periods = 3
        if len(values) < 2:
            return {"ok": False, "message": "历史数据不足"}
        predictions = []
        if model_type == "moving_average" or "moving" in str(model_type):
            try:
                window = int(str(entry.get("参数配置", "window=3")).replace("window=", ""))
            except Exception:
                window = 3
            for _ in range(predict_periods):
                pred = sum(values[-window:]) / window
                predictions.append(round(pred, 4))
                values = values + [pred]
        elif "linear" in str(model_type).lower() or "regression" in str(model_type).lower():
            n = len(values)
            x_mean = (n - 1) / 2
            y_mean = sum(values) / n
            num = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
            denom = sum((i - x_mean) ** 2 for i in range(n))
            slope = num / denom if denom != 0 else 0
            intercept = y_mean - slope * x_mean
            for i in range(predict_periods):
                pred = slope * (n + i) + intercept
                predictions.append(round(pred, 4))
        else:
            predictions = [sum(values) / len(values) for _ in range(predict_periods)]
        return {"ok": True, "predictions": predictions, "method": model_type,
                "message": f"预测完成，{len(predictions)}个周期"}
