"""跨端鉴权、预览一致性及 Agent 采集的回归测试。"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from starlette.requests import Request


def _request(host: str, token: str = "") -> Request:
    headers = [(b"authorization", f"Bearer {token}".encode())] if token else []
    return Request({"type": "http", "client": (host, 50000), "headers": headers,
                    "method": "GET", "path": "/api/events", "scheme": "http",
                    "server": ("127.0.0.1", 8000)})


def test_remote_requires_pairing_token(client):
    from app.access import access_token, remote_authorized

    token = access_token()
    assert remote_authorized(_request("127.0.0.1"))
    assert not remote_authorized(_request("192.168.1.42"))
    assert not remote_authorized(_request("192.168.1.42", "wrong"))
    assert remote_authorized(_request("192.168.1.42", token))
    pairing = client.get("/api/pairing")
    assert pairing.status_code == 200
    assert pairing.json()["token"] == token

    import asyncio
    import httpx
    from app.main import app

    async def check_remote():
        transport = httpx.ASGITransport(app=app, client=("192.168.1.42", 50123))
        async with httpx.AsyncClient(transport=transport, base_url="http://scheduler") as remote:
            assert (await remote.get("/api/events")).status_code == 401
            assert (await remote.get("/api/events", headers={"Authorization": f"Bearer {token}"})).status_code == 200
            assert (await remote.get("/api/pairing", headers={"Authorization": f"Bearer {token}"})).status_code == 403

    asyncio.run(check_remote())


def test_preview_rejects_changed_calendar_and_keeps_manual_event(client):
    day = (date.today() + timedelta(days=2)).isoformat()
    preview = client.post("/api/plan/preview", json={"date": day, "text": "复习线代 1 小时"}).json()
    assert preview["blocks"]
    manual = client.post("/api/events", json={
        "title": "手动会议", "start": f"{day}T10:00:00", "end": f"{day}T11:00:00",
    }).json()
    stale = client.post("/api/plan/apply", json={
        "date": day, "blocks": preview["blocks"], "plan_run_id": preview["plan_run_id"],
    })
    assert stale.status_code == 409
    fresh = client.post("/api/plan/preview", json={"date": day, "text": "复习线代 1 小时"}).json()
    applied = client.post("/api/plan/apply", json={
        "date": day, "blocks": fresh["blocks"], "plan_run_id": fresh["plan_run_id"],
    })
    assert applied.status_code == 200, applied.text
    assert applied.json()["engine"] == fresh["engine"]
    assert any(event["id"] == manual["id"] for event in client.get("/api/events", params={"date": day}).json())
    assert client.post("/api/plan/apply", json={
        "date": day, "blocks": fresh["blocks"], "plan_run_id": fresh["plan_run_id"],
    }).status_code == 409


def test_agent_capture_is_structured_idempotent_and_adjusts(client):
    day = (date.today() + timedelta(days=1)).isoformat()
    body = {
        "day": day, "source": "codex", "message_id": "turn-1",
        "message": "明天上午我要复习线代 60 分钟，下午精力只有 2 分",
        "feedback": {"energy_afternoon": 2},
        "tasks": [{"title": "复习线代", "estimate_min": 60}],
        "adjust_schedule": True,
    }
    first = client.post("/api/agent/capture", json=body)
    assert first.status_code == 200, first.text
    result = first.json()
    assert result["facts"]["feedback"]["energy_afternoon"] == 2
    assert result["plan_run_id"]
    assert client.get(f"/api/feedback/{day}").json()["energy_afternoon"] == 2
    again = client.post("/api/agent/capture", json=body).json()
    assert again["duplicate"] is True
    assert again["facts"] == result["facts"]
    assert len(client.get("/api/tasks").json()) == 1
    assert len(client.get("/api/agent/captures").json()) == 1


def test_today_energy_feedback_guides_rule_schedule(client):
    from app import db, engine
    from app.models import Feedback

    day = date.today() + timedelta(days=2)
    with db.SessionLocal() as session:
        session.add(Feedback(date=day, sleep_hours=5.5, energy_morning=1,
                             energy_afternoon=5))
        session.commit()
        ctx = engine.build_context(session, day)
        plan = engine.rule_plan(ctx)
        assert "任务量自动下调" in plan["notes"]
        assert ctx["current_feedback"]["energy_afternoon"] == 5


def test_apply_uses_stored_blocks_not_client_blocks(client):
    day = (date.today() + timedelta(days=3)).isoformat()
    preview = client.post("/api/plan/preview", json={"date": day, "text": "复习线代 1 小时"}).json()
    applied = client.post("/api/plan/apply", json={
        "date": day, "plan_run_id": preview["plan_run_id"],
        "blocks": [{**preview["blocks"][0], "title": "篡改标题"}],
    })
    assert applied.status_code == 200, applied.text
    assert "篡改标题" not in {event["title"] for event in applied.json()["events"]}


def test_manual_event_overlapping_meal_does_not_block_every_preview(client):
    day = (date.today() + timedelta(days=4)).isoformat()
    manual = client.post("/api/events", json={
        "title": "手动午间会议", "start": f"{day}T12:30:00", "end": f"{day}T13:30:00",
    }).json()
    preview = client.post("/api/plan/preview", json={"date": day, "text": "复习线代 1 小时"}).json()
    assert not any(b["title"] == "午餐" for b in preview["blocks"])
    applied = client.post("/api/plan/apply", json={"date": day, "plan_run_id": preview["plan_run_id"]})
    assert applied.status_code == 200, applied.text
    assert manual["id"] in {ev["id"] for ev in client.get("/api/events", params={"date": day}).json()}


def test_today_plan_does_not_recreate_past_meals(client):
    from app import db, engine

    day = date.today()
    with db.SessionLocal() as session:
        ctx = engine.build_context(session, day, now_dt=datetime.combine(day, datetime.min.time()).replace(hour=18, minute=30))
        assert all(block["start"] >= ctx["window"][0] for block in ctx["fixed_blocks"])
        assert not any(block["title"] == "午餐" for block in ctx["fixed_blocks"])


def test_settings_reach_scheduling_context(client):
    from app import db, engine

    assert client.put("/api/settings", json={
        "plan_buffer_ratio": "0.4", "llm_timeout_seconds": "18",
        "timezone": "Asia/Shanghai",
    }).status_code == 200
    with db.SessionLocal() as session:
        ctx = engine.build_context(session, date.today() + timedelta(days=3))
        assert ctx["buffer_ratio"] == 0.4
    assert client.put("/api/settings", json={"plan_buffer_ratio": "3"}).status_code == 400
