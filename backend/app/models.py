import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BlogStatus(str, enum.Enum):
    DRAFT = "draft"
    RESEARCHING = "researching"
    WRITING = "writing"
    REVIEW_PENDING = "review_pending"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"
    PUBLISHED = "published"
    FAILED = "failed"


class PublishFormat(str, enum.Enum):
    POST = "post"  # Short LinkedIn post (~1300 chars with formatting)
    ARTICLE = "article"  # Long-form LinkedIn article


class Niche(Base):
    __tablename__ = "niches"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    # daily / weekly / biweekly / monthly
    frequency: Mapped[str] = mapped_column(String(20), default="weekly")
    # day-of-week (0=Mon … 6=Sun) for weekly/biweekly; day-of-month (1–28) for monthly
    schedule_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    schedule_time: Mapped[str] = mapped_column(String(5), default="09:00")  # HH:MM
    publish_format: Mapped[str] = mapped_column(String(20), default=PublishFormat.POST)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    blogs: Mapped[list["Blog"]] = relationship(
        back_populates="niche", cascade="all, delete-orphan"
    )


class Blog(Base):
    __tablename__ = "blogs"

    id: Mapped[int] = mapped_column(primary_key=True)
    niche_id: Mapped[int] = mapped_column(ForeignKey("niches.id"))
    topic: Mapped[str] = mapped_column(Text, default="")
    title: Mapped[str] = mapped_column(String(500), default="")
    # Full rich Markdown with embedded ```mermaid blocks and tables
    content_markdown: Mapped[str] = mapped_column(Text, default="")
    # LinkedIn-formatted text (post) or article body
    linkedin_post: Mapped[str] = mapped_column(Text, default="")
    # Long-form article title + subtitle for LinkedIn Articles format
    linkedin_article_title: Mapped[str] = mapped_column(String(500), default="")
    linkedin_article_body: Mapped[str] = mapped_column(Text, default="")
    publish_format: Mapped[str] = mapped_column(String(20), default=PublishFormat.POST)
    research_summary: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default=BlogStatus.DRAFT)
    email_message_id: Mapped[str | None] = mapped_column(String(500), nullable=True)
    review_email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    revision_count: Mapped[int] = mapped_column(Integer, default=0)
    published_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    niche: Mapped["Niche"] = relationship(back_populates="blogs")
    revisions: Mapped[list["BlogRevision"]] = relationship(
        back_populates="blog", cascade="all, delete-orphan"
    )
    logs: Mapped[list["GenerationLog"]] = relationship(
        back_populates="blog", cascade="all, delete-orphan"
    )


class BlogRevision(Base):
    __tablename__ = "blog_revisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    blog_id: Mapped[int] = mapped_column(ForeignKey("blogs.id"))
    revision_number: Mapped[int] = mapped_column(Integer)
    content_markdown: Mapped[str] = mapped_column(Text)
    linkedin_post: Mapped[str] = mapped_column(Text, default="")
    linkedin_article_body: Mapped[str] = mapped_column(Text, default="")
    changes_requested: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    blog: Mapped["Blog"] = relationship(back_populates="revisions")


class AppSetting(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True)
    value: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class GenerationLog(Base):
    __tablename__ = "generation_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    blog_id: Mapped[int] = mapped_column(ForeignKey("blogs.id"))
    phase: Mapped[str] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    blog: Mapped["Blog"] = relationship(back_populates="logs")
