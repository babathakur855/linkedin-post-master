from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Blog, BlogStatus, BlogRevision, GenerationLog, Niche

router = APIRouter(prefix="/blogs", tags=["blogs"])


def _blog_to_dict(b: Blog, include_content: bool = False) -> dict[str, Any]:
    d = {
        "id": b.id,
        "niche_id": b.niche_id,
        "topic": b.topic,
        "title": b.title,
        "status": b.status,
        "publish_format": b.publish_format,
        "revision_count": b.revision_count,
        "published_url": b.published_url,
        "published_at": b.published_at.isoformat() if b.published_at else None,
        "created_at": b.created_at.isoformat(),
        "updated_at": b.updated_at.isoformat(),
    }
    if include_content:
        d.update(
            {
                "content_markdown": b.content_markdown,
                "linkedin_post": b.linkedin_post,
                "linkedin_article_title": b.linkedin_article_title,
                "linkedin_article_body": b.linkedin_article_body,
                "research_summary": b.research_summary,
            }
        )
    return d


@router.get("/")
async def list_blogs(
    status: str | None = None,
    niche_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    q = select(Blog).order_by(Blog.created_at.desc()).limit(limit).offset(offset)
    if status:
        q = q.where(Blog.status == status)
    if niche_id:
        q = q.where(Blog.niche_id == niche_id)
    blogs = (await db.execute(q)).scalars().all()
    return [_blog_to_dict(b) for b in blogs]


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(func.count()).select_from(Blog))).scalar()
    published = (
        await db.execute(
            select(func.count())
            .select_from(Blog)
            .where(Blog.status == BlogStatus.PUBLISHED)
        )
    ).scalar()
    pending = (
        await db.execute(
            select(func.count())
            .select_from(Blog)
            .where(Blog.status == BlogStatus.REVIEW_PENDING)
        )
    ).scalar()
    drafts = (
        await db.execute(
            select(func.count())
            .select_from(Blog)
            .where(
                Blog.status.in_(
                    [BlogStatus.DRAFT, BlogStatus.WRITING, BlogStatus.RESEARCHING]
                )
            )
        )
    ).scalar()
    return {
        "total": total,
        "published": published,
        "pending_review": pending,
        "drafts": drafts,
    }


@router.get("/{blog_id}")
async def get_blog(blog_id: int, db: AsyncSession = Depends(get_db)):
    blog = (
        await db.execute(select(Blog).where(Blog.id == blog_id))
    ).scalar_one_or_none()
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    d = _blog_to_dict(blog, include_content=True)

    # Include logs
    logs = (
        (
            await db.execute(
                select(GenerationLog)
                .where(GenerationLog.blog_id == blog_id)
                .order_by(GenerationLog.created_at)
            )
        )
        .scalars()
        .all()
    )
    d["logs"] = [
        {
            "phase": lg.phase,
            "message": lg.message,
            "created_at": lg.created_at.isoformat(),
        }
        for lg in logs
    ]

    # Include revisions
    revisions = (
        (
            await db.execute(
                select(BlogRevision)
                .where(BlogRevision.blog_id == blog_id)
                .order_by(BlogRevision.revision_number)
            )
        )
        .scalars()
        .all()
    )
    d["revisions"] = [
        {
            "id": r.id,
            "revision_number": r.revision_number,
            "changes_requested": r.changes_requested,
            "created_at": r.created_at.isoformat(),
        }
        for r in revisions
    ]

    # Niche name
    if blog.niche_id:
        niche = (
            await db.execute(select(Niche).where(Niche.id == blog.niche_id))
        ).scalar_one_or_none()
        d["niche_name"] = niche.name if niche else ""

    return d


class GenerateRequest(BaseModel):
    niche_id: int
    publish_format: str | None = None  # override niche default if provided


async def _run_generation(blog_id: int) -> None:
    from app.agents.orchestrator import generate_blog_pipeline
    from app.database import SessionLocal

    async with SessionLocal() as db:
        await generate_blog_pipeline(blog_id, db)


@router.post("/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_blog(
    body: GenerateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    niche = (
        await db.execute(select(Niche).where(Niche.id == body.niche_id))
    ).scalar_one_or_none()
    if not niche:
        raise HTTPException(status_code=404, detail="Niche not found")

    blog = Blog(
        niche_id=body.niche_id,
        status=BlogStatus.DRAFT,
        publish_format=body.publish_format or niche.publish_format,
    )
    db.add(blog)
    await db.commit()
    await db.refresh(blog)
    blog_id = blog.id

    background_tasks.add_task(_run_generation, blog_id)

    return {"blog_id": blog_id, "status": BlogStatus.DRAFT}


class ReviseRequest(BaseModel):
    changes: str


@router.post("/{blog_id}/revise")
async def request_revision(
    blog_id: int,
    body: ReviseRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    blog = (
        await db.execute(select(Blog).where(Blog.id == blog_id))
    ).scalar_one_or_none()
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")

    async def _revise(bid: int, changes: str) -> None:
        from app.agents.orchestrator import apply_email_revision
        from app.database import SessionLocal

        async with SessionLocal() as db2:
            b = (
                await db2.execute(select(Blog).where(Blog.id == bid))
            ).scalar_one_or_none()
            if b:
                await apply_email_revision(b, changes, db2)

    background_tasks.add_task(_revise, blog_id, body.changes)
    return {"blog_id": blog_id, "status": "revision_started"}


@router.post("/{blog_id}/approve")
async def approve_blog(
    blog_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    blog = (
        await db.execute(select(Blog).where(Blog.id == blog_id))
    ).scalar_one_or_none()
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")

    blog.status = BlogStatus.APPROVED
    await db.commit()

    async def _publish(bid: int) -> None:
        from app.services import linkedin_service
        from app.database import SessionLocal

        async with SessionLocal() as db2:
            b = (
                await db2.execute(select(Blog).where(Blog.id == bid))
            ).scalar_one_or_none()
            if not b:
                return
            try:
                url = await linkedin_service.publish_blog(b, db2)
                b.published_url = url
                b.published_at = datetime.utcnow()
                b.status = BlogStatus.PUBLISHED
            except Exception as exc:
                b.status = BlogStatus.FAILED
                from app.models import GenerationLog

                db2.add(
                    GenerationLog(blog_id=bid, phase="publish_error", message=str(exc))
                )
            await db2.commit()

    background_tasks.add_task(_publish, blog_id)
    return {"blog_id": blog_id, "status": "publishing"}


@router.delete("/{blog_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_blog(blog_id: int, db: AsyncSession = Depends(get_db)):
    blog = (
        await db.execute(select(Blog).where(Blog.id == blog_id))
    ).scalar_one_or_none()
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    await db.delete(blog)
    await db.commit()
