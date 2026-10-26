"""每日反馈。"""

from __future__ import annotations

from datetime import date as date_type
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import nl, stats
from ..db import get_db
from ..models import Feedback
from ..time_utils import local_today
from ..schemas import FeedbackOut, FeedbackUpsert

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.get("", response_model=list[FeedbackOut])
def list_feedback(
    start: date_type | None = Query(default=None),
    end: date_type | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[Feedback]:
    end = end or local_today(db)
    start = start or (end - timedelta(days=30))
    rows = db.scalars(
        select(Feedback).where(Feedback.date >= start, Feedback.date <= end).order_by(Feedback.date.desc())
    ).all()
    return list(rows)


@router.get("/{day}", response_model=FeedbackOut)
def get_feedback(day: date_type, db: Session = Depends(get_db)) -> Feedback:
    row = db.scalars(select(Feedback).where(Feedback.date == day)).first()
    if not row:
        raise HTTPException(404, "当天还没有反馈")
    return row


@router.put("/{day}", response_model=FeedbackOut)
def upsert_feedback(day: date_type, payload: FeedbackUpsert, db: Session = Depends(get_db)) -> Feedback:
    row = db.scalars(select(Feedback).where(Feedback.date == day)).first()
    data = payload.model_dump(exclude_unset=True)
    notes = data.pop("notes", None)
    if row is None:
        row = Feedback(date=day)
        db.add(row)
    for key, value in data.items():
        setattr(row, key, value)
    if notes is not None:
        row.notes = notes
        # 顺带从自然语言里抽结构化指标（仅在用户没填数字时）
        parsed = nl.parse_feedback_offline(notes)
        for key, value in parsed.items():
            if getattr(row, key, None) is None:
                setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


@router.post("/{day}/parse", response_model=dict)
def parse_feedback(day: date_type, text: str = Query(default=""), db: Session = Depends(get_db)) -> dict:
    """把一句自然语言反馈解析成结构化字段（不落库，供前端预填）。"""
    return nl.parse_feedback_offline(text)
