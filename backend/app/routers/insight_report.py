"""洞察报告 分析看板接口：汇总指标、参数运行与结果导出。"""
from __future__ import annotations

import csv
import io
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.services.analysis_board import summary_metrics
from app.schemas import ActionPayload, ActionResult, EntryPayload
from app.services.insight_report import InsightReportService

router = APIRouter(prefix="/api/insight_report", tags=["洞察报告"])
service = InsightReportService()
LIST_FIELDS = ["报告编号", "分析主题", "数据来源", "关键发现", "建议措施", "影响范围", "生成时间", "报告版本"]
STATUSES = ["草稿", "生成中", "已完成", "已归档"]


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
                             headers={"Content-Disposition": "attachment; filename=insight_report.csv"})


@router.get("/conclusions")
def get_conclusions() -> dict[str, Any]:
    """洞察结论数据表：关键发现与留存矩阵读取结果一起返回。"""
    return {"items": service.conclusions()}


@router.get("/verify")
def verify_samples() -> dict[str, Any]:
    """跨模块联动（V032）：用原报告样例核对关键发现。"""
    return service.verify()


@router.get("/{entry_id}")
def get_entry(entry_id: int) -> dict:
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"洞察报告 {entry_id} 不存在")
    return entry
