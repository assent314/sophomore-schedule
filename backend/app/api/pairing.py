"""仅供桌面本机查看的手机配对信息。"""

from fastapi import APIRouter, HTTPException, Request

from .. import access, config

router = APIRouter(prefix="/pairing", tags=["pairing"])


@router.get("")
def pairing(request: Request) -> dict:
    if not access.is_local(request):
        raise HTTPException(403, "只能在电脑本机查看配对密钥")
    return {
        "token": access.access_token(),
        "lan_enabled": config.HOST not in {"127.0.0.1", "::1", "localhost"},
        "https_enabled": bool(config.TLS_CERTFILE and config.TLS_KEYFILE),
    }
