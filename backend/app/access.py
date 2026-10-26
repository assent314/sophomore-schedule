"""本机信任与手机访问密钥。

密钥只保存在运行时数据目录，不进入仓库。远程设备必须带 Bearer 密钥；
桌面浏览器走回环地址，无须把密钥放入 URL 或页面源代码。
"""

from __future__ import annotations

import hmac
import ipaddress
import os
import secrets
from pathlib import Path

from fastapi import Request

from . import config

TOKEN_FILE = config.DATA_DIR / "access-token.txt"


def is_local(request: Request) -> bool:
    host = request.client.host if request.client else ""
    if host == "testclient":  # Starlette TestClient 的虚拟回环地址
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def access_token() -> str:
    try:
        return TOKEN_FILE.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        pass
    token = secrets.token_urlsafe(32)
    try:
        fd = os.open(str(TOKEN_FILE), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return TOKEN_FILE.read_text(encoding="utf-8").strip()
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(token)
    return token


def remote_authorized(request: Request) -> bool:
    if is_local(request):
        return True
    scheme, _, supplied = request.headers.get("authorization", "").partition(" ")
    return scheme.lower() == "bearer" and hmac.compare_digest(supplied, access_token())
