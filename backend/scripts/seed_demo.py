"""造一些「历史数据」用于演示统计 / 记忆 / 洞察，并支持一键清除。

用法（在 backend/ 目录下）：
    python scripts/seed_demo.py            # 写入近 24 天演示数据（今天除外）
    python scripts/seed_demo.py --clear    # 删除全部演示数据
    python scripts/seed_demo.py --days 60  # 自定义天数

标记：events.plan_run_id == "seed-demo"，tasks.source == "demo"，
feedback.notes 以 "[demo]" 开头。清除只删这些标记行，不动真实数据。
"""

from __future__ import annotations

import argparse
import random
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import SessionLocal, init_db  # noqa: E402
from app.models import Event, Feedback, MemoryDigest, Task  # noqa: E402

TAG = "seed-demo"
DEMO_HEAD = "[demo]"

# 每类方块：标题 / 分类 / kind / 开始时间 / 时长 / 完成概率
TEMPLATES = [
    ("深度阅读（论文/教材）", "study", "focus", time(9, 0), 90, 0.84),
    ("刷题与错题复盘", "study", "focus", time(10, 45), 60, 0.74),
    ("写代码 / 项目推进", "work", "focus", time(14, 0), 90, 0.7),
    ("整理笔记 & 闪卡复习", "study", "focus", time(16, 10), 45, 0.62),
    ("运动 / 散步", "exercise", "exercise", time(17, 30), 40, 0.55),
    ("英语听力 / 泛读", "study", "focus", time(20, 0), 45, 0.48),
    ("当日复盘 + 明日计划", "admin", "admin", time(21, 0), 20, 0.5),
]


def clear(session) -> None:
    ev = session.query(Event).filter(Event.plan_run_id == TAG).delete(synchronize_session=False)
    fb = session.query(Feedback).filter(Feedback.notes.like(f"{DEMO_HEAD}%")).delete(synchronize_session=False)
    tk = session.query(Task).filter(Task.source == "demo").delete(synchronize_session=False)
    mg = session.query(MemoryDigest).filter(MemoryDigest.engine == "demo").delete(synchronize_session=False)
    session.commit()
    print(f"已清除演示数据：events={ev} feedback={fb} tasks={tk} memory={mg}")


def seed(session, days: int) -> None:
    rng = random.Random(20261025)
    today = date.today()
    created_events = 0
    created_feedback = 0

    for offset in range(days, 0, -1):
        day = today - timedelta(days=offset)
        weekday = day.weekday()
        if rng.random() < 0.08:  # 偶尔整天没安排
            continue

        sleep = round(rng.uniform(6.0, 8.2), 1)
        low_energy = sleep < 6.6
        # 睡眠影响完成率，周末整体略低，形成可被洞察抓到的模式
        penalty = -0.16 if low_energy else 0.0
        penalty += -0.08 if weekday >= 5 else 0.0

        for title, category, kind, start_t, dur, base in TEMPLATES:
            if weekday >= 5 and kind == "focus" and rng.random() < 0.4:
                continue  # 周末少排一个专注块
            prob = max(0.1, min(0.95, base + penalty + rng.uniform(-0.05, 0.05)))
            start_dt = datetime.combine(day, start_t)
            end_dt = start_dt + timedelta(minutes=dur)
            done = rng.random() < prob
            status = "done" if done else ("partial" if rng.random() < 0.3 else "skipped")
            actual = dur if done else (int(dur * rng.uniform(0.3, 0.7)) if status == "partial" else 0)
            session.add(
                Event(
                    title=title,
                    category=category,
                    kind=kind,
                    start=start_dt,
                    end=end_dt,
                    plan_date=day,
                    status=status,
                    actual_min=actual,
                    quality=rng.randint(2, 5) if done else None,
                    reason="演示数据",
                    rule_ids=[],
                    plan_run_id=TAG,
                )
            )
            created_events += 1

        session.add(
            Feedback(
                date=day,
                sleep_hours=sleep,
                sleep_quality=rng.randint(2, 5) if not low_energy else rng.randint(1, 3),
                energy_morning=2 if low_energy else rng.randint(3, 5),
                energy_afternoon=rng.randint(1, 4) if low_energy else rng.randint(3, 5),
                energy_evening=rng.randint(1, 3) if low_energy else rng.randint(2, 4),
                mood=rng.randint(2, 5),
                notes=f"{DEMO_HEAD} {'睡得少，下午明显掉线' if low_energy else '状态正常'}",
            )
        )
        created_feedback += 1

    session.add(
        MemoryDigest(
            kind="rolling28",
            period_start=today - timedelta(days=days),
            period_end=today - timedelta(days=1),
            summary_md=(
                "## 近一月概览（演示）\n\n- 上午 9–11 点完成率最高，晚上 20 点后明显下滑。\n"
                "- 睡眠低于 6.5 小时的第二天，下午深度块完成率下降约 20%。\n"
                "- 建议：把最难的深度任务锁在上午，晚上只安排轻量复盘。"
            ),
            stats_json={},
            engine="demo",
        )
    )
    session.commit()
    print(f"已写入演示数据：events={created_events} feedback={created_feedback}（近 {days} 天）")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clear", action="store_true")
    parser.add_argument("--days", type=int, default=24)
    args = parser.parse_args()

    init_db()
    session = SessionLocal()
    try:
        if args.clear:
            clear(session)
        else:
            seed(session, args.days)
    finally:
        session.close()


if __name__ == "__main__":
    main()
