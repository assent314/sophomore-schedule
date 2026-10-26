"""本地 stdio MCP 服务：Codex 与 DeepSeek Harness 可共用。

运行：python backend/agent_mcp.py
标准输出只供 MCP 协议使用，不打印日志或聊天内容。
"""

from __future__ import annotations

from datetime import date

from mcp.server.fastmcp import FastMCP
from sqlalchemy import select

from app import db, engine
from app.agent_bridge import ChatCaptureInput, capture, recent_captures
from app.models import Event, Feedback, Task

mcp = FastMCP("schedule", instructions=(
    "在用户明确谈到睡眠、时段精力、长期作息、具体待办或日程冲突时，"
    "读取当前日程并调用 capture_chat_context。只提交用户明确表达的事实；"
    "不要从闲聊推断任务或睡眠。工具会记录结构化事实并在适当日期重新规划未来的 AI 方块。"
))


@mcp.tool()
def get_schedule_context(day: str) -> dict:
    """读取指定日期的日程、待办、反馈和习惯，供 Agent 判断是否需要调整。day 为 YYYY-MM-DD。"""
    plan_date = date.fromisoformat(day)
    db.init_db()
    with db.SessionLocal() as session:
        profile = engine.profile_to_dict(engine.get_profile(session))
        events = session.scalars(select(Event).where(Event.plan_date == plan_date).order_by(Event.start)).all()
        tasks = session.scalars(select(Task).where(Task.status.in_(["pending", "scheduled", "partial"]))).all()
        feedback = session.scalar(select(Feedback).where(Feedback.date == plan_date))
        return {
            "day": day,
            "profile": profile,
            "events": [engine._event_dict(item) for item in events],
            "tasks": [engine._task_dict(item) for item in tasks],
            "feedback": {
                key: getattr(feedback, key) for key in (
                    "sleep_hours", "sleep_quality", "energy_morning",
                    "energy_afternoon", "energy_evening", "mood")
            } if feedback else None,
        }


@mcp.tool()
async def capture_chat_context(
    message: str,
    day: str,
    source: str = "agent",
    message_id: str | None = None,
    feedback: dict | None = None,
    tasks: list[dict] | None = None,
    habitual_energy_curve: list[int] | None = None,
    constraints: list[str] | None = None,
    adjust_schedule: bool = True,
) -> dict:
    """采集聊天中明确的精力/睡眠/任务信息，并按需重排未来 AI 日程。

    Agent 应传入明确提取的 feedback、tasks、habitual_energy_curve、constraints；
    未提供结构化字段时，服务端只用保守的离线规则抽取。重复 message_id 不会重复写入。
    """
    payload = ChatCaptureInput(
        message=message, day=date.fromisoformat(day), source=source,
        message_id=message_id, feedback=feedback, tasks=tasks or [],
        habitual_energy_curve=habitual_energy_curve,
        constraints=constraints or [], adjust_schedule=adjust_schedule,
    )
    db.init_db()
    with db.SessionLocal() as session:
        return await capture(session, payload)


@mcp.tool()
def list_schedule_captures(limit: int = 10) -> list[dict]:
    """查看最近由 Agent 写入的事实、是否重排、对应运行记录，不返回原始聊天。"""
    db.init_db()
    with db.SessionLocal() as session:
        return recent_captures(session, max(1, min(limit, 50)))


if __name__ == "__main__":
    mcp.run(transport="stdio")
