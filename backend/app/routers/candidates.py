import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app import database
from app.auth import get_current_user, require_admin
from app.database import get_db
from app.models import Candidate, CandidateStatus, Role, SummaryStatus, User
from app.schemas import (
    CandidateCreate,
    CandidateDetail,
    CandidateListResponse,
    InternalNotesUpdate,
    ScoreCreate,
    ScoreOut,
    SummaryTriggerResponse,
)
from app.services import candidate_service
from app.services.events import subscribe, unsubscribe

router = APIRouter(prefix="/candidates", tags=["candidates"])


def _serialize_candidate(
    candidate: Candidate, current_user: User, scores: list | None = None
) -> CandidateDetail:
    available_scores = candidate.scores if scores is None else scores
    user_is_admin = current_user.role == Role.admin
    visible_scores = available_scores if user_is_admin else [
        score for score in available_scores if score.reviewer_id == current_user.id
    ]

    return CandidateDetail(
        id=candidate.id,
        name=candidate.name,
        email=candidate.email,
        role_applied=candidate.role_applied,
        status=candidate.status,
        skills=candidate.skills,
        created_at=candidate.created_at,
        internal_notes=candidate.internal_notes if user_is_admin else None,
        ai_summary=candidate.ai_summary,
        ai_summary_status=candidate.ai_summary_status,
        scores=[
            ScoreOut(
                id=score.id,
                candidate_id=score.candidate_id,
                category=score.category,
                score=score.score,
                reviewer_id=score.reviewer_id,
                reviewer_email=score.reviewer.email if score.reviewer else None,
                note=score.note,
                created_at=score.created_at,
            )
            for score in visible_scores
        ],
    )


@router.get("", response_model=CandidateListResponse)
async def list_candidates(
    status_filter: CandidateStatus | None = Query(default=None, alias="status"),
    role_applied: str | None = Query(default=None),
    skill: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidates, total = await candidate_service.search_candidates(
        db,
        status=status_filter.value if status_filter else None,
        role_applied=role_applied,
        skill=skill,
        keyword=keyword,
        offset=offset,
        limit=limit,
    )
    return CandidateListResponse(items=candidates, total=total, offset=offset, limit=limit)


@router.post("", response_model=CandidateDetail, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    payload: CandidateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    candidate = Candidate(
        name=payload.name,
        email=payload.email,
        role_applied=payload.role_applied,
        skills=payload.skills,
        internal_notes=payload.internal_notes or "",
    )
    db.add(candidate)
    await db.commit()
    await db.refresh(candidate)
    return _serialize_candidate(candidate, current_user, scores=[])


@router.get("/{candidate_id}", response_model=CandidateDetail)
async def get_candidate(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidate = await candidate_service.get_candidate_with_scores(db, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return _serialize_candidate(candidate, current_user)


@router.patch("/{candidate_id}/notes", response_model=CandidateDetail)
async def update_internal_notes(
    candidate_id: str,
    payload: InternalNotesUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    candidate = await candidate_service.get_candidate_with_scores(db, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    candidate.internal_notes = payload.internal_notes
    await db.commit()
    candidate = await candidate_service.get_candidate_with_scores(db, candidate_id)
    return _serialize_candidate(candidate, current_user)


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_candidate(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    candidate = await candidate_service.get_candidate_with_scores(db, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    await candidate_service.soft_delete_candidate(db, candidate)


@router.post("/{candidate_id}/scores", response_model=ScoreOut, status_code=status.HTTP_201_CREATED)
async def submit_score(
    candidate_id: str,
    payload: ScoreCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidate = await candidate_service.get_candidate_with_scores(db, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    new_score = await candidate_service.create_score(
        db, candidate_id, current_user, payload.category, payload.score, payload.note or ""
    )
    return ScoreOut(
        id=new_score.id,
        candidate_id=new_score.candidate_id,
        category=new_score.category,
        score=new_score.score,
        reviewer_id=new_score.reviewer_id,
        reviewer_email=current_user.email,
        note=new_score.note,
        created_at=new_score.created_at,
    )


@router.post("/{candidate_id}/summary", response_model=SummaryTriggerResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_summary(
    candidate_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidate = await candidate_service.get_candidate_with_scores(db, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    candidate.ai_summary_status = SummaryStatus.pending
    candidate.ai_summary = None
    await db.commit()

    background_tasks.add_task(candidate_service.generate_ai_summary, database.AsyncSessionLocal, candidate_id)

    return SummaryTriggerResponse(ai_summary_status=SummaryStatus.pending)


@router.get("/{candidate_id}/stream")
async def stream_candidate_updates(
    candidate_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    queue = subscribe(candidate_id)

    async def event_generator():
        try:
            yield "event: connected\ndata: {}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event, data = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"event: {event}\ndata: {data}\n\n"
                except asyncio.TimeoutError:
                    yield "event: ping\ndata: {}\n\n"
        finally:
            unsubscribe(candidate_id, queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
