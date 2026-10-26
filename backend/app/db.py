"""数据库连接与会话。"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
import sqlite3

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from . import config

SCHEMA_VERSION = 1


class Base(DeclarativeBase):
    pass


engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)

# SQLite 打开外键约束 + WAL，提升并发读写体验
@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_connection, _record) -> None:  # noqa: ANN001
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from . import models  # noqa: F401  确保模型已注册

    # 在首次接管旧数据库时保留一份完整快照（SQLite backup API 包含 WAL 中的事务）。
    with sqlite3.connect(config.DB_PATH) as source:
        version = source.execute("PRAGMA user_version").fetchone()[0]
        if version > SCHEMA_VERSION:
            raise RuntimeError(f"数据库版本 {version} 高于程序支持的 {SCHEMA_VERSION}")
        has_tables = source.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' LIMIT 1"
        ).fetchone() is not None
        if version < SCHEMA_VERSION and has_tables:
            backup_dir = config.DATA_DIR / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            target = backup_dir / f"before-schema-v{SCHEMA_VERSION}-{stamp}.db"
            if not target.exists():
                with sqlite3.connect(target) as backup:
                    source.backup(backup)
    Base.metadata.create_all(bind=engine)
    with sqlite3.connect(config.DB_PATH) as connection:
        connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
