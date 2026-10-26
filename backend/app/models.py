"""SQLAlchemy 数据模型。"""

from __future__ import annotations

import uuid
from datetime import date as date_type
from datetime import datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def new_id() -> str:
    return uuid.uuid4().hex[:16]


def now() -> datetime:
    return datetime.now().replace(microsecond=0)


class Task(Base):
    """待办池中的一个任务（可被排进日历多次，例如分段完成）。"""

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(200))
    notes: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(20), default="study")
    cognitive_type: Mapped[str] = mapped_column(String(20), default="deep")  # deep/shallow/physical/social/rest
    energy_demand: Mapped[str] = mapped_column(String(10), default="high")  # high/medium/low
    estimate_min: Mapped[int] = mapped_column(Integer, default=45)
    priority: Mapped[int] = mapped_column(Integer, default=3)  # 1=最高 … 5=最低
    due_date: Mapped[date_type | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/scheduled/done/partial/skipped/dropped
    source: Mapped[str] = mapped_column(String(20), default="manual")  # manual/nl/import
    project: Mapped[str] = mapped_column(String(80), default="")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class Event(Base):
    """日历上的一个时间方块。"""

    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    task_id: Mapped[str | None] = mapped_column(String(24), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    notes: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(20), default="study")
    kind: Mapped[str] = mapped_column(String(20), default="focus")  # focus/study/admin/exercise/meal/rest/break/social/fixed/commute/buffer
    start: Mapped[datetime] = mapped_column(DateTime)
    end: Mapped[datetime] = mapped_column(DateTime)
    plan_date: Mapped[date_type] = mapped_column(Date, index=True)
    locked: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="planned")  # planned/done/partial/skipped/moved
    actual_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quality: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    reason: Mapped[str] = mapped_column(Text, default="")
    rule_ids: Mapped[list] = mapped_column(JSON, default=list)
    plan_run_id: Mapped[str | None] = mapped_column(String(24), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class Feedback(Base):
    """每日反馈。"""

    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    date: Mapped[date_type] = mapped_column(Date, unique=True, index=True)
    sleep_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    sleep_quality: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    energy_morning: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    energy_afternoon: Mapped[int | None] = mapped_column(Integer, nullable=True)
    energy_evening: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mood: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class Profile(Base):
    """个人作息 / 习惯 / 状态档案（单行）。"""

    __tablename__ = "profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    wake_time: Mapped[str] = mapped_column(String(5), default="07:00")
    sleep_time: Mapped[str] = mapped_column(String(5), default="23:30")
    chronotype: Mapped[str] = mapped_column(String(20), default="neutral")  # morning/neutral/evening
    max_focus_min: Mapped[int] = mapped_column(Integer, default=90)
    preferred_block_min: Mapped[int] = mapped_column(Integer, default=45)
    break_min: Mapped[int] = mapped_column(Integer, default=10)
    lunch_start: Mapped[str] = mapped_column(String(5), default="12:00")
    lunch_end: Mapped[str] = mapped_column(String(5), default="13:00")
    dinner_start: Mapped[str] = mapped_column(String(5), default="18:00")
    dinner_end: Mapped[str] = mapped_column(String(5), default="19:00")
    energy_curve: Mapped[list] = mapped_column(JSON, default=list)  # 24 项，1-5
    fixed_commitments: Mapped[list] = mapped_column(JSON, default=list)
    preferences: Mapped[list] = mapped_column(JSON, default=list)
    goals: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class MemoryDigest(Base):
    """滚动记忆摘要（近一月完成情况等的叙述版，供规划 prompt 注入）。"""

    __tablename__ = "memory_digests"

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    kind: Mapped[str] = mapped_column(String(20), default="rolling28")  # rolling28/weekly
    period_start: Mapped[date_type] = mapped_column(Date)
    period_end: Mapped[date_type] = mapped_column(Date)
    summary_md: Mapped[str] = mapped_column(Text, default="")
    stats_json: Mapped[dict] = mapped_column(JSON, default=dict)
    engine: Mapped[str] = mapped_column(String(20), default="rule")  # rule/llm
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)


class PlanRun(Base):
    """一次 AI 规划调用记录，便于回溯与调参。"""

    __tablename__ = "plan_runs"

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    plan_date: Mapped[date_type] = mapped_column(Date, index=True)
    mode: Mapped[str] = mapped_column(String(20), default="new")  # new/adjust
    input_text: Mapped[str] = mapped_column(Text, default="")
    engine: Mapped[str] = mapped_column(String(20), default="llm")  # llm/fallback
    model: Mapped[str] = mapped_column(String(60), default="")
    status: Mapped[str] = mapped_column(String(20), default="ok")  # ok/error/fallback
    error: Mapped[str] = mapped_column(Text, default="")
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    events_created: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    raw_response: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
