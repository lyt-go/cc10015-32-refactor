"""AB结果分析 分析看板接口：汇总指标、参数运行与结果导出。"""
from __future__ import annotations

import csv
import io
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.services.analysis_board import summary_metrics
from app.schemas import ActionPayload, ActionResult, EntryPayload
from app.services.ab_result import AbResultService

router = APIRouter(prefix="/api/ab_result", tags=["AB结果分析"])
service = AbResultService()
LIST_FIELDS = ["报告编号", "实验编号", "分析指标", "对照组均值", "实验组均值", "置信水平", "效果方向", "生成时间"]
STATUSES = ["待分析", "计算中", "已完成", "已归档"]


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
                             headers={"Content-Disposition": "attachment; filename=ab_result.csv"})


@router.get("/{entry_id}")
def get_entry(entry_id: int) -> dict:
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"分析报告 {entry_id} 不存在")
    return entry
