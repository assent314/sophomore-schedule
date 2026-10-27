"""排程引擎：规则排程 + LLM 排程 + 校验落库。"""

from __future__ import annotations

import json
import hashlib
from collections import defaultdict
from datetime import date as date_type
from datetime import datetime, time, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from . import config, knowledge, nl, stats
from .llm import DeepSeekClient, LLMError
from .models import Event, Feedback, MemoryDigest, PlanRun, Profile, Task
from .settings_store import effective_settings
from .time_utils import local_now

GRID_MIN = 15
MIN_BLOCK_MIN = 10


# --------------------------------------------------------------------------- 时间工具
def _combine(d: date_type, hhmm: str) -> datetime:
    hh, mm = (hhmm or "00:00").split(":")[:2]
    return datetime.combine(d, time(int(hh), int(mm)))


def _ceil_dt(dt: datetime, grid: int = GRID_MIN) -> datetime:
    base = dt.replace(second=0, microsecond=0)
    rem = base.minute % grid
    if rem or dt.second:
        base = base + timedelta(minutes=(grid - rem) if rem else 0)
    return base


def _min_of_day(dt: datetime) -> int:
    return dt.hour * 60 + dt.minute


def _energy_at(curve: list[int], dt: datetime) -> float:
    if not curve:
        curve = knowledge.DEFAULT_ENERGY_CURVE
    return float(curve[dt.hour % 24])


def _avg_energy(curve: list[int], start: datetime, end: datetime) -> float:
    total = 0.0
    minutes = 0
    cursor = start
    while cursor < end:
        step = min(15, int((end - cursor).total_seconds() // 60))
        total += _energy_at(curve, cursor) * step
        minutes += step
        cursor += timedelta(minutes=step)
    return total / minutes if minutes else 0.0


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


COURSE_IMPORT_TAG = "course-import"
ROUTINE_PLAN_TAG = "routine-plan"


def _is_protected_event(ev: Event) -> bool:
    """已有事件里，哪些必须被排程避开 / 重排时不能删。

    - locked：用户锁定的方块；
    - plan_run_id == "course-import"：从课表 PDF 导入的课程（设计上只展示、可拖动，但占时间）；
    - plan_run_id == "routine-plan"：睡眠和用餐时间（展示并占时间，但不计完成率）；
    - kind == "fixed"：固定安排类事件（课表、会议）。
    """
    if ev.locked:
        return True
    if (ev.plan_run_id or "") in {COURSE_IMPORT_TAG, ROUTINE_PLAN_TAG}:
        return True
    return (ev.kind or "") == "fixed"


def _must_preserve(ev: Event, run_ids: set[str], *, mode: str, now_dt: datetime,
                   replace_ai_blocks: bool, keep_done: bool) -> bool:
    """手动事件、已完成事件和过去的事件永远不被自动排程覆盖。"""
    return (
        _is_protected_event(ev)
        or not replace_ai_blocks
        or ev.plan_run_id not in run_ids
        or ev.status in {"done", "partial"}
        or ev.start < now_dt
    )


def context_revision(ctx: dict) -> str:
    """预览所依据的事实版本；新增/编辑事件或状态后必须重新预览。"""
    stable = {key: ctx[key] for key in ("profile", "tasks", "events", "feedbacks", "memory_text", "buffer_ratio", "timezone")}
    encoded = json.dumps(stable, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


# --------------------------------------------------------------------------- 上下文
def get_profile(session: Session) -> Profile:
    prof = session.get(Profile, 1)
    if prof is None:
        prof = Profile(id=1, **knowledge.DEFAULT_PROFILE)
        session.add(prof)
        session.commit()
    return prof


def profile_to_dict(prof: Profile) -> dict:
    return {
        "wake_time": prof.wake_time,
        "sleep_time": prof.sleep_time,
        "chronotype": prof.chronotype,
        "max_focus_min": prof.max_focus_min,
        "preferred_block_min": prof.preferred_block_min,
        "break_min": prof.break_min,
        "lunch_start": prof.lunch_start,
        "lunch_end": prof.lunch_end,
        "dinner_start": prof.dinner_start,
        "dinner_end": prof.dinner_end,
        "energy_curve": prof.energy_curve or knowledge.DEFAULT_ENERGY_CURVE,
        "fixed_commitments": prof.fixed_commitments or [],
        "preferences": prof.preferences or [],
        "goals": prof.goals or [],
        "notes": prof.notes or "",
    }


def _task_dict(t: Task) -> dict:
    return {
        "id": t.id,
        "title": t.title,
        "notes": t.notes or "",
        "category": t.category,
        "cognitive_type": t.cognitive_type,
        "energy_demand": t.energy_demand,
        "estimate_min": t.estimate_min,
        "priority": t.priority,
        "due_date": t.due_date.isoformat() if t.due_date else None,
        "project": t.project or "",
        "tags": t.tags or [],
    }


def _event_dict(e: Event) -> dict:
    return {
        "id": e.id,
        "title": e.title,
        "kind": e.kind,
        "category": e.category,
        "start": _iso(e.start),
        "end": _iso(e.end),
        "locked": bool(e.locked),
        "status": e.status,
    }


def _fixed_blocks(plan_date: date_type, prof: dict) -> list[dict]:
    """档案里的固定安排 + 三餐。"""
    blocks: list[dict] = []
    weekday = plan_date.weekday()
    for item in prof.get("fixed_commitments") or []:
        weekdays = item.get("weekdays") or []
        if weekdays and weekday not in weekdays:
            continue
        try:
            s = _combine(plan_date, item.get("start", "09:00"))
            e = _combine(plan_date, item.get("end", "10:00"))
        except (ValueError, TypeError):
            continue
        if e <= s:
            e = s + timedelta(minutes=60)
        blocks.append(
            {
                "title": item.get("title") or "固定安排",
                "start": s,
                "end": e,
                "kind": "fixed",
                "category": item.get("category") or "fixed",
            }
        )
    for key_s, key_e, title in (
        ("lunch_start", "lunch_end", "午餐"),
        ("dinner_start", "dinner_end", "晚餐"),
    ):
        try:
            s = _combine(plan_date, prof.get(key_s) or "00:00")
            e = _combine(plan_date, prof.get(key_e) or "00:00")
        except (ValueError, TypeError):
            continue
        if e > s:
            blocks.append({"title": title, "start": s, "end": e, "kind": "meal", "category": "life"})
    return blocks


def day_window(plan_date: date_type, prof: dict, now_dt: datetime) -> tuple[datetime, datetime]:
    start = _combine(plan_date, prof.get("wake_time") or "07:00")
    end = _combine(plan_date, prof.get("sleep_time") or "23:30")
    if end <= start:
        end += timedelta(days=1)
    if plan_date == now_dt.date():
        start = max(start, _ceil_dt(now_dt + timedelta(minutes=5)))
    return start, end


def subtract(window: tuple[datetime, datetime], occupied: list[tuple[datetime, datetime]]) -> list[list[datetime]]:
    start, end = window
    free: list[list[datetime]] = [[start, end]]
    for o_s, o_e in sorted(occupied):
        nxt: list[list[datetime]] = []
        for f_s, f_e in free:
            if o_e <= f_s or o_s >= f_e:
                nxt.append([f_s, f_e])
                continue
            if o_s > f_s:
                nxt.append([f_s, min(o_s, f_e)])
            if o_e < f_e:
                nxt.append([max(o_e, f_s), f_e])
        free = [seg for seg in nxt if (seg[1] - seg[0]).total_seconds() >= 300]
    return free


def _take_from_free(free: list[list[datetime]], start: datetime, end: datetime) -> None:
    new_free: list[list[datetime]] = []
    for f_s, f_e in free:
        if end <= f_s or start >= f_e:
            new_free.append([f_s, f_e])
            continue
        if start > f_s:
            new_free.append([f_s, start])
        if end < f_e:
            new_free.append([end, f_e])
    free[:] = [seg for seg in new_free if (seg[1] - seg[0]).total_seconds() >= 300]


# --------------------------------------------------------------------------- 上下文
def build_context(
    session: Session,
    plan_date: date_type,
    *,
    mode: str = "new",
    replace_ai_blocks: bool = True,
    keep_done: bool = True,
    extra_constraints: list[str] | None = None,
    now_dt: datetime | None = None,
) -> dict:
    now_dt = now_dt or local_now(session).replace(second=0, microsecond=0)
    prof = profile_to_dict(get_profile(session))
    tasks = session.scalars(
        select(Task)
        .where(Task.status.in_(["pending", "scheduled", "partial"]))
        .order_by(Task.priority.asc(), Task.estimate_min.desc())
    ).all()
    events = session.scalars(
        select(Event).where(Event.plan_date == plan_date).order_by(Event.start.asc())
    ).all()
    run_ids = set(session.scalars(select(PlanRun.id).where(PlanRun.plan_date == plan_date)).all())
    fb_rows = session.scalars(
        select(Feedback).order_by(Feedback.date.desc()).limit(14)
    ).all()
    feedbacks = [
        {
            "date": f.date.isoformat(),
            "sleep_hours": f.sleep_hours,
            "sleep_quality": f.sleep_quality,
            "energy_morning": f.energy_morning,
            "energy_afternoon": f.energy_afternoon,
            "energy_evening": f.energy_evening,
            "mood": f.mood,
            "notes": f.notes,
        }
        for f in fb_rows
    ]
    yesterday = next((f for f in feedbacks if f["date"] == (plan_date - timedelta(days=1)).isoformat()), None)
    current_feedback = next((f for f in feedbacks if f["date"] == plan_date.isoformat()), None)
    window = day_window(plan_date, prof, now_dt)
    fixed = [
        {**block, "start": max(block["start"], window[0])}
        for block in _fixed_blocks(plan_date, prof)
        if block["end"] > window[0] and block["start"] < window[1]
    ]
    # 所有会保留下来的事件都应在预览时占位，包括手动添加和已经完成的方块。
    locked = [
        {"title": ev.title, "start": ev.start, "end": ev.end, "kind": ev.kind, "category": ev.category}
        for ev in events
        if _must_preserve(ev, run_ids, mode=mode, now_dt=now_dt,
                          replace_ai_blocks=replace_ai_blocks, keep_done=keep_done)
    ]
    # 档案中的用餐/固定块若与已有手动或课程事件冲突，以日历上的实际事件为准。
    fixed = [b for b in fixed if not any(
        b["start"] < existing["end"] and existing["start"] < b["end"]
        for existing in locked
    )]
    occupied = [(b["start"], b["end"]) for b in fixed] + [(b["start"], b["end"]) for b in locked]
    free = subtract(window, occupied)
    free_min = sum(int((e - s).total_seconds() // 60) for s, e in free)
    settings = effective_settings(session)
    return {
        "plan_date": plan_date,
        "now": now_dt,
        "mode": mode,
        "profile": prof,
        "tasks": [_task_dict(t) for t in tasks],
        "events": [_event_dict(e) for e in events],
        "feedbacks": feedbacks,
        "yesterday": yesterday,
        "current_feedback": current_feedback,
        "window": window,
        "fixed_blocks": fixed,
        "locked_blocks": locked,
        "preserve_ids": {ev.id for ev in events if _must_preserve(
            ev, run_ids, mode=mode, now_dt=now_dt,
            replace_ai_blocks=replace_ai_blocks, keep_done=keep_done)},
        "occupied": occupied,
        "free": free,
        "free_min": free_min,
        "extra_constraints": extra_constraints or [],
        "buffer_ratio": max(0.0, min(0.8, float(settings["plan_buffer_ratio"]))),
        "timezone": settings["timezone"],
        "memory_text": stats.compact_for_prompt(session, now_dt.date()),
        "stats": stats.overview(session, days=28, today=now_dt.date()),
        "llm": _llm_info(session),
    }


def _llm_info(session: Session) -> dict:
    from .settings_store import effective_settings

    st = effective_settings(session)
    return {
        "available": bool(st.get("llm_api_key")),
        "model": st.get("llm_model", ""),
        "base_url": st.get("llm_base_url", ""),
    }


# --------------------------------------------------------------------------- 规则排程
_ROLE_BY_KIND = {
    "focus": "deep",
    "study": "deep",
    "admin": "light",
    "social": "light",
    "exercise": "move",
    "rest": "rest",
}

_DEEP_TYPES = {"deep"}
_LIGHT_TYPES = {"shallow", "social"}


def _classify_task(t: dict) -> str:
    cat = t.get("category")
    cog = t.get("cognitive_type")
    if cat == "exercise":
        return "move"
    if cat in {"rest"}:
        return "rest"
    if cat in {"life", "admin"}:
        return "light"
    if cog == "physical":
        return "move"
    if cog and cog in _LIGHT_TYPES:
        return "light"
    return "deep"


def _score_slot(role: str, start: datetime, end: datetime, curve: list[int], edges: set[datetime]) -> float:
    e = _avg_energy(curve, start, end)
    hour = start.hour
    score = 0.0
    if role == "deep":
        score += e * 12
        if 8 <= hour <= 12:
            score += 6
        if hour >= 21:
            score -= 14
    elif role == "light":
        score += (5.5 - e) * 6
        if 13 <= hour <= 17:
            score += 5
        if e < 1.5:
            score -= 4
    elif role == "move":
        score += 8 if 15 <= hour <= 18 else 0
        score += 3 if 7 <= hour <= 9 else 0
        score += (5.5 - e) * 2
    elif role == "rest":
        score += 8 if 13 <= hour <= 15 else 0
        score += (5.5 - e) * 2
    if start in edges:
        score += 3
    if end in edges:
        score += 2
    return score


def _pick_slot(
    free: list[list[datetime]],
    duration: int,
    role: str,
    curve: list[int],
    edges: set[datetime],
) -> tuple[datetime, datetime] | None:
    best: tuple[float, datetime, datetime] | None = None
    for f_s, f_e in free:
        cursor = _ceil_dt(f_s)
        while cursor + timedelta(minutes=duration) <= f_e:
            end = cursor + timedelta(minutes=duration)
            score = _score_slot(role, cursor, end, curve, edges)
            if best is None or score > best[0]:
                best = (score, cursor, end)
            cursor += timedelta(minutes=GRID_MIN)
        if best is None:
            # 允许比网格更晚开始
            pass
    if best is None:
        # 最后尝试：贴边放下
        for f_s, f_e in free:
            if (f_e - f_s).total_seconds() // 60 >= duration:
                return _ceil_dt(f_s), _ceil_dt(f_s) + timedelta(minutes=duration)
    return (best[1], best[2]) if best else None


def _block(
    title: str,
    start: datetime,
    end: datetime,
    kind: str,
    category: str,
    *,
    task_id: str | None = None,
    notes: str = "",
    reason: str = "",
    rule_ids: list[str] | None = None,
    locked: bool = False,
) -> dict:
    return {
        "title": title,
        "start": _iso(start),
        "end": _iso(end),
        "kind": kind,
        "category": category,
        "task_id": task_id,
        "notes": notes,
        "reason": reason,
        "rule_ids": rule_ids or [],
        "locked": locked,
    }


def rule_plan(ctx: dict) -> dict:
    prof = ctx["profile"]
    curve = list(prof.get("energy_curve") or knowledge.DEFAULT_ENERGY_CURVE)
    current_feedback = ctx.get("current_feedback") or {}
    for key, hours in (
        ("energy_morning", range(6, 12)),
        ("energy_afternoon", range(12, 18)),
        ("energy_evening", range(18, 24)),
    ):
        if current_feedback.get(key) is not None:
            for hour in hours:
                curve[hour] = int(current_feedback[key])
    free = [list(seg) for seg in ctx["free"]]
    edges: set[datetime] = set()
    for seg in free:
        edges.add(seg[0])
        edges.add(seg[1])
    for b in ctx["fixed_blocks"]:
        edges.add(b["start"])
        edges.add(b["end"])

    max_focus = max(25, min(int(prof.get("max_focus_min") or 90), 120))
    pref_block = max(25, min(int(prof.get("preferred_block_min") or 45), max_focus))
    break_min = max(5, min(int(prof.get("break_min") or 10), 30))
    buffer_ratio = ctx.get("buffer_ratio")
    if buffer_ratio is None:
        buffer_ratio = 0.15
    capacity = int(ctx["free_min"] * (1 - buffer_ratio))
    sleep_hours = current_feedback.get("sleep_hours")
    if sleep_hours is None:
        sleep_hours = (ctx.get("yesterday") or {}).get("sleep_hours")
    notes: list[str] = []
    questions: list[str] = []
    rule_ids: list[str] = ["planning_fallacy_buffer", "circadian_peak", "micro_break"]

    if sleep_hours is not None and sleep_hours < 6:
        capacity = int(capacity * 0.6)
        notes.append(f"昨夜睡眠 {sleep_hours}h，今日任务量自动下调约 40%，优先完成最重要的 1 个深度块。")
        rule_ids += ["sleep_sufficiency"]
    elif sleep_hours is not None and sleep_hours < 7:
        capacity = int(capacity * 0.8)
        notes.append(f"昨夜睡眠 {sleep_hours}h，任务量下调约 20%，午后建议 15–20 分钟小睡。")
        rule_ids += ["sleep_sufficiency", "nap_consolidation"]

    blocks: list[dict] = []
    placed_min = 0
    deferred: list[dict] = []

    # 固定安排与三餐先落
    for b in ctx["fixed_blocks"]:
        blocks.append(
            _block(
                b["title"],
                b["start"],
                b["end"],
                b["kind"],
                b["category"],
                reason="档案中的固定安排/用餐时间",
                rule_ids=["sleep_consistency"] if b["kind"] == "meal" else [],
                locked=True,
            )
        )

    tasks = sorted(
        ctx["tasks"],
        key=lambda t: (
            int(t.get("priority") or 3),
            t.get("due_date") or "9999-12-31",
            -int(t.get("estimate_min") or 45),
        ),
    )
    if not tasks:
        questions.append("今天想做点什么呢？可以按「做什么 + 大概多久」描述，例如：复习线代 1 小时、写论文 2 小时。")

    for task in tasks:
        role = _classify_task(task)
        remaining = int(task.get("estimate_min") or 45)
        placed_this = 0
        while remaining >= 15:
            chunk = pref_block if remaining > pref_block else remaining
            if chunk < 20:
                chunk = remaining
            # 深度块不能超过 max_focus
            chunk = min(chunk, max_focus)
            # 放不下时逐步缩短
            slot = None
            for trial in (chunk, max(25, chunk // 2), 20):
                if trial < 15:
                    continue
                slot = _pick_slot(free, trial, role, curve, edges)
                if slot:
                    chunk = trial
                    break
            if not slot:
                break
            if placed_min + chunk > capacity:
                slot = None
                break
            start, end = slot
            reason_parts = []
            if role == "deep":
                reason_parts.append(f"放在能量较高时段（{start:%H:%M} 前后能量 {_avg_energy(curve, start, end):.1f}/5）")
                reason_parts.append("单块不超过 90 分钟，避免警觉性衰减")
            elif role == "light":
                reason_parts.append("机械/事务类任务安排在精力较低时段，把峰值时段留给深度任务")
            elif role == "move":
                reason_parts.append("运动安排在午后低谷，兼顾执行功能恢复与情绪")
            rules = {
                "deep": ["circadian_peak", "ultradian_block", "retrieval_practice"],
                "light": ["circadian_peak", "task_switching_cost"],
                "move": ["exercise_aerobic"],
                "rest": ["micro_break"],
            }[role]
            blocks.append(
                _block(
                    task["title"],
                    start,
                    end,
                    "exercise" if role == "move" else ("admin" if role == "light" else "focus"),
                    task.get("category") or ("exercise" if role == "move" else "study"),
                    task_id=task.get("id"),
                    notes=task.get("notes") or "",
                    reason="；".join(reason_parts),
                    rule_ids=rules,
                )
            )
            _take_from_free(free, start, end)
            edges.update({start, end})
            remaining -= chunk
            placed_this += chunk
            placed_min += chunk
            # 块后休息
            if break_min and remaining > 0:
                for f_s, f_e in list(free):
                    if f_s - end <= timedelta(minutes=GRID_MIN) and (f_e - end).total_seconds() // 60 >= break_min:
                        b_start, b_end = end, end + timedelta(minutes=break_min)
                        blocks.append(
                            _block(
                                "短休息",
                                b_start,
                                b_end,
                                "break",
                                "rest",
                                reason="任务块之间留出真休息，防止注意资源持续衰减",
                                rule_ids=["micro_break"],
                            )
                        )
                        _take_from_free(free, b_start, b_end)
                        edges.update({b_start, b_end})
                        break
                    break
        if remaining > 0:
            deferred.append({**task, "left_min": remaining})

    # 缓冲块
    buffer_slot = None
    for trial in (30, 25, 20):
        buffer_slot = _pick_slot(free, trial, "light", curve, edges)
        if buffer_slot:
            b_start, b_end = buffer_slot
            blocks.append(
                _block(
                    "缓冲 / 收尾",
                    b_start,
                    b_end,
                    "buffer",
                    "admin",
                    notes="如果到点你就整理今天未完成的下一步",
                    reason="留出 20–30 分钟应对规划谬误与意外",
                    rule_ids=["planning_fallacy_buffer", "implementation_intentions"],
                )
            )
            _take_from_free(free, b_start, b_end)
            break

    if deferred:
        names = "、".join(f"{d['title']}（剩 {d['left_min']} 分钟）" for d in deferred[:5])
        notes.append(f"以下任务今天时间不够，建议顺延或拆小：{names}")
        rule_ids.append("procrastination_low_friction")
    if placed_min > 0 and sleep_hours is None:
        notes.append("还没有昨天的睡眠/精力反馈，今天的强度按默认档位估计。")
        questions.append("昨晚睡了多少小时？今天上午/下午/晚上的精力大概几分（1–5）？")

    blocks.sort(key=lambda b: b["start"])
    return {
        "engine": "rule",
        "blocks": blocks,
        "notes": "\n".join(notes),
        "questions": questions,
        "adjustments": [],
        "rule_ids_used": sorted(set(rule_ids) | {r for b in blocks for r in b["rule_ids"]}),
        "usage": {},
        "raw": "",
        "deferred": deferred,
    }


# --------------------------------------------------------------------------- LLM 排程
_SYSTEM_PROMPT = """你是一个「学习科学排程引擎」，把用户今天要做的事排进日历方块。
你的排程必须基于给出的规则卡（神经科学 / 认知心理学实证结论），每个方块都要能追溯到规则 id。

输出要求：只输出一个 JSON 对象，不要任何解释文字，结构如下：
{
  "task_updates": [
    {"title": "任务名", "category": "study|work|exercise|life|admin|rest|social",
     "cognitive_type": "deep|shallow|physical|social|rest", "estimate_min": 45,
     "priority": 1, "due_date": "2026-10-25 或 null", "notes": "", "project": ""}
  ],
  "blocks": [
    {"title": "方块标题", "start": "YYYY-MM-DDTHH:MM:SS", "end": "YYYY-MM-DDTHH:MM:SS",
     "kind": "focus|study|admin|exercise|meal|rest|break|social|fixed|commute|buffer",
     "category": "study|work|exercise|life|admin|rest|social|fixed",
     "task_ref": "对应 task_updates 里某个 title（没有就填 null）",
     "notes": "给用户看的一句话说明，可写 if-then 实施意向",
     "reason": "为什么排在这个时间/长度（一句话）",
     "rule_ids": ["circadian_peak"], "locked": false}
  ],
  "notes": "整体说明，可多行，1-4 句",
  "questions": ["信息不足需要问用户的问题，没有就空数组"],
  "adjustments": ["相对用户原始描述的调整及原因，没有就空数组"]
}

硬性约束：
0. 先解析「用户今天的自然语言描述」：把描述的每件事拆成 task_updates，标题要保留用户说的具体主题（如「概率论第三章」「两套真题」「后端接口」「间隔重复论文」），不要笼统替换成「数学练习」「英语单词」这类模板名；排进 blocks 的方块标题也要对应这些具体任务；
1. 所有时间必须在给定的「可排时间窗」内，且不能与「已占用时段」重叠；
2. 每个 focus/study 块 25–90 分钟；深度任务优先放能量曲线高的时段；
3. 块与块之间留 5–15 分钟间隔或休息块；深度任务不要贴着睡前一小时；
4. 排入任务总量不超过可排时长的 85%，排不下的不要硬塞，写进 notes；
5. task_ref 与 task_updates 的 title 保持一致，便于关联；
6. 不要编造用户没说的事实；不确定的信息写进 questions；背景/活动类安排（健身、吃饭）按用户说的时段排；
7. 所有时间用本地时间（Asia/Shanghai），不带时区后缀。"""


def _fmt_curve(curve: list[int]) -> str:
    return " ".join(f"{h:02d}:{int(curve[h % 24])}" for h in range(7, 24))


def build_user_prompt(ctx: dict) -> str:
    prof = ctx["profile"]
    window = ctx["window"]
    parts: list[str] = []
    parts.append(f"# 今天\n日期：{ctx['plan_date']}（周{'一二三四五六日'[ctx['plan_date'].weekday()]}）")
    parts.append(f"当前时间：{ctx['now']:%Y-%m-%d %H:%M}")
    parts.append(f"可排时间窗：{window[0]:%H:%M} – {window[1]:%H:%M}（共 {ctx['free_min']} 分钟自由时间）")
    parts.append(f"模式：{'按现有日历调整剩下时间' if ctx['mode'] == 'adjust' else '新规划今天'}")

    parts.append("\n# 个人档案")
    parts.append(
        f"起床 {prof['wake_time']}，睡觉 {prof['sleep_time']}，作息类型 {prof['chronotype']}；"
        f"单块上限 {prof['max_focus_min']} 分钟，偏好块长 {prof['preferred_block_min']} 分钟，休息 {prof['break_min']} 分钟"
    )
    parts.append(f"能量曲线（每小时 1-5 分）：{_fmt_curve(prof['energy_curve'])}")
    if prof.get("preferences"):
        parts.append("个人偏好：" + "；".join(prof["preferences"]))
    if prof.get("goals"):
        parts.append("长期目标：" + "；".join(prof["goals"]))
    if prof.get("notes"):
        parts.append("补充说明：" + prof["notes"])

    parts.append("\n# 已占用时段（不可排任务）")
    for b in ctx["fixed_blocks"]:
        parts.append(f"- {b['start']:%H:%M}-{b['end']:%H:%M} {b['title']}（{'固定' if b['kind'] != 'meal' else '用餐'}）")
    for b in ctx["locked_blocks"]:
        parts.append(f"- {b['start']:%H:%M}-{b['end']:%H:%M} {b['title']}（已有安排，不可占用）")

    if ctx["mode"] == "adjust":
        parts.append("\n# 今日现有日历方块")
        for e in ctx["events"]:
            parts.append(f"- {e['start'][11:16]}-{e['end'][11:16]} {e['title']} [{e['kind']}/{e['status']}]")

    parts.append("\n# 用户今天的自然语言描述（这是最重要的输入，先据此拆任务）")
    parts.append((ctx.get("input_text") or "").strip() or "- （用户没写描述，按待办池排）")

    parts.append("\n# 待办任务（已有）")
    if ctx["tasks"]:
        for t in ctx["tasks"]:
            due = f"，截止 {t['due_date']}" if t["due_date"] else ""
            parts.append(
                f"- id={t['id']} | {t['title']} | {t['category']}/{t['cognitive_type']}"
                f" | 预估 {t['estimate_min']} 分钟 | 优先级 P{t['priority']}{due}"
            )
    else:
        parts.append("- （空）")

    parts.append("\n# 最近反馈")
    fb = ctx["feedbacks"][:7]
    if fb:
        for f in fb:
            bits = []
            if f["sleep_hours"] is not None:
                bits.append(f"睡眠{f['sleep_hours']}h")
            for key, label in (("energy_morning", "上午"), ("energy_afternoon", "下午"), ("energy_evening", "晚上")):
                if f[key] is not None:
                    bits.append(f"{label}精力{f[key]}")
            if f["mood"] is not None:
                bits.append(f"情绪{f['mood']}")
            parts.append(f"- {f['date']}：" + ("，".join(bits) if bits else "无量化数据") + (f"；{f['notes']}" if f["notes"] else ""))
    else:
        parts.append("- 暂无反馈数据")

    parts.append("\n# 近 28 天统计（滚动的完成情况记忆）")
    parts.append(ctx["memory_text"] or "- 暂无历史")

    parts.append("\n# 规则卡（rule_ids 只能从这里选）")
    parts.append(knowledge.rules_compact_for_prompt())

    if ctx["extra_constraints"]:
        parts.append("\n# 用户额外要求")
        for c in ctx["extra_constraints"]:
            parts.append(f"- {c}")
    return "\n".join(parts)


def normalize_blocks(raw_blocks: list[Any], ctx: dict, task_ref_map: dict[str, str]) -> list[dict]:
    plan_date = ctx["plan_date"]
    win_start, win_end = ctx["window"]
    occupied = [(b["start"], b["end"]) for b in ctx["fixed_blocks"]] + [
        (b["start"], b["end"]) for b in ctx["locked_blocks"]
    ]
    parsed: list[dict] = []
    for rb in raw_blocks or []:
        if not isinstance(rb, dict):
            continue
        title = str(rb.get("title") or "").strip()
        if not title:
            continue
        try:
            start = _parse_dt(rb.get("start"), plan_date)
            end = _parse_dt(rb.get("end"), plan_date)
        except (ValueError, TypeError):
            continue
        if end <= start:
            end = start + timedelta(minutes=45)
        # 夹到可用窗口
        start = max(start, win_start)
        end = min(end, win_end)
        if (end - start).total_seconds() // 60 < MIN_BLOCK_MIN:
            continue
        kind = str(rb.get("kind") or "focus")
        if kind not in knowledge.KIND_LABEL:
            kind = "focus"
        category = str(rb.get("category") or knowledge.KIND_CATEGORY.get(kind, "study"))
        if category not in knowledge.EVENT_CATEGORY_LABEL:
            category = knowledge.KIND_CATEGORY.get(kind, "study")
        rule_ids = [r for r in (rb.get("rule_ids") or []) if knowledge.get_rule(str(r))]
        task_ref = rb.get("task_ref")
        task_id = task_ref_map.get(str(task_ref)) if task_ref else None
        parsed.append(
            _block(
                title[:120],
                start,
                end,
                kind,
                category,
                task_id=task_id,
                notes=str(rb.get("notes") or "")[:500],
                reason=str(rb.get("reason") or "")[:300],
                rule_ids=rule_ids,
                locked=bool(rb.get("locked")),
            )
        )
    # 去掉与占用时段重叠的块
    keep: list[dict] = []
    for b in parsed:
        s = datetime.fromisoformat(b["start"])
        e = datetime.fromisoformat(b["end"])
        if any(s < o_e and e > o_s for o_s, o_e in occupied):
            continue
        keep.append(b)
    # 自身重叠处理
    keep.sort(key=lambda b: b["start"])
    result: list[dict] = []
    for b in keep:
        s = datetime.fromisoformat(b["start"])
        e = datetime.fromisoformat(b["end"])
        if result:
            prev_end = datetime.fromisoformat(result[-1]["end"])
            if s < prev_end:
                s = prev_end
                if s.minute % 5:
                    s = s + timedelta(minutes=5 - s.minute % 5)
                e = s + timedelta(minutes=max(MIN_BLOCK_MIN, (e - s).total_seconds() // 60))
                if e > win_end:
                    continue
                b["start"], b["end"] = _iso(s), _iso(e)
        if (e - s).total_seconds() // 60 < MIN_BLOCK_MIN:
            continue
        result.append(b)
    return result


def _parse_dt(value: Any, plan_date: date_type) -> datetime:
    if isinstance(value, datetime):
        return value
    s = str(value or "").strip()
    if not s:
        raise ValueError("empty datetime")
    if len(s) <= 5 and ":" in s:
        hh, mm = s.split(":")[:2]
        return datetime.combine(plan_date, time(int(hh), int(mm)))
    s = s.replace(" ", "T")
    s = s.removesuffix("Z")
    return datetime.fromisoformat(s)


async def llm_plan(ctx: dict) -> dict:
    from .settings_store import effective_settings

    st = effective_settings(ctx["_session"]) if ctx.get("_session") else {}
    client = DeepSeekClient(api_key=st.get("llm_api_key"), base_url=st.get("llm_base_url"),
                            timeout=float(st.get("llm_timeout_seconds") or 150))
    user_prompt = build_user_prompt(ctx)
    parsed, usage = await client.chat_json(
        _SYSTEM_PROMPT, user_prompt, model=st.get("llm_model"), temperature=0.25, max_tokens=6000
    )

    # 整理 LLM 返回的任务
    task_updates: list[dict] = []
    for tu in parsed.get("task_updates") or []:
        if not isinstance(tu, dict) or not str(tu.get("title") or "").strip():
            continue
        cat = tu.get("category") if tu.get("category") in knowledge.EVENT_CATEGORY_LABEL else "study"
        cog = tu.get("cognitive_type") if tu.get("cognitive_type") in {"deep", "shallow", "physical", "social", "rest"} else "deep"
        try:
            prio = int(tu.get("priority") or 3)
        except (TypeError, ValueError):
            prio = 3
        task_updates.append(
            {
                "title": str(tu["title"]).strip()[:200],
                "notes": str(tu.get("notes") or ""),
                "category": cat,
                "cognitive_type": cog,
                "energy_demand": "high" if cog == "deep" else "medium",
                "estimate_min": max(10, min(int(tu.get("estimate_min") or 45), 300)),
                "priority": max(1, min(prio, 5)),
                "due_date": str(tu.get("due_date") or "") or None,
                "project": str(tu.get("project") or "")[:80],
                "tags": [],
            }
        )

    # task_ref → 已有任务 id 或占位（提交时补）
    ref_map: dict[str, str] = {}
    for t in ctx["tasks"]:
        ref_map[t["title"]] = t["id"]
        for tu in task_updates:
            if tu["title"] == t["title"] or tu["title"] in t["title"] or t["title"] in tu["title"]:
                ref_map[tu["title"]] = t["id"]
    blocks = normalize_blocks(parsed.get("blocks") or [], ctx, ref_map)

    notes = str(parsed.get("notes") or "")
    questions = [str(q) for q in (parsed.get("questions") or []) if str(q).strip()]
    adjustments = [str(a) for a in (parsed.get("adjustments") or []) if str(a).strip()]
    used = sorted({r for b in blocks for r in b["rule_ids"]})
    return {
        "engine": "llm",
        "blocks": blocks,
        "notes": notes,
        "questions": questions[:5],
        "adjustments": adjustments[:8],
        "rule_ids_used": used,
        "usage": usage,
        "raw": json.dumps(parsed, ensure_ascii=False),
        "task_updates": task_updates,
        "deferred": [],
    }


# --------------------------------------------------------------------------- 执行与落库
async def execute_plan(
    session: Session,
    plan_date: date_type,
    text: str,
    *,
    mode: str = "new",
    preview: bool = False,
    replace_ai_blocks: bool = True,
    keep_done: bool = True,
    extra_constraints: list[str] | None = None,
    save_tasks: bool = True,
    now_dt: datetime | None = None,
) -> dict:
    ctx = build_context(
        session, plan_date, mode=mode, replace_ai_blocks=replace_ai_blocks,
        keep_done=keep_done, extra_constraints=extra_constraints, now_dt=now_dt
    )
    ctx["_session"] = session
    ctx["input_text"] = text or ""
    base_revision = context_revision(ctx)
    run = PlanRun(
        plan_date=plan_date,
        mode=mode,
        input_text=text or "",
        engine="fallback",
        model=(ctx["llm"] or {}).get("model", ""),
        status="ok",
    )
    session.add(run)
    session.flush()

    llm_available = bool(ctx["llm"]["available"])
    plan: dict
    if llm_available and (text.strip() or mode == "adjust"):
        try:
            plan = await llm_plan(ctx)
        except LLMError as exc:
            plan = rule_plan(ctx)
            plan["notes"] = (plan["notes"] + f"\n[LLM 调用失败，已用规则引擎兜底：{exc}]").strip()
            plan["engine"] = "fallback"
            run.status = "fallback"
            run.error = str(exc)[:1000]
    else:
        # 无 LLM：用离线解析把自然语言变成任务，再用规则引擎排
        if text.strip():
            offline = nl.parse_tasks_offline(text)
            if offline:
                ctx["tasks"] = ctx["tasks"] + [{**t, "id": None} for t in offline]
                ctx["offline_tasks"] = offline
        plan = rule_plan(ctx)
        if not text.strip() and ctx["tasks"]:
            plan["notes"] = (plan["notes"] + "\n未提供新的自然语言描述，已按待办池自动排程。").strip()

    # 无论模型还是规则引擎，先把内部重叠整理进预览，避免提交时才悄悄改时间。
    plan["blocks"] = _resolve_block_overlaps(plan["blocks"], [], plan_date)
    run.engine = plan["engine"]
    run.notes = plan.get("notes", "")[:4000]
    run.raw_response = (plan.get("raw") or "")[:200000]
    usage = plan.get("usage") or {}
    run.prompt_tokens = int(usage.get("prompt_tokens") or 0)
    run.completion_tokens = int(usage.get("completion_tokens") or 0)

    events: list[Event] = []
    if not preview:
        events = commit_plan(
            session,
            ctx,
            plan,
            run=run,
            mode=mode,
            replace_ai_blocks=replace_ai_blocks,
            keep_done=keep_done,
            save_tasks=save_tasks,
        )
        run.events_created = len(events)
        session.commit()
    else:
        run.status = "preview"
        run.raw_response = json.dumps({
            "plan": plan,
            "context_revision": base_revision,
            "expires_at": (local_now(session) + timedelta(minutes=30)).isoformat(),
            "replace_ai_blocks": replace_ai_blocks,
            "keep_done": keep_done,
        }, ensure_ascii=False, default=str)
        session.commit()

    return {
        "plan_run_id": run.id,
        "engine": plan["engine"],
        "blocks": plan["blocks"],
        "notes": plan.get("notes", ""),
        "questions": plan.get("questions", []),
        "adjustments": plan.get("adjustments", []),
        "rule_ids_used": plan.get("rule_ids_used", []),
        "memory_used": bool(ctx["memory_text"]),
        "usage": usage,
        "events": events,
        "deferred": plan.get("deferred", []),
        "free_min": ctx["free_min"],
        "plan_date": plan_date,
    }


def _resolve_block_overlaps(
    blocks: list[dict], occupied: list[tuple[datetime, datetime]], plan_date: date_type
) -> list[dict]:
    """把互相重叠的方块按时间顺序顺延，保持时长不变。

    LLM 规划偶尔会给出互相压住的方块（例如微休息 20:30-20:45 与下一个块 20:40 开始）。
    规则：按开始时间排序，碰到已占用区间就把开始时间推到该区间结束；顺延到 23:59 之后
    或剩余不足 5 分钟的方块直接丢弃，避免出现跨天或极短的碎片。
    """
    day_start = datetime.combine(plan_date, time(0, 0))
    day_end = datetime.combine(plan_date, time(23, 59))
    taken: list[tuple[datetime, datetime]] = list(occupied)
    out: list[dict] = []
    for b in sorted(blocks, key=lambda x: (x["start"], x["end"])):
        try:
            s = datetime.fromisoformat(b["start"])
            e = datetime.fromisoformat(b["end"])
        except (TypeError, ValueError):
            continue
        dur = e - s
        if dur.total_seconds() <= 0:
            continue
        if s < day_start:
            s = day_start
        moved_at = 0
        while moved_at < 50:
            moved_at += 1
            clash = next(((ts, te) for ts, te in taken if s < te and e > ts), None)
            if clash is None:
                break
            s = clash[1]
            e = s + dur
        if e > day_end or (e - s).total_seconds() < 300:
            continue
        nb = dict(b)
        nb["start"] = s.isoformat()
        nb["end"] = e.isoformat()
        out.append(nb)
        taken.append((s, e))
    return out


def commit_plan(
    session: Session,
    ctx: dict,
    plan: dict,
    *,
    run: PlanRun,
    mode: str,
    replace_ai_blocks: bool,
    keep_done: bool,
    save_tasks: bool,
    strict_preview: bool = False,
) -> list[Event]:
    plan_date = ctx["plan_date"]
    blocks: list[dict] = plan["blocks"]

    # 1) 保存/更新任务
    task_updates: list[dict] = plan.get("task_updates") or []
    title_to_id: dict[str, str] = {t["title"]: t["id"] for t in ctx["tasks"]}
    if save_tasks:
        existing = {t.title: t for t in session.scalars(select(Task)).all()}
        for tu in task_updates:
            title = tu["title"]
            task = existing.get(title)
            if task is None:
                task = Task(
                    title=title,
                    notes=tu.get("notes") or "",
                    category=tu.get("category") or "study",
                    cognitive_type=tu.get("cognitive_type") or "deep",
                    energy_demand=tu.get("energy_demand") or "high",
                    estimate_min=int(tu.get("estimate_min") or 45),
                    priority=int(tu.get("priority") or 3),
                    source="nl",
                )
                due = tu.get("due_date")
                if due:
                    try:
                        task.due_date = date_type.fromisoformat(str(due)[:10])
                    except ValueError:
                        task.due_date = None
                session.add(task)
                session.flush()
                existing[title] = task
            title_to_id[title] = task.id

    # 2) 旧方块清理
    if replace_ai_blocks:
        stmt = select(Event).where(Event.plan_date == plan_date)
        for ev in session.scalars(stmt).all():
            if ev.id in ctx["preserve_ids"]:
                continue
            session.delete(ev)
        session.flush()

    # 3) 写新方块（locked 的固定安排若已存在则跳过，避免重复）
    existing_locked = {
        (ev.title, ev.start, ev.end)
        for ev in session.scalars(select(Event).where(Event.plan_date == plan_date)).all()
        if ev.id in ctx["preserve_ids"]
    }
    candidates: list[dict] = []
    for b in blocks:
        if b.get("locked") and (b["title"], datetime.fromisoformat(b["start"]), datetime.fromisoformat(b["end"])) in existing_locked:
            continue
        candidates.append(b)
    # 3.2) 时间归一化：LLM 偶尔排出互相重叠的方块，按开始时间顺延，避免日历上两块压在一起
    kept_spans = [
        (ev.start, ev.end)
        for ev in session.scalars(select(Event).where(Event.plan_date == plan_date)).all()
    ]
    resolved = _resolve_block_overlaps(candidates, kept_spans, plan_date)
    if strict_preview and resolved != candidates:
        raise ValueError("日程发生冲突，预览已失效，请重新生成预览")
    candidates = resolved

    created: list[Event] = []
    for b in candidates:
        start_dt = datetime.fromisoformat(b["start"])
        end_dt = datetime.fromisoformat(b["end"])
        task_id = b.get("task_id") or title_to_id.get(b["title"])
        ev = Event(
            task_id=task_id,
            title=b["title"],
            notes=b.get("notes") or "",
            category=b.get("category") or "study",
            kind=b.get("kind") or "focus",
            start=start_dt,
            end=end_dt,
            plan_date=plan_date,
            locked=bool(b.get("locked")),
            status="planned",
            reason=b.get("reason") or "",
            rule_ids=b.get("rule_ids") or [],
            plan_run_id=run.id,
        )
        session.add(ev)
        created.append(ev)
    session.flush()

    # 3.5) 给没有任务归属的「工作类」方块补建任务，保证任务池与日历一致
    _NON_TASK_KINDS = {"fixed", "meal", "break", "rest", "buffer"}
    if save_tasks:
        existing_titles = {t.title: t for t in session.scalars(select(Task)).all()}
        for ev in created:
            if ev.task_id or ev.kind in _NON_TASK_KINDS:
                continue
            task = existing_titles.get(ev.title)
            if task is None:
                task = Task(
                    title=ev.title[:200],
                    notes=ev.notes or "",
                    category=ev.category or "study",
                    cognitive_type="shallow" if ev.kind in {"admin", "buffer"} else "deep",
                    estimate_min=max(15, int((ev.end - ev.start).total_seconds() // 60)),
                    priority=3,
                    source="nl",
                )
                session.add(task)
                session.flush()
                existing_titles[ev.title] = task
            ev.task_id = task.id
        session.flush()

    # 4) 任务状态
    scheduled_ids = {ev.task_id for ev in created if ev.task_id}
    for tid in scheduled_ids:
        task = session.get(Task, tid)
        if task and task.status == "pending":
            task.status = "scheduled"
    return created
