"""统计与滚动记忆。

完成率口径
  done_min  = 已勾选完成方块的（实际耗时或计划时长）
  partial   = 记一半
  completed = status in {done, partial}
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date as date_type
from datetime import datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from . import knowledge
from .models import Event, Feedback, MemoryDigest, PlanRun, Task
from .time_utils import local_today

WEEKDAY_LABEL = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

# 课表导入的「只展示」事件：出现在日历上，但不计入完成率统计，免得整学期课程把完成率拉垮
COURSE_TAG = "course-import"


def exclude_course_import():
    """统计口径里排除课表导入事件（plan_run_id 为空的正常事件都保留）。"""
    return or_(Event.plan_run_id.is_(None), Event.plan_run_id != COURSE_TAG)



def _cat_label(key: str) -> str:
    return knowledge.EVENT_CATEGORY_LABEL.get(key, key)


def _today(session: Session) -> date_type:
    return local_today(session)


def _minute_len(ev: Event) -> int:
    return max(0, int((ev.end - ev.start).total_seconds() // 60))


def _done_fraction(ev: Event) -> float:
    if ev.status == "done":
        return 1.0
    if ev.status == "partial":
        return 0.5
    return 0.0


def _bucket(hour: int) -> str:
    if 5 <= hour < 12:
        return "上午(5-12)"
    if 12 <= hour < 18:
        return "下午(12-18)"
    if 18 <= hour < 24:
        return "晚上(18-24)"
    return "深夜(0-5)"


def overview(session: Session, days: int = 28, today: date_type | None = None) -> dict:
    today = today or _today(session)
    start = today - timedelta(days=days - 1)
    events = session.scalars(
        select(Event).where(Event.plan_date >= start, Event.plan_date <= today, exclude_course_import())
    ).all()
    feedbacks = session.scalars(
        select(Feedback).where(Feedback.date >= start, Feedback.date <= today).order_by(Feedback.date)
    ).all()

    planned_min = sum(_minute_len(e) for e in events)
    done_min = sum(round(_minute_len(e) * _done_fraction(e)) for e in events)
    completion = round(done_min / planned_min, 3) if planned_min else 0.0

    by_cat: dict[str, dict] = defaultdict(lambda: {"planned_min": 0, "done_min": 0, "count": 0, "done_count": 0})
    by_bucket: dict[str, dict] = defaultdict(lambda: {"planned_min": 0, "done_min": 0, "count": 0, "done_count": 0})
    by_weekday: dict[str, dict] = defaultdict(
        lambda: {"planned_min": 0, "done_min": 0, "count": 0, "done_count": 0, "days": set()}
    )
    daily: dict[date_type, dict] = defaultdict(
        lambda: {"planned_min": 0, "done_min": 0, "blocks_planned": 0, "blocks_done": 0}
    )
    accuracy_samples: list[dict] = []

    for ev in events:
        length = _minute_len(ev)
        done = round(length * _done_fraction(ev))
        cat = by_cat[ev.category]
        cat["planned_min"] += length
        cat["done_min"] += done
        cat["count"] += 1
        cat["done_count"] += 1 if ev.status in {"done", "partial"} else 0

        b = by_bucket[_bucket(ev.start.hour)]
        b["planned_min"] += length
        b["done_min"] += done
        b["count"] += 1
        b["done_count"] += 1 if ev.status in {"done", "partial"} else 0

        wd = by_weekday[WEEKDAY_LABEL[ev.plan_date.weekday()]]
        wd["planned_min"] += length
        wd["done_min"] += done
        wd["count"] += 1
        wd["done_count"] += 1 if ev.status in {"done", "partial"} else 0
        wd["days"].add(ev.plan_date)

        d = daily[ev.plan_date]
        d["planned_min"] += length
        d["done_min"] += done
        d["blocks_planned"] += 1
        d["blocks_done"] += 1 if ev.status in {"done", "partial"} else 0

        if ev.actual_min:
            accuracy_samples.append(
                {"plan_date": ev.plan_date.isoformat(), "category": ev.category,
                 "estimate": length, "actual": ev.actual_min}
            )

    est_acc = {"samples": len(accuracy_samples)}
    if accuracy_samples:
        ests = [s["estimate"] for s in accuracy_samples]
        acts = [s["actual"] for s in accuracy_samples]
        est_acc.update(
            {
                "avg_estimate_min": round(sum(ests) / len(ests), 1),
                "avg_actual_min": round(sum(acts) / len(acts), 1),
                "bias_ratio": round(sum(acts) / sum(ests), 3) if sum(ests) else None,
            }
        )

    daily_list = [
        {
            "date": d,
            "planned_min": v["planned_min"],
            "done_min": v["done_min"],
            "completion_rate": round(v["done_min"] / v["planned_min"], 3) if v["planned_min"] else 0.0,
            "blocks_planned": v["blocks_planned"],
            "blocks_done": v["blocks_done"],
        }
        for d, v in sorted(daily.items())
    ]

    fb_trend = [
        {
            "date": f.date.isoformat(),
            "sleep_hours": f.sleep_hours,
            "sleep_quality": f.sleep_quality,
            "energy_morning": f.energy_morning,
            "energy_afternoon": f.energy_afternoon,
            "energy_evening": f.energy_evening,
            "mood": f.mood,
        }
        for f in feedbacks
    ]

    def _rate(v: dict) -> float:
        return round(v["done_min"] / v["planned_min"], 3) if v["planned_min"] else 0.0

    result = {
        "days": days,
        "period_start": start,
        "period_end": today,
        "total_planned_min": planned_min,
        "total_done_min": done_min,
        "completion_rate": completion,
        "by_category": [
            {"key": k, **_rate_round(v), "completion_rate": _rate(v)}
            for k, v in sorted(by_cat.items(), key=lambda kv: -kv[1]["planned_min"])
        ],
        "by_hour_bucket": [
            {"key": k, **_rate_round(v), "completion_rate": _rate(v)} for k, v in by_bucket.items()
        ],
        "by_weekday": [
            {"key": k, **_rate_round(v), "completion_rate": _rate(v), "active_days": len(v["days"])}
            for k, v in by_weekday.items()
        ],
        "estimate_accuracy": est_acc,
        "daily": daily_list,
        "feedback_trend": fb_trend,
        "top_insights": [],
        "_accuracy_samples": accuracy_samples,
    }
    result["top_insights"] = build_insights(result, feedbacks, events)
    return result


def _rate_round(v: dict) -> dict:
    return {
        "planned_min": v["planned_min"],
        "done_min": v["done_min"],
        "count": v["count"],
        "done_count": v["done_count"],
    }


def build_insights(stats: dict, feedbacks: list[Feedback], events: list[Event]) -> list[str]:
    insights: list[str] = []
    if stats["total_planned_min"] < 60:
        insights.append("历史数据还太少，先记录 2–3 天：每天勾掉完成情况并在晚上写一句反馈，我就能开始校准。")
        return insights

    insights.append(
        f"近 {stats['days']} 天共排入 {stats['total_planned_min'] // 60} 小时、"
        f"完成率 {stats['completion_rate'] * 100:.0f}%。"
    )

    buckets = [b for b in stats["by_hour_bucket"] if b["planned_min"] >= 30]
    if len(buckets) >= 2:
        best = max(buckets, key=lambda b: b["completion_rate"])
        worst = min(buckets, key=lambda b: b["completion_rate"])
        if best["key"] != worst["key"] and best["completion_rate"] - worst["completion_rate"] > 0.1:
            insights.append(
                f"{best['key']}的完成率最高（{best['completion_rate'] * 100:.0f}%），"
                f"{worst['key']}最低（{worst['completion_rate'] * 100:.0f}%）；"
                f"可以考虑把最重要的任务往{best['key']}挪。"
            )

    cats = [c for c in stats["by_category"] if c["planned_min"] >= 60]
    if cats:
        c = cats[0]
        insights.append(f"投入最多的是「{_cat_label(c['key'])}」（{c['planned_min'] // 60} 小时，完成率 {c['completion_rate'] * 100:.0f}%）。")

    acc = stats["estimate_accuracy"]
    if acc.get("samples", 0) >= 3 and acc.get("bias_ratio"):
        ratio = acc["bias_ratio"]
        if ratio > 1.15:
            insights.append(
                f"实际耗时平均是你预估的 {ratio:.2f} 倍（规划谬误），后续我会按这个系数放大你的预估。"
            )
        elif ratio < 0.85:
            insights.append(f"实际耗时只有预估的 {ratio:.2f} 倍，你可能估得偏保守，可以适当加量。")
        else:
            insights.append(f"预估和实际基本吻合（实际/预估 = {ratio:.2f}）。")

    short_sleep = [f for f in feedbacks if f.sleep_hours is not None and f.sleep_hours < 6.5]
    if len(short_sleep) >= 2:
        insights.append(f"有 {len(short_sleep)} 天睡眠不足 6.5 小时，这些天之后的完成率通常会被拉低。")

    if events:
        skipped = [e for e in events if e.status == "skipped"]
        if len(skipped) >= 2:
            titles = "、".join(sorted({e.title for e in skipped})[:3])
            insights.append(f"被跳过的方块集中在：{titles}。这类任务建议拆得更小或换到高能量时段。")
    return insights


def compact_for_prompt(session: Session, today: date_type | None = None) -> str:
    """给 LLM 的紧凑历史摘要（近 28 天 + 最新记忆摘要）。"""
    today = today or _today(session)
    stats = overview(session, days=28, today=today)
    lines = [
        f"近 28 天：排入 {stats['total_planned_min'] // 60}h，完成率 {stats['completion_rate'] * 100:.0f}%，"
        f"记录天数 {len(stats['daily'])}。",
    ]
    for ins in stats["top_insights"][:4]:
        lines.append(f"- {ins}")
    if stats["by_category"]:
        parts = [f"{_cat_label(c['key'])}:{c['completion_rate'] * 100:.0f}%" for c in stats["by_category"][:5]]
        lines.append("分类完成率：" + "，".join(parts))
    digest = latest_memory(session)
    if digest and digest.summary_md:
        lines.append("此前生成的滚动摘要：" + digest.summary_md.replace("\n", " ")[:600])
    return "\n".join(lines)


def latest_memory(session: Session) -> MemoryDigest | None:
    return session.scalars(
        select(MemoryDigest).order_by(MemoryDigest.created_at.desc()).limit(1)
    ).first()


def memory_text(session: Session) -> str:
    digest = latest_memory(session)
    if not digest:
        return ""
    return digest.summary_md


def refresh_memory(
    session: Session,
    *,
    today: date_type | None = None,
    days: int = 28,
    use_llm: bool = False,
    llm_summary: str | None = None,
) -> MemoryDigest:
    """重算滚动记忆。llm_summary 由调用方（异步 LLM）生成后传入。"""
    today = today or _today(session)
    start = today - timedelta(days=days - 1)
    stats = overview(session, days=days, today=today)

    lines = [
        f"## 近 {days} 天（{start} → {today}）",
        f"- 排入：{stats['total_planned_min'] // 60} 小时；完成：{stats['total_done_min'] // 60} 小时；"
        f"完成率 {stats['completion_rate'] * 100:.0f}%",
    ]
    if stats["by_category"]:
        for c in stats["by_category"]:
            lines.append(
                f"- {_cat_label(c['key'])}：{c['planned_min'] // 60}h，完成率 {c['completion_rate'] * 100:.0f}%"
            )
    if stats["by_hour_bucket"]:
        lines.append(
            "- 时段：" + "，".join(f"{b['key']} {b['completion_rate'] * 100:.0f}%" for b in stats["by_hour_bucket"])
        )
    if stats["estimate_accuracy"].get("bias_ratio"):
        lines.append(f"- 预估偏差系数（实际/预估）：{stats['estimate_accuracy']['bias_ratio']}")
    for ins in stats["top_insights"]:
        lines.append(f"- 洞察：{ins}")

    summary = "\n".join(lines)
    engine = "rule"
    if use_llm and llm_summary:
        summary = llm_summary.strip()
        engine = "llm"
    digest = MemoryDigest(
        kind=f"rolling{days}",
        period_start=start,
        period_end=today,
        summary_md=summary,
        stats_json=_json_safe({k: v for k, v in stats.items() if k not in {"_accuracy_samples"}}),
        engine=engine,
    )
    session.add(digest)
    session.commit()
    return digest


def _json_safe(value):
    """把 date / datetime 等不可 JSON 序列化的对象转成字符串。"""
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (date_type, datetime)):
        return value.isoformat()
    return value


def is_stale(session: Session, digest: MemoryDigest | None, today: date_type | None = None) -> bool:
    if digest is None:
        return True
    today = today or _today(session)
    if digest.period_end < today - timedelta(days=1):
        return True
    last_event = session.scalars(select(Event).order_by(Event.updated_at.desc()).limit(1)).first()
    if last_event and last_event.updated_at and last_event.updated_at.date() > digest.period_end:
        return True
    return False


def progress_series(session: Session, days: int = 30, today: date_type | None = None) -> list[dict]:
    """累积完成曲线，用于前端图表。"""
    today = today or _today(session)
    start = today - timedelta(days=days - 1)
    events = session.scalars(
        select(Event).where(Event.plan_date >= start, Event.plan_date <= today, exclude_course_import())
    ).all()
    per_day: dict[date_type, dict] = defaultdict(lambda: {"planned": 0, "done": 0})
    for ev in events:
        length = _minute_len(ev)
        per_day[ev.plan_date]["planned"] += length
        per_day[ev.plan_date]["done"] += round(length * _done_fraction(ev))
    series = []
    cum_p = cum_d = 0
    cursor = start
    while cursor <= today:
        v = per_day.get(cursor, {"planned": 0, "done": 0})
        cum_p += v["planned"]
        cum_d += v["done"]
        series.append(
            {
                "date": cursor.isoformat(),
                "planned_min": v["planned"],
                "done_min": v["done"],
                "cum_planned_min": cum_p,
                "cum_done_min": cum_d,
            }
        )
        cursor += timedelta(days=1)
    return series
