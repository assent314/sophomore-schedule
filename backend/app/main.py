"""FastAPI 应用入口。"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config, db
from .api import agent_api, events, feedback, knowledge_api, pairing, plan, profile, settings_api, stats_api, tasks
from .access import remote_authorized


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="日程规划 · 学习科学排程", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://localhost", "capacitor://localhost", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def require_remote_token(request: Request, call_next):
    if request.url.path.startswith("/api/") and request.method != "OPTIONS":
        if not remote_authorized(request):
            return JSONResponse({"detail": "未配对：请在手机连接页填写电脑设置中显示的密钥"}, status_code=401)
    return await call_next(request)


for module in (tasks, events, feedback, profile, plan, stats_api, knowledge_api, settings_api, pairing, agent_api):
    app.include_router(module.router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    from .models import Event, Task
    from .settings_store import effective_settings

    with db.SessionLocal() as session:
        try:
            st = effective_settings(session)
            counts = {
                "tasks": session.query(Task).count(),
                "events": session.query(Event).count(),
            }
        except Exception:  # noqa: BLE001 — 首次启动表还没建
            st = dict(config.DEFAULT_SETTINGS)
            counts = {"tasks": 0, "events": 0}
    return {
        "ok": True,
        "version": app.version,
        "db": str(config.DB_PATH),
        "llm_configured": bool(st.get("llm_api_key")),
        "llm_model": st.get("llm_model"),
        "counts": counts,
    }


if config.FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(config.FRONTEND_DIST), html=True), name="frontend")
else:

    @app.get("/")
    def root() -> JSONResponse:
        return JSONResponse(
            {
                "message": "后端已启动，但前端尚未构建。请先运行 `pnpm --dir frontend build`。",
                "api": "/api/health",
            }
        )
