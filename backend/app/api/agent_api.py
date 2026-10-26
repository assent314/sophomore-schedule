"""通用 Agent REST 入口；局域网访问受同一配对密钥保护。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..agent_bridge import ChatCaptureInput, capture, recent_captures
from ..db import get_db

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/capture")
async def capture_chat(payload: ChatCaptureInput, db: Session = Depends(get_db)) -> dict:
    return await capture(db, payload)


@router.get("/captures")
def list_captures(limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db)) -> list[dict]:
    return recent_captures(db, limit)
