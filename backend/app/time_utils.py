"""把设置中的时区用于排程日期判断；数据库事件仍使用当地墙上时间。"""

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from . import config


def local_now(session: Session | None = None) -> datetime:
    from .settings_store import effective_settings

    name = effective_settings(session).get("timezone") or config.TIMEZONE
    try:
        zone = ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        zone = ZoneInfo("Asia/Shanghai")
    return datetime.now(zone).replace(tzinfo=None)


def local_today(session: Session | None = None):
    return local_now(session).date()
