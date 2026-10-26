"""pytest 公共夹具：使用临时数据库、禁用真实 LLM。"""

from __future__ import annotations

import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="schedule-test-")
os.environ.setdefault("SCHEDULE_DATA_DIR", _TMP)
os.environ["DEEPSEEK_API_KEY"] = ""  # 已被 .env 加载时也不会覆盖
os.environ["SCHEDULE_PORT"] = "8123"

import pytest  # noqa: E402

from app import config, db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    db.init_db()
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _clean_tables():
    from app.models import AgentCapture, AppSetting, Event, Feedback, MemoryDigest, PlanRun, Profile, Task

    db.init_db()
    with db.SessionLocal() as s:
        for model in (AgentCapture, Event, Task, Feedback, MemoryDigest, PlanRun, Profile, AppSetting):
            s.query(model).delete()
        s.commit()
    yield


def pytest_sessionfinish(session, exitstatus):  # noqa: ANN001
    import shutil

    shutil.rmtree(config.DATA_DIR, ignore_errors=True)
