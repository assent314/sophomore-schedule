"""设置存取：环境变量默认值 + app_settings 表覆盖。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import config
from .models import AppSetting

KNOWN_KEYS = set(config.DEFAULT_SETTINGS.keys())


def _db_values(session: Session) -> dict[str, str]:
    rows = session.scalars(select(AppSetting)).all()
    return {r.key: r.value for r in rows if r.value is not None and r.value != ""}


def effective_settings(session: Session | None = None) -> dict[str, str]:
    merged = dict(config.DEFAULT_SETTINGS)
    if session is not None:
        try:
            merged.update(_db_values(session))
        except Exception:  # noqa: BLE001 — 表尚未创建时回退到环境变量
            pass
    return merged


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}…{value[-4:]}"


def set_settings(session: Session, updates: dict[str, str]) -> dict[str, str]:
    for key, value in updates.items():
        if key not in KNOWN_KEYS or value is None:
            continue
        row = session.get(AppSetting, key)
        if row is None:
            session.add(AppSetting(key=key, value=str(value)))
        else:
            row.value = str(value)
    session.commit()
    return effective_settings(session)
