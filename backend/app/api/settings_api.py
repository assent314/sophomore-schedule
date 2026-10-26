"""设置与 LLM 连通性测试。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
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
        updates[key] = str(value)
    set_settings(db, updates)
    return get_settings(db)


@router.post("/test")
async def test_llm(db: Session = Depends(get_db)) -> dict:
    st = effective_settings(db)
    if not st.get("llm_api_key"):
        raise HTTPException(400, "尚未配置 API Key")
    client = DeepSeekClient(api_key=st["llm_api_key"], base_url=st["llm_base_url"])
    try:
        models = await client.models()
    except LLMError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "models": models, "configured_model": st.get("llm_model")}
