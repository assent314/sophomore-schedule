"""AI 排程接口。"""

from __future__ import annotations

import json
from datetime import date as date_type
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import engine
from ..db import get_db
from ..models import PlanRun
from ..time_utils import local_now
from ..schemas import PlanApplyRequest, PlanRequest, PlanResponse

router = APIRouter(prefix="/plan", tags=["plan"])


@router.post("", response_model=PlanResponse)
async def plan(payload: PlanRequest, db: Session = Depends(get_db)) -> PlanResponse:
    try:
        result = await engine.execute_plan(
            db,
            payload.date,
            payload.text,
            mode=payload.mode,
            preview=False,
            replace_ai_blocks=payload.replace_ai_blocks,
            keep_done=payload.keep_done,
            extra_constraints=payload.extra_constraints,
            save_tasks=payload.save_tasks,
        )
    except Exception as exc:  # noqa: BLE001 — 统一转成可读错误
        raise HTTPException(500, f"排程失败：{exc}") from exc
    return PlanResponse(**result)


@router.post("/preview", response_model=dict)
async def preview_plan(payload: PlanRequest, db: Session = Depends(get_db)) -> dict:
    result = await engine.execute_plan(
        db,
        payload.date,
        payload.text,
        mode=payload.mode,
        preview=True,
        replace_ai_blocks=payload.replace_ai_blocks,
        keep_done=payload.keep_done,
        extra_constraints=payload.extra_constraints,
        save_tasks=False,
    )
    return {
        "plan_run_id": result["plan_run_id"],
        "engine": result["engine"],
        "blocks": result["blocks"],
        "notes": result["notes"],
        "questions": result["questions"],
        "adjustments": result["adjustments"],
        "rule_ids_used": result["rule_ids_used"],
        "deferred": result["deferred"],
        "free_min": result["free_min"],
        "usage": result["usage"],
    }


@router.post("/apply", response_model=PlanResponse)
def apply_plan(payload: PlanApplyRequest, db: Session = Depends(get_db)) -> PlanResponse:
    """只应用服务端保存的预览；基础日程变化时要求重新预览。"""
    run = db.get(PlanRun, payload.plan_run_id) if payload.plan_run_id else None
    if run is None:
        raise HTTPException(404, "预览不存在，请重新生成")
    if run.status != "preview":
        raise HTTPException(409, "预览已应用或失效，请重新生成")
    if run.plan_date != payload.date or run.mode != payload.mode:
        raise HTTPException(400, "预览日期或模式不匹配")
    try:
        saved = json.loads(run.raw_response)
        plan = saved["plan"]
        expiry = datetime.fromisoformat(saved["expires_at"])
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(409, "预览记录不完整，请重新生成") from exc
    if local_now(db) > expiry:
        raise HTTPException(409, "预览已超过 30 分钟，请重新生成")
    if (payload.replace_ai_blocks != saved["replace_ai_blocks"] or
            payload.keep_done != saved["keep_done"]):
        raise HTTPException(400, "预览选项不匹配")
    ctx = engine.build_context(
        db, payload.date, mode=payload.mode,
        replace_ai_blocks=payload.replace_ai_blocks, keep_done=payload.keep_done,
    )
    if engine.context_revision(ctx) != saved["context_revision"]:
        raise HTTPException(409, "日程或个人设置已变化，请重新生成预览")
    ctx["_session"] = db
    try:
        events = engine.commit_plan(
            db,
            ctx,
            plan,
            run=run,
            mode=payload.mode,
            replace_ai_blocks=payload.replace_ai_blocks,
            keep_done=payload.keep_done,
            save_tasks=True,
            strict_preview=True,
        )
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(400, f"应用失败：{exc}") from exc
    run.events_created = len(events)
    run.status = "applied"
    db.commit()
    return PlanResponse(
        plan_run_id=run.id,
        engine=run.engine,
        events=events,
        notes=run.notes,
        memory_used=False,
        usage={},
    )


@router.get("/runs", response_model=list[dict])
def list_runs(
    day: date_type | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[dict]:
    stmt = select(PlanRun).order_by(PlanRun.created_at.desc()).limit(limit)
    if day:
        stmt = stmt.where(PlanRun.plan_date == day)
    rows = db.scalars(stmt).all()
    return [
        {
            "id": r.id,
            "plan_date": r.plan_date.isoformat(),
            "mode": r.mode,
            "engine": r.engine,
            "status": r.status,
            "error": r.error,
            "events_created": r.events_created,
            "prompt_tokens": r.prompt_tokens,
            "completion_tokens": r.completion_tokens,
            "notes": r.notes,
            "created_at": r.created_at.isoformat(),
            "input_text": r.input_text[:200],
        }
        for r in rows
    ]
