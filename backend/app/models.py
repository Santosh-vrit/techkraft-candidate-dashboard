import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class Role(str, enum.Enum):
    reviewer = "reviewer"
    admin = "admin"


class CandidateStatus(str, enum.Enum):
    new = "new"
    reviewed = "reviewed"
    hired = "hired"
    rejected = "rejected"
    archived = "archived"


class SummaryStatus(str, enum.Enum):
    none = "none"
    pending = "pending"
    completed = "completed"
    failed = "failed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role), nullable=False, default=Role.reviewer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    scores: Mapped[list["Score"]] = relationship(back_populates="reviewer")


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    role_applied: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    status: Mapped[CandidateStatus] = mapped_column(
        Enum(CandidateStatus), index=True, nullable=False, default=CandidateStatus.new
    )
    skills: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    internal_notes: Mapped[str] = mapped_column(Text, nullable=True, default="")
    ai_summary: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    ai_summary_status: Mapped[SummaryStatus] = mapped_column(
        Enum(SummaryStatus), nullable=False, default=SummaryStatus.none
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, default=None)

    scores: Mapped[list["Score"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")


class Score(Base):
    __tablename__ = "scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    candidate_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("candidates.id"), index=True, nullable=False
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    reviewer_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=True, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    candidate: Mapped["Candidate"] = relationship(back_populates="scores")
    reviewer: Mapped["User"] = relationship(back_populates="scores")
