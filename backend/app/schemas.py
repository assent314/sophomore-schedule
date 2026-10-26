"""API 请求/响应模型（Pydantic v2）。"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Category = Literal["study", "work", "exercise", "life", "admin", "rest", "social", "fixed"]
Kind = Literal[
    "focus", "study", "admin", "exercise", "meal", "rest", "break", "social", "fixed", "commute", "buffer"
]
Status = Literal["planned", "done", "partial", "skipped", "moved"]
TaskStatus = Literal["pending", "scheduled", "done", "partial", "skipped", "dropped"]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Task ----------
class TaskOut(ORMModel):
    id: str
    title: str
    notes: str = ""
    category: str = "study"
    cognitive_type: str = "deep"
    energy_demand: str = "high"
    estimate_min: int = 45
    priority: int = 3
    due_date: date | None = None
    status: str = "pending"
    source: str = "manual"
    project: str = ""
    tags: list = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class TaskCreate(BaseModel):
    title: str
    notes: str = ""
    category: Category = "study"
    cognitive_type: Literal["deep", "shallow", "physical", "social", "rest"] = "deep"
    energy_demand: Literal["high", "medium", "low"] = "high"
    estimate_min: int = 45
    priority: int = 3
    due_date: date | None = None
    status: TaskStatus = "pending"
    source: str = "manual"
    project: str = ""
    tags: list = Field(default_factory=list)


class TaskUpdate(BaseModel):
    title: str | None = None
    notes: str | None = None
    category: Category | None = None
    cognitive_type: Literal["deep", "shallow", "physical", "social", "rest"] | None = None
    energy_demand: Literal["high", "medium", "low"] | None = None
    estimate_min: int | None = None
    priority: int | None = None
    due_date: date | None = None
    status: TaskStatus | None = None
    project: str | None = None
    tags: list | None = None


# ---------- Event ----------
class EventOut(ORMModel):
    id: str
    task_id: str | None = None
    title: str
    notes: str = ""
    category: str = "study"
    kind: str = "focus"
    start: datetime
    end: datetime
    plan_date: date
    locked: bool = False
    status: str = "planned"
    actual_min: int | None = None
    quality: int | None = None
    reason: str = ""
    rule_ids: list = Field(default_factory=list)
    plan_run_id: str | None = None
    created_at: datetime
    updated_at: datetime


class EventCreate(BaseModel):
    title: str
    start: datetime
    end: datetime
    notes: str = ""
    category: Category = "study"
    kind: Kind = "focus"
    task_id: str | None = None
    locked: bool = False
    reason: str = ""
    rule_ids: list = Field(default_factory=list)
    # 仅用于导入类事件打标签（如课表导入 "course-import"），正常手动创建留空即可
    plan_run_id: str | None = None


class EventUpdate(BaseModel):
    title: str | None = None
    notes: str | None = None
    category: Category | None = None
    kind: Kind | None = None
    start: datetime | None = None
    end: datetime | None = None
    locked: bool | None = None
    status: Status | None = None
    actual_min: int | None = None
    quality: int | None = None
    task_id: str | None = None


# ---------- Feedback ----------
class FeedbackOut(ORMModel):
    id: str
    date: date
    sleep_hours: float | None = None
    sleep_quality: int | None = None
    energy_morning: int | None = None
    energy_afternoon: int | None = None
    energy_evening: int | None = None
    mood: int | None = None
    notes: str = ""
    updated_at: datetime


class FeedbackUpsert(BaseModel):
    sleep_hours: float | None = None
    sleep_quality: int | None = None
    energy_morning: int | None = None
    energy_afternoon: int | None = None
    energy_evening: int | None = None
    mood: int | None = None
    notes: str | None = None


# ---------- Profile ----------
class FixedCommitment(BaseModel):
    title: str
    weekdays: list[int] = Field(default_factory=list)  # 0=周一 … 6=周日；空=每天
    start: str = "09:00"
    end: str = "10:00"
    category: Category = "fixed"
    kind: Kind = "fixed"


class ProfileOut(ORMModel):
    wake_time: str
    sleep_time: str
    chronotype: str
    max_focus_min: int
    preferred_block_min: int
    break_min: int
    lunch_start: str
    lunch_end: str
    dinner_start: str
    dinner_end: str
    energy_curve: list
    fixed_commitments: list
    preferences: list
    goals: list
    notes: str = ""
    updated_at: datetime


class ProfileUpdate(BaseModel):
    wake_time: str | None = None
    sleep_time: str | None = None
    chronotype: Literal["morning", "neutral", "evening"] | None = None
    max_focus_min: int | None = None
    preferred_block_min: int | None = None
    break_min: int | None = None
    lunch_start: str | None = None
    lunch_end: str | None = None
    dinner_start: str | None = None
    dinner_end: str | None = None
    energy_curve: list[int] | None = None
    fixed_commitments: list[FixedCommitment] | None = None
    preferences: list[str] | None = None
    goals: list[str] | None = None
    notes: str | None = None


# ---------- Planning ----------
class PlanRequest(BaseModel):
    date: date
    text: str = ""
    mode: Literal["new", "adjust"] = "new"
    replace_ai_blocks: bool = True
    keep_done: bool = True
    extra_constraints: list[str] = Field(default_factory=list)
    save_tasks: bool = True


class PlannedBlock(BaseModel):
    title: str
    start: str  # ISO datetime 或 HH:MM
    end: str
    kind: Kind = "focus"
    category: Category = "study"
    task_id: str | None = None
    task_ref: str | None = None
    notes: str = ""
    reason: str = ""
    rule_ids: list[str] = Field(default_factory=list)
    locked: bool = False


class PlanApplyRequest(BaseModel):
    """把预览结果原样落库（不再调用 LLM，保证所见即所得）。"""

    date: date
    blocks: list[PlannedBlock]
    plan_run_id: str | None = None
    mode: Literal["new", "adjust"] = "new"
    replace_ai_blocks: bool = True
    keep_done: bool = True


class PlanResponse(BaseModel):
    plan_run_id: str
    engine: str
    events: list[EventOut]
    notes: str = ""
    questions: list[str] = Field(default_factory=list)
    adjustments: list[str] = Field(default_factory=list)
    rule_ids_used: list[str] = Field(default_factory=list)
    memory_used: bool = False
    usage: dict[str, Any] = Field(default_factory=dict)


class PlanPreviewResponse(BaseModel):
    plan_run_id: str
    engine: str
    blocks: list[dict]
    notes: str = ""
    questions: list[str] = Field(default_factory=list)
    adjustments: list[str] = Field(default_factory=list)


# ---------- Stats / memory ----------
class DayCompletion(BaseModel):
    date: date
    planned_min: int
    done_min: int
    completion_rate: float
    blocks_planned: int
    blocks_done: int


class StatsOverview(BaseModel):
    days: int
    period_start: date
    period_end: date
    total_planned_min: int
    total_done_min: int
    completion_rate: float
    by_category: list[dict]
    by_hour_bucket: list[dict]
    by_weekday: list[dict]
    estimate_accuracy: dict
    daily: list[DayCompletion]
    feedback_trend: list[dict]
    top_insights: list[str] = Field(default_factory=list)


class MemoryOut(BaseModel):
    kind: str
    period_start: date
    period_end: date
    summary_md: str
    stats: dict = Field(default_factory=dict)
    engine: str = "rule"
    created_at: datetime | None = None
    stale: bool = False


# ---------- Settings ----------
class SettingsOut(BaseModel):
    llm_model: str
    llm_base_url: str
    timezone: str
    plan_buffer_ratio: str
    llm_timeout_seconds: str
    has_api_key: bool
    api_key_preview: str = ""
    llm_online: bool | None = None


class SettingsUpdate(BaseModel):
    llm_api_key: str | None = None
    llm_model: str | None = None
    llm_base_url: str | None = None
    timezone: str | None = None
    plan_buffer_ratio: str | None = None
    llm_timeout_seconds: str | None = None


class RuleOut(BaseModel):
    id: str
    name: str
    category: str
    summary: str
    mechanism: str
    scheduling_effect: list[str]
    evidence_strength: str
    citations: list[dict]
