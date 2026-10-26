"""应用配置：环境变量默认值 + 运行期可覆盖项（数据库 settings 表）。

同一份配置同时支持两种运行方式：
- 源码运行：`python backend/run.py`，数据落在 backend/data/
- 打包运行：`日程规划.exe`（PyInstaller onefile），静态资源取自解包目录，
  数据落在 exe 同级的 data/，.env 依次在 exe 目录、exe/backend、exe/data 里找。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

FROZEN = bool(getattr(sys, "frozen", False))
# PyInstaller onefile 运行时的解包目录；源码运行时为空
MEIPASS = Path(getattr(sys, "_MEIPASS", "")) if FROZEN else None
EXE_DIR = Path(sys.executable).resolve().parent if FROZEN else None

if FROZEN and MEIPASS is not None:
    BUNDLE_DIR = MEIPASS
    BACKEND_DIR = BUNDLE_DIR / "backend"
    ROOT_DIR = BUNDLE_DIR
    FRONTEND_DIST = BUNDLE_DIR / "frontend" / "dist"
    DEFAULT_DATA_DIR = EXE_DIR / "data"
    ENV_CANDIDATES = [
        EXE_DIR / ".env",
        EXE_DIR / "backend" / ".env",
        EXE_DIR / "data" / ".env",
    ]
else:
    BACKEND_DIR = Path(__file__).resolve().parent.parent
    ROOT_DIR = BACKEND_DIR.parent
    FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"
    # 源码运行也用项目根目录的 data/（与 exe 同一份数据，避免两套库漂移）
    DEFAULT_DATA_DIR = ROOT_DIR / "data"
    ENV_CANDIDATES = [BACKEND_DIR / ".env"]
    BUNDLE_DIR = None

# 先加载 .env（先找到的优先），再读取环境变量
for _env_file in ENV_CANDIDATES:
    if _env_file.is_file():
        load_dotenv(_env_file)
        break

DATA_DIR = Path(os.getenv("SCHEDULE_DATA_DIR", str(DEFAULT_DATA_DIR)))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "schedule.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

TIMEZONE = os.getenv("SCHEDULE_TIMEZONE", "Asia/Shanghai")
HOST = os.getenv("SCHEDULE_HOST", "0.0.0.0")
PORT = int(os.getenv("SCHEDULE_PORT", "8000"))

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# 配置项默认值（写入 settings 表后可被 UI 覆盖）
DEFAULT_SETTINGS: dict[str, str] = {
    "llm_api_key": DEEPSEEK_API_KEY,
    "llm_base_url": DEEPSEEK_BASE_URL,
    "llm_model": DEEPSEEK_MODEL,
    "timezone": TIMEZONE,
    "plan_buffer_ratio": "0.15",
    "llm_timeout_seconds": "150",
}

# 供前端展示/测试的公开配置项，不含密钥明文
SECRET_SETTING_KEYS = {"llm_api_key"}
