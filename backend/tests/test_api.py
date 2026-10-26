"""后端 API 冒烟测试（不依赖真实 LLM）。"""

from __future__ import annotations

from datetime import date, datetime, timedelta


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["db"].endswith("schedule.db")


def test_knowledge_has_rules(client):
    r = client.get("/api/knowledge/rules")
    assert r.status_code == 200
    rules = r.json()
    assert len(rules) >= 18
    ids = {x["id"] for x in rules}
    assert {"spaced_practice", "retrieval_practice", "circadian_peak"} <= ids
    meta = client.get("/api/knowledge/meta").json()
    assert meta["rule_count"] == len(rules)


def test_task_crud(client):
    r = client.post("/api/tasks", json={"title": "复习线性代数", "estimate_min": 60, "priority": 1})
    assert r.status_code == 201, r.text
    task = r.json()
    assert task["status"] == "pending"
    listed = client.get("/api/tasks").json()
    assert any(t["id"] == task["id"] for t in listed)
    r = client.patch(f"/api/tasks/{task['id']}", json={"status": "done", "estimate_min": 30})
    assert r.status_code == 200
    assert r.json()["status"] == "done"
    assert client.delete(f"/api/tasks/{task['id']}").status_code == 204


def test_profile_defaults_and_update(client):
    r = client.get("/api/profile")
    assert r.status_code == 200
    prof = r.json()
    assert prof["wake_time"] == "07:00"
    assert len(prof["energy_curve"]) == 24
    r = client.put(
        "/api/profile",
        json={"wake_time": "06:30", "sleep_time": "23:00", "preferred_block_min": 50,
              "fixed_commitments": [{"title": "组会", "weekdays": [0], "start": "10:00", "end": "11:00"}]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["preferred_block_min"] == 50
    assert body["fixed_commitments"][0]["title"] == "组会"


def test_feedback_upsert_and_parse(client):
    today = date.today().isoformat()
    r = client.put(f"/api/feedback/{today}", json={"sleep_hours": 6.5, "energy_morning": 3, "notes": "有点累"})
    assert r.status_code == 200
    assert r.json()["sleep_hours"] == 6.5
    again = client.put(f"/api/feedback/{today}", json={"energy_evening": 2})
    assert again.status_code == 200
    assert again.json()["energy_evening"] == 2
    assert again.json()["sleep_hours"] == 6.5
    listed = client.get("/api/feedback").json()
    assert len(listed) == 1
    parsed = client.post(f"/api/feedback/{today}/parse", params={"text": "昨晚睡了5小时，下午很累"}).json()
    assert parsed["sleep_hours"] == 5


def test_plan_rule_engine_commit(client):
    today = (date.today() + timedelta(days=1)).isoformat()
    # 固定一个上午 9:00-12:00 的会议，验证占用时段不被覆盖
    client.put("/api/profile", json={"wake_time": "07:00", "sleep_time": "23:00",
                                     "fixed_commitments": [{"title": "开会", "weekdays": [], "start": "09:00", "end": "12:00"}]})
    r = client.post("/api/plan/preview", json={"date": today, "text": "复习线代 1 小时，写论文 2 小时"})
    assert r.status_code == 200, r.text
    preview = r.json()
    assert preview["engine"] in {"rule", "fallback", "llm"}
    assert preview["blocks"], preview
    # 预览不落库
    assert client.get("/api/events", params={"date": today}).json() == []

    r = client.post("/api/plan", json={"date": today, "text": "复习线代 1 小时，写论文 2 小时"})
    assert r.status_code == 200, r.text
    plan = r.json()
    assert len(plan["events"]) >= 2
    events = client.get("/api/events", params={"date": today}).json()
    assert len(events) >= 2
    for ev in events:
        assert ev["plan_date"] == today
        assert ev["start"] < ev["end"]
    # 没有任务块压到 9:00-12:00 的会议里（fixed/meal 方块本身就是会议与三餐）
    work = [ev for ev in events if ev["kind"] not in {"fixed", "meal", "break"}]
    for ev in work:
        assert not (ev["start"] < f"{today}T12:00:00" and ev["end"] > f"{today}T09:00:00")
    assert any(ev["title"] == "开会" for ev in events)
    # 重复规划不会重复创建固定安排
    client.post("/api/plan", json={"date": today, "text": "复习线代 1 小时"})
    again = client.get("/api/events", params={"date": today}).json()
    assert len([e for e in again if e["title"] == "开会"]) == 1


def test_plan_preview_apply_roundtrip(client):
    """预览的方块原样落库：块数、标题、时间与预览一致，且不再二次排程。"""
    today = (date.today() + timedelta(days=1)).isoformat()
    client.put("/api/profile", json={"wake_time": "07:00", "sleep_time": "23:00", "fixed_commitments": []})
    r = client.post("/api/plan/preview", json={"date": today, "text": "复习线代 1 小时，写论文 2 小时"})
    assert r.status_code == 200, r.text
    preview = r.json()
    assert preview["blocks"]
    ai_blocks = [b for b in preview["blocks"] if b["kind"] not in {"fixed", "meal"}]
    assert ai_blocks

    r = client.post(
        "/api/plan/apply",
        json={
            "date": today,
            "blocks": preview["blocks"],
            "plan_run_id": preview["plan_run_id"],
            "mode": "new",
        },
    )
    assert r.status_code == 200, r.text
    applied = r.json()
    got = client.get("/api/events", params={"date": today}).json()
    assert len(got) == len(applied["events"])
    preview_titles = sorted(b["title"] for b in ai_blocks)
    got_titles = sorted(e["title"] for e in got if e["kind"] not in {"fixed", "meal"})
    assert preview_titles == got_titles


def test_event_complete_and_stats(client):
    today = date(2026, 10, 20)
    client.post(
        "/api/events",
        json={
            "title": "深度学习块",
            "start": f"{today}T09:00:00",
            "end": f"{today}T10:00:00",
            "kind": "focus",
            "category": "study",
        },
    )
    events = client.get("/api/events", params={"date": today.isoformat()}).json()
    assert len(events) == 1
    ev = events[0]
    r = client.post(f"/api/events/{ev['id']}/complete", params={"status": "done", "actual_min": 55, "quality": 4})
    assert r.status_code == 200
    assert r.json()["status"] == "done"
    stats = client.get("/api/stats/overview", params={"days": 30}).json()
    assert stats["total_planned_min"] >= 60
    assert stats["total_done_min"] >= 55
    progress = client.get("/api/stats/progress", params={"days": 7}).json()
    assert len(progress["series"]) == 7


def test_memory_refresh_rule(client):
    today = date.today()
    client.post(
        "/api/events",
        json={"title": "背单词", "start": f"{today}T08:00:00", "end": f"{today}T08:30:00",
              "kind": "study", "category": "study"},
    )
    r = client.post("/api/memory/refresh", params={"use_llm": False})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["engine"] == "rule"
    assert "近 28 天" in body["summary_md"]
    mem = client.get("/api/memory").json()
    assert mem["stale"] is False
    assert mem["summary_md"]


def test_settings_masked(client):
    r = client.get("/api/settings")
    assert r.status_code == 200
    body = r.json()
    assert "llm_api_key" not in body
    assert body["has_api_key"] in {True, False}


def test_course_import_events_excluded_from_stats(client):
    """课表导入事件（plan_run_id=course-import）要能从统计里排除。"""
    today = date.today().isoformat()
    r = client.post(
        "/api/events",
        json={
            "title": "生物工艺学原理",
            "start": f"{today}T08:00:00",
            "end": f"{today}T09:35:00",
            "category": "fixed",
            "kind": "fixed",
            "plan_run_id": "course-import",
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["plan_run_id"] == "course-import"

    before = client.get("/api/stats/overview", params={"days": 7}).json()
    assert all(
        "生物工艺学原理" not in c["key"] for c in before["by_category"]
    ), before["by_category"]
    # 正常事件仍然计入
    client.post(
        "/api/events",
        json={"title": "错题整理", "start": f"{today}T10:00:00", "end": f"{today}T10:30:00"},
    )
    after = client.get("/api/stats/overview", params={"days": 7}).json()
    assert after["total_planned_min"] > before["total_planned_min"]


def test_overlapping_blocks_are_shifted():
    """LLM 排出的重叠方块要按时间顺序顺延，而不是叠在一起。"""
    from app.engine import _resolve_block_overlaps

    blocks = [
        {"title": "A", "start": "2026-10-25T20:30:00", "end": "2026-10-25T20:45:00"},
        {"title": "B", "start": "2026-10-25T20:40:00", "end": "2026-10-25T21:20:00"},
        {"title": "C", "start": "2026-10-25T21:20:00", "end": "2026-10-25T21:30:00"},
    ]
    out = _resolve_block_overlaps(blocks, [(datetime(2026, 10, 25, 23, 0), datetime(2026, 10, 25, 23, 30))], date(2026, 10, 25))
    assert [b["title"] for b in out] == ["A", "B", "C"]
    assert out[0]["end"] == "2026-10-25T20:45:00"
    assert out[1]["start"] == "2026-10-25T20:45:00"   # 被 A 顺延
    assert out[2]["start"] == "2026-10-25T21:25:00"   # C 跟着 B 顺延


def test_plan_avoids_and_keeps_course_events(client):
    """从课表导入的课程（plan_run_id=course-import，未锁定）排程要避开，重排后也不能被删掉。"""
    day = "2026-11-02"  # 周一
    course = client.post(
        "/api/events",
        json={
            "title": "基因工程原理与应用",
            "start": f"{day}T09:55:00",
            "end": f"{day}T11:35:00",
            "category": "fixed",
            "kind": "fixed",
            "plan_run_id": "course-import",
        },
    )
    assert course.status_code == 201, course.text
    course_id = course.json()["id"]

    preview = client.post(
        "/api/plan/preview",
        json={"date": day, "text": "今天上午复习概率论，下午写项目接口，晚上健身", "mode": "new"},
    )
    assert preview.status_code == 200, preview.text
    plan = preview.json()
    assert plan["blocks"], plan

    def minutes(hhmm: str) -> int:
        h, m = hhmm.split(":")[:2]
        return int(h) * 60 + int(m)

    for b in plan["blocks"]:
        bs, be = minutes(b["start"][11:16]), minutes(b["end"][11:16])
        assert not (bs < minutes("11:35") and minutes("09:55") < be), f"方块压到课程: {b}"

    applied = client.post(
        "/api/plan/apply",
        json={
            "date": day,
            "blocks": plan["blocks"],
            "plan_run_id": plan.get("plan_run_id"),
            "mode": "new",
            "replace_ai_blocks": True,
            "keep_done": True,
        },
    )
    assert applied.status_code == 200, applied.text

    day_events = client.get("/api/events", params={"date": day}).json()
    kept = [e for e in day_events if e["id"] == course_id]
    assert kept, "重排把课表导入的课程删掉了"
    assert kept[0]["plan_run_id"] == "course-import"
    # 课程与 AI 方块之间不留重叠
    spans = sorted((minutes(e["start"][11:16]), minutes(e["end"][11:16]), e["title"]) for e in day_events)
    for (s1, e1, t1), (s2, e2, t2) in zip(spans, spans[1:]):
        assert e1 <= s2 + 1, f"{t1} 与 {t2} 重叠"
