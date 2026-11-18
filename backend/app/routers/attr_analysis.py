"""归因分析 分析看板接口：汇总指标、参数运行与结果导出。"""
from __future__ import annotations

import csv
import io
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.services.analysis_board import summary_metrics
from app.schemas import ActionPayload, ActionResult, EntryPayload
from app.services.attr_analysis import AttrAnalysisService

router = APIRouter(prefix="/api/attr_analysis", tags=["归因分析"])
service = AttrAnalysisService()
LIST_FIELDS = ["任务编号", "目标指标", "候选因子", "归因模型", "分析窗口", "贡献度阈值", "交互项数", "任务批次"]
STATUSES = ["草稿", "计算中", "已完成", "已取消"]


def csv_cell(value: Any) -> str:
    text = str(value) if value is not None else ""
    if text and text[0] in "=+-@":
        text = "'" + text
    return '"' + text.replace('"', '""') + '"'


@router.get("/summary")
def get_summary() -> dict[str, Any]:
    return {"metrics": summary_metrics()}


@router.get("")
def list_results() -> dict[str, Any]:
    return {"items": service.list_results()}


@router.post("/run")
def run_analysis(payload: EntryPayload) -> dict[str, Any]:
    results = service.run_analysis(payload.values)
    return {"items": results}


@router.get("/export")
def export_entries() -> StreamingResponse:
    items = service.list_results()
    buf = io.StringIO(newline="")
    writer = csv.writer(buf)
    all_keys = ["id"]
    if items:
        all_keys = list(items[0].keys())
    writer.writerow(all_keys)
    for item in items:
        writer.writerow([csv_cell(item.get(k, "")) for k in all_keys])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": "attachment; filename=attr_analysis.csv"})


@router.get("/{entry_id}")
def get_entry(entry_id: int) -> dict:
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"归因任务 {entry_id} 不存在")
    return entry
