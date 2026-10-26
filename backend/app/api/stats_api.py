"""统计与滚动记忆接口。"""

from __future__ import annotations

from datetime import date as date_type

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import stats
from ..db import get_db
from ..time_utils import local_today

router = APIRouter(tags=["stats"])


@router.get("/stats/overview")
def get_overview(
    days: int = Query(default=28, ge=1, le=180),
    db: Session = Depends(get_db),
) -> dict:
    data = stats.overview(db, days=days)
    data.pop("_accuracy_samples", None)
    return data


@router.get("/stats/progress")
def get_progress(
    days: int = Query(default=30, ge=1, le=180),
    db: Session = Depends(get_db),
) -> dict:
    return {"series": stats.progress_series(db, days=days), "insights": stats.overview(db, days=days)["top_insights"]}


@router.get("/memory")
def get_memory(days: int = Query(default=28, ge=1, le=180), db: Session = Depends(get_db)) -> dict:
    digest = stats.latest_memory(db)
    stale = stats.is_stale(db, digest)
    if digest is None:
        return {
            "kind": f"rolling{days}",
            "period_start": local_today(db).isoformat(),
            "period_end": local_today(db).isoformat(),
            "summary_md": "",
            "stats": {},
            "engine": "rule",
            "created_at": None,
            "stale": True,
        }
    return {
        "kind": digest.kind,
        "period_start": digest.period_start.isoformat(),
        "period_end": digest.period_end.isoformat(),
        "summary_md": digest.summary_md,
        "stats": digest.stats_json or {},
        "engine": digest.engine,
        "created_at": digest.created_at.isoformat(),
        "stale": stale,
    }


@router.post("/memory/refresh")
async def refresh_memory(
    days: int = Query(default=28, ge=1, le=180),
    use_llm: bool = Query(default=True),
    db: Session = Depends(get_db),
) -> dict:
    from ..llm import DeepSeekClient, LLMError
    from ..settings_store import effective_settings

    llm_text: str | None = None
    engine_note = "rule"
    if use_llm:
        st = effective_settings(db)
        if st.get("llm_api_key"):
            data = stats.overview(db, days=days)
            prompt = _memory_prompt(data)
            try:
                client = DeepSeekClient(api_key=st["llm_api_key"], base_url=st["llm_base_url"],
                                        timeout=float(st.get("llm_timeout_seconds") or 150))
                parsed, _usage = await client.chat_json(
                    "你是一个复盘助手，负责把统计数据写成一段简洁的中文复盘，供未来的排程模型参考。",
                    prompt,
                    model=st.get("llm_model"),
                    max_tokens=900,
                    temperature=0.4,
                )
                llm_text = str(parsed.get("summary") or "").strip()
                if llm_text:
                    engine_note = "llm"
            except LLMError:
                llm_text = None
    digest = stats.refresh_memory(db, days=days, use_llm=bool(llm_text), llm_summary=llm_text)
    return {
        "kind": digest.kind,
        "period_start": digest.period_start.isoformat(),
        "period_end": digest.period_end.isoformat(),
        "summary_md": digest.summary_md,
        "stats": digest.stats_json,
        "engine": engine_note,
        "created_at": digest.created_at.isoformat(),
        "stale": False,
    }


def _memory_prompt(data: dict) -> str:
    lines = [
        f"请根据下面近 {data['days']} 天的日程统计数据，写一段 200-350 字的中文复盘。",
        "要求：1) 指出完成率走势与最稳定的时段；2) 指出哪类任务被跳过多、可能原因；3) 给出 2-3 条下周可执行的调整建议；",
        "4) 只陈述数据支持的内容，不要编造；5) 用 markdown 小标题 + 短句，不要表格。",
        "",
        f"总排入 {data['total_planned_min']} 分钟，完成 {data['total_done_min']} 分钟，完成率 {data['completion_rate']}。",
    ]
    for c in data.get("by_category", []):
        lines.append(f"- 分类 {c['key']}: 计划 {c['planned_min']} 分钟, 完成率 {c['completion_rate']}")
    for b in data.get("by_hour_bucket", []):
        lines.append(f"- 时段 {b['key']}: 完成率 {b['completion_rate']}")
    for w in data.get("by_weekday", []):
        lines.append(f"- {w['key']}: 完成率 {w['completion_rate']}")
    if data.get("estimate_accuracy", {}).get("bias_ratio"):
        lines.append(f"- 实际/预估耗时比: {data['estimate_accuracy']['bias_ratio']}")
    for ins in data.get("top_insights", []):
        lines.append(f"- 已有洞察: {ins}")
    lines.append("")
    lines.append('只输出 JSON：{"summary": "markdown 文本"}')
    return "\n".join(lines)
