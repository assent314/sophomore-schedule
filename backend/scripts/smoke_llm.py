"""真实 LLM 冒烟：需要 backend/.env 里配置 DEEPSEEK_API_KEY。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def main() -> int:
    with TestClient(app) as c:
        health = c.get("/api/health").json()
        print("health:", health)
        if not health["llm_configured"]:
            print("未配置 API Key，跳过真实 LLM 冒烟")
            return 0
        print("\n--- 自然语言预览（真实 LLM） ---")
        r = c.post(
            "/api/plan/preview",
            json={
                "date": "2026-10-26",
                "text": "明天上午复习线性代数 1.5 小时（周三考试），下午写论文 3 小时，晚上去健身房 1 小时，另外取个快递",
            },
        )
        print("status:", r.status_code)
        data = r.json()
        if r.status_code != 200:
            print(data)
            return 1
        print("engine:", data["engine"], "| usage:", data.get("usage"))
        print("memory_used:", data.get("memory_used"), "| free_min:", data.get("free_min"))
        for b in data["blocks"]:
            print(f"  {b['start'][11:16]}-{b['end'][11:16]}  {b['kind']:<8} {b['title']}  规则={b['rule_ids']}")
        print("notes:", data["notes"].replace("\n", " | "))
        print("questions:", data["questions"])
        print("adjustments:", data["adjustments"])
        print("\n--- 日反馈解析（真实 LLM） ---")
        r = c.post("/api/feedback/2026-10-25/parse", params={"text": "昨晚只睡了5个半小时，上午脑子还行，下午很困，晚上跑了3公里"})
        print("status:", r.status_code, r.json())
        print("\n--- 调整模式（真实 LLM） ---")
        r = c.post(
            "/api/plan/preview",
            json={"date": "2026-10-26", "mode": "adjust", "text": "下午临时要开会 2 小时，帮我把日程挪一下"},
        )
        print("status:", r.status_code)
        data = r.json()
        print("engine:", data.get("engine"))
        for b in data.get("blocks", []):
            print(f"  {b['start'][11:16]}-{b['end'][11:16]}  {b['title']}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
