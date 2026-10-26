"""本地启动入口：python run.py"""

from __future__ import annotations

import uvicorn

from app import config


def main() -> None:
    uvicorn.run(
        "app.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
