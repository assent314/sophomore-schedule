"""Codex / DeepSeek Harness 共用的聊天事实采集与排程入口。"""

from __future__ import annotations

import hashlib
import re
from datetime import date

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import engine, nl
from .models import AgentCapture, Feedback, Task
from .time_utils import local_today


class EnergyFeedback(BaseModel):
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    sleep_quality: int | None = Field(default=None, ge=1, le=5)
    energy_morning: int | None = Field(default=None, ge=1, le=5)
    energy_afternoon: int | None = Field(default=None, ge=1, le=5)
    energy_evening: int | None = Field(default=None, ge=1, le=5)
    mood: int | None = Field(default=None, ge=1, le=5)


class CapturedTask(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    estimate_min: int = Field(default=45, ge=10, le=600)
    category: str = "study"
    priority: int = Field(default=3, ge=1, le=5)
    due_date: date | None = None


class ChatCaptureInput(BaseModel):
    day: date
    message: str = Field(min_length=1, max_length=4000)
    source: str = Field(default="agent", min_length=1, max_length=40)
    message_id: str | None = Field(default=None, max_length=120)
    feedback: EnergyFeedback | None = None
    tasks: list[CapturedTask] = Field(default_factory=list, max_length=20)
    # 仅当用户明确说的是长期/平时的规律时，由 Agent 传入整条 24 小时曲线。
    habitual_energy_curve: list[int] | None = None
    constraints: list[str] = Field(default_factory=list, max_length=10)
    adjust_schedule: bool = True

    @field_validator("habitual_energy_curve")
    @classmethod
    def validate_curve(cls, value: list[int] | None) -> list[int] | None:
        if value is not None and (len(value) != 24 or any(not 1 <= v <= 5 for v in value)):
            raise ValueError("精力曲线必须是 24 个 1 至 5 的整数")
        return value


def _explicit_feedback(message: str) -> dict:
    out = nl.parse_feedback_offline(message)
    # 只解析明确指向时段的感受，不把笼统的“累”改写为某个时段的精力。
    for period, key in (("上午|早上", "energy_morning"),
                        ("下午", "energy_afternoon"), ("晚上|傍晚", "energy_evening")):
        if re.search(rf"(?:{period})[^。；;，,]{{0,12}}(?:很累|疲惫|没精神|精力差|困)", message):
            out.setdefault(key, 2)
        if re.search(rf"(?:{period})[^。；;，,]{{0,12}}(?:精神很好|精力充沛|状态很好)", message):
            out.setdefault(key, 4)
    return out


def _explicit_tasks(message: str) -> list[CapturedTask]:
    out: list[CapturedTask] = []
    for statement in nl.split_statements(message):
        if not nl.parse_duration_min(statement):
            continue
        if not re.search(r"(?:要|需要|计划|安排|必须|完成|复习|写|做|准备|学习|运动|健身)", statement):
            continue
        if re.search(r"(?:昨晚|睡了|睡眠|精力|心情)", statement):
            continue
        for parsed in nl.parse_tasks_offline(statement):
            out.append(CapturedTask(title=parsed["title"], estimate_min=parsed["estimate_min"],
                                    category=parsed["category"], priority=parsed["priority"]))
    return out[:20]


def _dedupe_key(payload: ChatCaptureInput) -> str:
    source_id = payload.message_id or payload.message.strip()
    return hashlib.sha256(f"{payload.source}\n{payload.day}\n{source_id}".encode("utf-8")).hexdigest()


async def capture(session: Session, payload: ChatCaptureInput) -> dict:
    existing = session.scalar(select(AgentCapture).where(AgentCapture.dedupe_key == _dedupe_key(payload)))
    if existing:
        return _result(existing, duplicate=True)

    feedback = _explicit_feedback(payload.message)
    if payload.feedback:
        feedback.update(payload.feedback.model_dump(exclude_none=True))
    tasks = payload.tasks or _explicit_tasks(payload.message)
    constraints = [s.strip()[:300] for s in payload.constraints if s.strip()]
    changed = bool(feedback or tasks or payload.habitual_energy_curve or constraints)

    if feedback:
        row = session.scalar(select(Feedback).where(Feedback.date == payload.day))
        if row is None:
            row = Feedback(date=payload.day)
            session.add(row)
        for key, value in feedback.items():
            setattr(row, key, value)

    created_tasks: list[dict] = []
    for item in tasks:
        existing_task = session.scalar(select(Task).where(
            Task.title == item.title, Task.status.in_(["pending", "scheduled", "partial"])))
        if existing_task:
            continue
        category = item.category if item.category in {"study", "work", "exercise", "life", "admin", "rest", "social"} else "study"
        task = Task(title=item.title, estimate_min=item.estimate_min, category=category,
                    priority=item.priority, due_date=item.due_date, source="agent")
        session.add(task)
        session.flush()
        created_tasks.append({"id": task.id, "title": task.title})

    if payload.habitual_energy_curve:
        profile = engine.get_profile(session)
        profile.energy_curve = payload.habitual_energy_curve

    facts = {
        "feedback": feedback,
        "tasks_created": created_tasks,
        "habitual_energy_curve_changed": bool(payload.habitual_energy_curve),
        "constraints": constraints,
        "adjust_requested": payload.adjust_schedule,
    }
    row = AgentCapture(dedupe_key=_dedupe_key(payload), source=payload.source,
                       day=payload.day, facts_json=dict(facts))
    session.add(row)
    session.commit()

    if changed and payload.adjust_schedule and payload.day >= local_today(session):
        try:
            result = await engine.execute_plan(
                session, payload.day, "", mode="adjust" if payload.day == local_today(session) else "new",
                replace_ai_blocks=True, keep_done=True, extra_constraints=constraints,
            )
            row.plan_run_id = result["plan_run_id"]
            facts["adjusted_event_ids"] = [ev.id for ev in result["events"]]
        except Exception as exc:  # 事实仍可保留，失败原因返回给 Agent 与用户
            session.rollback()
            row = session.get(AgentCapture, row.id)
            facts["adjust_error"] = str(exc)[:300]
        row.facts_json = dict(facts)
        session.commit()
    return _result(row)


def _result(row: AgentCapture, *, duplicate: bool = False) -> dict:
    return {
        "id": row.id,
        "source": row.source,
        "day": row.day.isoformat(),
        "facts": row.facts_json,
        "plan_run_id": row.plan_run_id,
        "duplicate": duplicate,
        "created_at": row.created_at.isoformat(),
    }


def recent_captures(session: Session, limit: int = 20) -> list[dict]:
    rows = session.scalars(select(AgentCapture).order_by(AgentCapture.created_at.desc()).limit(limit)).all()
    return [_result(row) for row in rows]
