from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Niche
from app.services.scheduler_service import reload_schedules

router = APIRouter(prefix="/niches", tags=["niches"])


class NicheCreate(BaseModel):
    name: str
    description: str = ""
    keywords: list[str] = []
    frequency: str = "weekly"
    schedule_day: int | None = None
    schedule_time: str = "09:00"
    publish_format: str = "post"
    active: bool = True


class NicheUpdate(NicheCreate):
    pass


def _niche_to_dict(n: Niche) -> dict[str, Any]:
    return {
        "id": n.id,
        "name": n.name,
        "description": n.description,
        "keywords": n.keywords,
        "frequency": n.frequency,
        "schedule_day": n.schedule_day,
        "schedule_time": n.schedule_time,
        "publish_format": n.publish_format,
        "active": n.active,
        "created_at": n.created_at.isoformat(),
        "updated_at": n.updated_at.isoformat(),
    }


@router.get("/")
async def list_niches(db: AsyncSession = Depends(get_db)):
    niches = (
        (await db.execute(select(Niche).order_by(Niche.created_at.desc())))
        .scalars()
        .all()
    )
    return [_niche_to_dict(n) for n in niches]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_niche(body: NicheCreate, db: AsyncSession = Depends(get_db)):
    niche = Niche(**body.model_dump())
    db.add(niche)
    await db.commit()
    await db.refresh(niche)
    await reload_schedules()
    return _niche_to_dict(niche)


@router.get("/{niche_id}")
async def get_niche(niche_id: int, db: AsyncSession = Depends(get_db)):
    niche = (
        await db.execute(select(Niche).where(Niche.id == niche_id))
    ).scalar_one_or_none()
    if not niche:
        raise HTTPException(status_code=404, detail="Niche not found")
    return _niche_to_dict(niche)


@router.put("/{niche_id}")
async def update_niche(
    niche_id: int, body: NicheUpdate, db: AsyncSession = Depends(get_db)
):
    niche = (
        await db.execute(select(Niche).where(Niche.id == niche_id))
    ).scalar_one_or_none()
    if not niche:
        raise HTTPException(status_code=404, detail="Niche not found")
    for k, v in body.model_dump().items():
        setattr(niche, k, v)
    niche.updated_at = datetime.utcnow()
    await db.commit()
    await reload_schedules()
    return _niche_to_dict(niche)


@router.delete("/{niche_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_niche(niche_id: int, db: AsyncSession = Depends(get_db)):
    niche = (
        await db.execute(select(Niche).where(Niche.id == niche_id))
    ).scalar_one_or_none()
    if not niche:
        raise HTTPException(status_code=404, detail="Niche not found")
    await db.delete(niche)
    await db.commit()
    await reload_schedules()
