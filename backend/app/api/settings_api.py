"""设置与 LLM 连通性测试。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from sqlalchemy.orm import Session

from ..db import get_db
from ..llm import DeepSeekClient, LLMError
from ..schemas import SettingsOut, SettingsUpdate
from ..settings_store import effective_settings, mask_secret, set_settings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db)) -> SettingsOut:
    st = effective_settings(db)
    return SettingsOut(
        llm_model=st.get("llm_model", ""),
        llm_base_url=st.get("llm_base_url", ""),
        timezone=st.get("timezone", ""),
        plan_buffer_ratio=st.get("plan_buffer_ratio", "0.15"),
        llm_timeout_seconds=st.get("llm_timeout_seconds", "150"),
        has_api_key=bool(st.get("llm_api_key")),
        api_key_preview=mask_secret(st.get("llm_api_key", "")),
    )


@router.put("", response_model=SettingsOut)
def update_settings(payload: SettingsUpdate, db: Session = Depends(get_db)) -> SettingsOut:
    updates: dict[str, str] = {}
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is None:
            continue
        if key == "llm_api_key" and not str(value).strip():
            continue
        if key == "plan_buffer_ratio":
            try:
                number = float(value)
                if not 0 <= number <= 0.8:
                    raise ValueError()
            except (TypeError, ValueError) as exc:
                raise HTTPException(400, "缓冲比例必须在 0 至 0.8 之间") from exc
        if key == "llm_timeout_seconds":
            try:
                number = float(value)
                if not 5 <= number <= 600:
                    raise ValueError()
            except (TypeError, ValueError) as exc:
                raise HTTPException(400, "模型超时必须在 5 至 600 秒之间") from exc
        if key == "timezone":
            try:
                ZoneInfo(str(value))
            except (ZoneInfoNotFoundError, ValueError) as exc:
                raise HTTPException(400, "请输入有效的 IANA 时区，例如 Asia/Shanghai") from exc
        updates[key] = str(value)
    set_settings(db, updates)
    return get_settings(db)


@router.post("/test")
async def test_llm(db: Session = Depends(get_db)) -> dict:
    st = effective_settings(db)
    if not st.get("llm_api_key"):
        raise HTTPException(400, "尚未配置 API Key")
    client = DeepSeekClient(api_key=st["llm_api_key"], base_url=st["llm_base_url"],
                            timeout=float(st.get("llm_timeout_seconds") or 150))
    try:
        models = await client.models()
    except LLMError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "models": models, "configured_model": st.get("llm_model")}
