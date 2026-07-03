from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models import CandidateStatus, Role, SummaryStatus

SCORE_CATEGORIES = [
    "Technical Skills",
    "Communication",
    "Problem Solving",
    "Culture Fit",
    "Experience",
]


# ---- Auth ----
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=1, max_length=255)
    # NOTE: intentionally no `role` field here — role is always hardcoded to
    # "reviewer" server-side (see routers/auth.py). Never accept role from the client.


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role


class UserOut(BaseModel):
    id: str
    email: EmailStr
    role: Role

    class Config:
        from_attributes = True


# ---- Scores ----
class ScoreCreate(BaseModel):
    category: str
    score: int = Field(ge=1, le=5)
    note: Optional[str] = ""

    @field_validator("category")
    @classmethod
    def category_must_be_known(cls, v: str) -> str:
        if v not in SCORE_CATEGORIES:
            raise ValueError(f"category must be one of {SCORE_CATEGORIES}")
        return v


class ScoreOut(BaseModel):
    id: str
    candidate_id: str
    category: str
    score: int
    reviewer_id: str
    reviewer_email: Optional[str] = None
    note: Optional[str] = ""
    created_at: datetime

    class Config:
        from_attributes = True


# ---- Candidates ----
class CandidateCreate(BaseModel):
    name: str
    email: EmailStr
    role_applied: str
    skills: list[str] = []
    internal_notes: Optional[str] = ""


class CandidateListItem(BaseModel):
    id: str
    name: str
    email: EmailStr
    role_applied: str
    status: CandidateStatus
    skills: list[str]
    created_at: datetime

    class Config:
        from_attributes = True


class CandidateListResponse(BaseModel):
    items: list[CandidateListItem]
    total: int
    offset: int
    limit: int


class CandidateDetail(BaseModel):
    id: str
    name: str
    email: EmailStr
    role_applied: str
    status: CandidateStatus
    skills: list[str]
    created_at: datetime
    internal_notes: Optional[str] = None  # omitted (None) for reviewers
    ai_summary: Optional[str] = None
    ai_summary_status: SummaryStatus
    scores: list[ScoreOut]

    class Config:
        from_attributes = True


class InternalNotesUpdate(BaseModel):
    internal_notes: str


class SummaryTriggerResponse(BaseModel):
    ai_summary_status: SummaryStatus
