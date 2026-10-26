"""个人作息/习惯档案。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import engine
from ..db import get_db
from ..schemas import ProfileOut, ProfileUpdate

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileOut)
def get_profile(db: Session = Depends(get_db)) -> ProfileOut:
    prof = engine.get_profile(db)
    return ProfileOut.model_validate(prof)


@router.put("", response_model=ProfileOut)
def update_profile(payload: ProfileUpdate, db: Session = Depends(get_db)) -> ProfileOut:
    prof = engine.get_profile(db)
    data = payload.model_dump(exclude_unset=True)
    if "energy_curve" in data and data["energy_curve"] is not None:
        curve = [max(1, min(5, int(v))) for v in data["energy_curve"]]
        if len(curve) != 24:
            curve = (curve + [3] * 24)[:24]
        data["energy_curve"] = curve
    if "fixed_commitments" in data and data["fixed_commitments"] is not None:
        data["fixed_commitments"] = [
            item.model_dump() if hasattr(item, "model_dump") else item for item in data["fixed_commitments"]
        ]
    for key, value in data.items():
        setattr(prof, key, value)
    db.commit()
    db.refresh(prof)
    return ProfileOut.model_validate(prof)


@router.get("/defaults", response_model=dict)
def defaults() -> dict:
    from ..knowledge import DEFAULT_PROFILE

    return DEFAULT_PROFILE
