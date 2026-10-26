"""任务池 CRUD。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Task
from ..schemas import TaskCreate, TaskOut, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskOut])
def list_tasks(
    status: str | None = Query(default=None),
    include_done: bool = Query(default=True),
    db: Session = Depends(get_db),
) -> list[Task]:
    stmt = select(Task).order_by(Task.status.asc(), Task.priority.asc(), Task.created_at.desc())
    if status:
        stmt = stmt.where(Task.status == status)
    elif not include_done:
        stmt = stmt.where(Task.status.in_(["pending", "scheduled", "partial"]))
    return list(db.scalars(stmt).all())


@router.post("", response_model=TaskOut, status_code=201)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)) -> Task:
    task = Task(**payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: str, db: Session = Depends(get_db)) -> Task:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    return task


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: str, payload: TaskUpdate, db: Session = Depends(get_db)) -> Task:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, key, value)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: str, db: Session = Depends(get_db)) -> None:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    db.delete(task)
    db.commit()
