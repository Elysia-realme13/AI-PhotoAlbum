"""
Agent Chat API - session management and message handling
POST /api/agent/sessions              -  create session
GET  /api/agent/sessions              -  list sessions
GET  /api/agent/sessions/{id}/messages -  get messages
POST /api/agent/sessions/{id}/messages -  send message
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.api.deps import get_required_user
from app.models.user import User
from app.services.agent.chat_agent import (
    create_session as _create_session,
    list_sessions as _list_sessions,
    get_session as _get_session,
    get_messages as _get_messages,
    send_message as _send_message,
)

router = APIRouter(prefix="/api/agent", tags=["agent"])


class CreateSessionRequest(BaseModel):
    title: str = "new chat"


class SessionResponse(BaseModel):
    id: str
    title: str
    message_count: int
    created_at: str
    updated_at: str


class MessageItem(BaseModel):
    id: int
    role: str
    content: object
    tool_calls: Optional[dict] = None
    created_at: str


class SendMessageRequest(BaseModel):
    message: str


class SendMessageResponse(BaseModel):
    reply: str
    results: List[dict] = []
    total: int = 0
    needs_confirmation: bool = False
    pending_candidates: List[dict] = []
    message_id: int


@router.post("/sessions", response_model=SessionResponse)
def create_session(
    req: CreateSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    sess = _create_session(db, user_id=str(current_user.id), title=req.title)
    return SessionResponse(
        id=str(sess.id), title=sess.title,
        message_count=sess.message_count or 0,
        created_at=sess.created_at.isoformat(),
        updated_at=sess.updated_at.isoformat(),
    )


@router.get("/sessions", response_model=List[SessionResponse])
def list_session(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    sessions = _list_sessions(db, user_id=str(current_user.id))
    return [SessionResponse(**s) for s in sessions]


@router.get("/sessions/{session_id}/messages", response_model=List[MessageItem])
def get_session_messages(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    sess = _get_session(db, session_id)
    if not sess:
        raise HTTPException(404, "session not found")
    if str(sess.user_id) != str(current_user.id):
        raise HTTPException(403, "forbidden")
    messages = _get_messages(db, session_id)
    return [MessageItem(**m) for m in messages]


@router.post("/sessions/{session_id}/messages", response_model=SendMessageResponse)
def send_message(
    session_id: str,
    req: SendMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    sess = _get_session(db, session_id)
    if not sess:
        raise HTTPException(404, "session not found")
    if str(sess.user_id) != str(current_user.id):
        raise HTTPException(403, "forbidden")

    result = _send_message(
        db=db, user_id=str(current_user.id),
        session_id=session_id, message=req.message,
    )
    return SendMessageResponse(**result)
