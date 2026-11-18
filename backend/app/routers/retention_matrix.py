"""留存矩阵数据表接口：历史列、V032 独立版本、留档与核对。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import EntryPayload
from app.services import retention

router = APIRouter(prefix="/api/retention_matrix", tags=["留存矩阵"])
service = retention.RetentionMatrixService()


@router.get("")
def get_matrix(version: str = Query("V031"), include_residue: bool = Query(False)) -> dict[str, Any]:
    return service.matrix(version=version, include_residue=include_residue)


@router.get("/versions")
def get_versions() -> dict[str, Any]:
    return {"items": service.versions()}


@router.get("/history-check")
def history_check() -> dict[str, Any]:
    """重构核对：留存矩阵数据表必须复现历史结果。"""
    return service.history_check()


@router.get("/archive")
def get_archive() -> dict[str, Any]:
    return {"items": service.archive()}


@router.get("/archive-check")
def check_archive() -> dict[str, Any]:
    """按 V032 留档核对矩阵状态。"""
    return service.check_archive()


@router.get("/snapshots")
def get_snapshots() -> dict[str, Any]:
    return {"items": service.snapshots()}


@router.post("/replace")
def replace_matrix(payload: EntryPayload) -> dict[str, Any]:
    """V032 矩阵替换：先校验残留，再按策略替换，结果整笔留档。"""
    values = payload.values
    try:
        return service.replace(
            policy=str(values.get("策略") or retention.POLICY_HISTORICAL_FIRST),
            caliber=str(values.get("口径") or retention.CURRENT_CALIBER),
            operator=str(values.get("接收方") or "V032"),
        )
    except retention.RetentionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/clean-residue")
def clean_residue(payload: EntryPayload) -> dict[str, Any]:
    return service.clean_residue(operator=str(payload.values.get("接收方") or "V032"))


@router.post("/restore")
def restore_matrix(payload: EntryPayload) -> dict[str, Any]:
    return service.restore(operator=str(payload.values.get("接收方") or "V032"))
