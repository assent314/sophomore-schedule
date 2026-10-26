"""学习科学规则库接口（透明可追溯是核心卖点）。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import knowledge

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/rules")
def list_rules() -> list[dict]:
    return knowledge.all_rules()


@router.get("/rules/{rule_id}")
def get_rule(rule_id: str) -> dict:
    rule = knowledge.get_rule(rule_id)
    if not rule:
        raise HTTPException(404, "规则不存在")
    return rule


@router.get("/meta")
def meta() -> dict:
    return {
        "categories": [
            {"key": k, "label": v, "color": knowledge.CATEGORY_COLOR[k]} for k, v in knowledge.CATEGORY_LABEL.items()
        ],
        "strengths": knowledge.STRENGTH_LABEL,
        "event_categories": [
            {"key": k, "label": v, "color": knowledge.EVENT_CATEGORY_COLOR[k]}
            for k, v in knowledge.EVENT_CATEGORY_LABEL.items()
        ],
        "kinds": [{"key": k, "label": v} for k, v in knowledge.KIND_LABEL.items()],
        "rule_count": len(knowledge.RULES),
    }


@router.get("/doc")
def doc() -> dict:
    return {"markdown": knowledge.rules_markdown()}
