"""桌面启动器：双击 日程规划.exe（或 `python backend/launcher.py`）即可用。

做的事情：
1. 如果 8000 端口上已经有本程序在跑，直接打开浏览器，不重复启动；
2. 否则启动 uvicorn，等 /api/health 就绪后自动打开默认浏览器；
3. 日志写到 data/app.log；致命错误弹 MessageBox（打包成 noconsole 时也能看到原因）。
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
import threading
import time
import urllib.request
import webbrowser

HEALTH_TIMEOUT = 1.2
READY_TIMEOUT = 90
# 自动化测试 / 后台常驻时置 1，不自动弹浏览器
NO_BROWSER = os.getenv("SCHEDULE_NO_BROWSER") == "1"


def _open_browser(port: int) -> None:
    if NO_BROWSER:
        return
    webbrowser.open(f"http://127.0.0.1:{port}")


def _msgbox(title: str, text: str) -> None:
    """打包成无控制台程序时，用系统对话框把错误告诉用户。"""
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, text, title, 0x10)
    except Exception:  # noqa: BLE001 — 没有 GUI 就只剩日志
        print(f"[{title}] {text}", file=sys.stderr)


def _health_ok(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=HEALTH_TIMEOUT) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


def _open_when_ready(port: int) -> None:
    deadline = time.time() + READY_TIMEOUT
    while time.time() < deadline:
        if _health_ok(port):
            _open_browser(port)
            return
        time.sleep(0.4)


def _migrate_legacy_db(config) -> None:
    """源码目录里的演示数据库，首次打包运行时搬一份过来，省得重新造数。

    用 sqlite 的 backup API 复制，能正确带上 WAL 里尚未落盘的事务。
    """
    if config.DB_PATH.exists():
        return
    candidates = []
    if config.EXE_DIR is not None:
        candidates.append(config.EXE_DIR / "backend" / "data" / "schedule.db")
    candidates.append(config.ROOT_DIR / "backend" / "data" / "schedule.db")
    for src in candidates:
        try:
            if not src.is_file():
                continue
            import sqlite3

            config.DATA_DIR.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(f"file:{src.as_posix()}?mode=ro", uri=True) as s, sqlite3.connect(
                config.DB_PATH
            ) as d:
                s.backup(d)
            return
        except Exception:  # noqa: BLE001 — 迁移失败不影响启动
            continue


def main() -> None:
    from app import config

    log_file = config.DATA_DIR / "app.log"
    logging.basicConfig(
        filename=str(log_file),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        encoding="utf-8",
    )

    port = config.PORT
    if _health_ok(port):
        _open_browser(port)
        return

    _migrate_legacy_db(config)

    threading.Thread(target=_open_when_ready, args=(port,), daemon=True).start()

    try:
        import uvicorn

        from app.main import app

        uvicorn.run(app, host=config.HOST, port=port, log_level="info", log_config=None)
    except Exception as exc:  # noqa: BLE001 — 端口占用 / 依赖缺失等
        logging.exception("启动失败")
        _msgbox(
            "日程规划启动失败",
            f"{exc}\n\n常见原因：8000 端口被占用。\n日志：{log_file}\n也可先关闭占用端口的程序后重试。",
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
