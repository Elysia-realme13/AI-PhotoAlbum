"""
Search API - hybrid CLIP + face search via LangGraph agent
POST /api/search  -  text -> photo results
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.api.deps import get_required_user
from app.models.user import User
from app.crud.photo import get_photo_by_id
from app.services.agent.search_agent import run_search_agent
from app.services.name_confirmation_service import create_pending

router = APIRouter(prefix="/api/search", tags=["search"])


class SearchRequest(BaseModel):
    query: str
    page: int = 1
    page_size: int = 20


class SearchHit(BaseModel):
    photo_id: str
    score: float
    thumbnail_url: str
    file_url: str
    original_name: Optional[str] = None


class SearchResponse(BaseModel):
    results: List[SearchHit]
    total: int
    needs_confirmation: bool = False
    pending_candidates: List[dict] = []
    session_id: Optional[str] = None


@router.post("", response_model=SearchResponse)
def search(
    req: SearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    agent_result = run_search_agent(
        query=req.query, db=db,
        owner_id=str(current_user.id),
        session_id=str(current_user.id),
    )

    if agent_result.get("error"):
        raise HTTPException(400, agent_result["error"])

    needs_confirmation = agent_result.get("needs_confirmation", False)
    pending_candidates = agent_result.get("pending_candidates", [])

    if needs_confirmation and pending_candidates:
        create_pending(
            session_id=str(current_user.id),
            query=req.query,
            candidates=pending_candidates,
        )

    merged = agent_result.get("merged_results", [])
    start = (req.page - 1) * req.page_size
    end = start + req.page_size
    page_items = merged[start:end]

    results = []
    for hit in page_items:
        photo = get_photo_by_id(db, hit["photo_id"])
        if photo:
            results.append(SearchHit(
                photo_id=hit["photo_id"],
                score=hit["score"],
                thumbnail_url=f"/api/medias/{hit['photo_id']}/thumbnail",
                file_url=f"/api/medias/{hit['photo_id']}/file",
                original_name=photo.original_name,
            ))

    return SearchResponse(
        results=results,
        total=len(merged),
        needs_confirmation=needs_confirmation,
        pending_candidates=pending_candidates,
        session_id=str(current_user.id),
    )
