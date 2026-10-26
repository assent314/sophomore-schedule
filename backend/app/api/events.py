"""日历方块（事件）CRUD 与完成打勾。"""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Event
from ..schemas import EventCreate, EventOut, EventUpdate

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[EventOut])
def list_events(
    start: date_type | None = Query(default=None),
    end: date_type | None = Query(default=None),
    date: date_type | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[Event]:
    if date:
        start = end = date
    if start is None:
        start = date_type.today() - timedelta(days=7)
    if end is None:
        end = start + timedelta(days=21)
    rows = db.scalars(
        select(Event).where(Event.plan_date >= start, Event.plan_date <= end).order_by(Event.start.asc())
    ).all()
    return list(rows)


@router.post("", response_model=EventOut, status_code=201)
def create_event(payload: EventCreate, db: Session = Depends(get_db)) -> Event:
    if payload.end <= payload.start:
        raise HTTPException(400, "结束时间必须晚于开始时间")
    ev = Event(**payload.model_dump(), plan_date=payload.start.date())
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


@router.patch("/{event_id}", response_model=EventOut)
def update_event(event_id: str, payload: EventUpdate, db: Session = Depends(get_db)) -> Event:
    ev = db.get(Event, event_id)
    if not ev:
        raise HTTPException(404, "方块不存在")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(ev, key, value)
    if "start" in data and "end" not in data:
        ev.end = ev.start + (ev.end - ev.start)
    if "start" in data:
        ev.plan_date = ev.start.date()
    if ev.end <= ev.start:
        raise HTTPException(400, "结束时间必须晚于开始时间")
    db.commit()
    db.refresh(ev)
    return ev


@router.post("/{event_id}/complete", response_model=EventOut)
def complete_event(
    event_id: str,
    status: str = Query(default="done"),
    actual_min: int | None = Query(default=None),
    quality: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> Event:
    ev = db.get(Event, event_id)
    if not ev:
        raise HTTPException(404, "方块不存在")
    if status not in {"planned", "done", "partial", "skipped", "moved"}:
        raise HTTPException(400, "非法状态")
    ev.status = status
    if actual_min is not None:
        ev.actual_min = max(0, actual_min)
    if quality is not None:
        ev.quality = max(1, min(5, quality))
    db.commit()
    db.refresh(ev)
    return ev


@router.delete("/{event_id}", status_code=204)
def delete_event(event_id: str, db: Session = Depends(get_db)) -> None:
    ev = db.get(Event, event_id)
    if not ev:
        raise HTTPException(404, "方块不存在")
    db.delete(ev)
    db.commit()
