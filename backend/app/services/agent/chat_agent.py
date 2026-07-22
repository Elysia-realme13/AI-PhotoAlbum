"""Conversational retrieval agent --- supervisor-driven with session management.

Session management:
  1. Create/manage chat sessions (persisted in AgentSession / AgentMessage).
  2. Supervisor routes intent to specialist agents.
  3. Format results into natural-language replies.
  4. Save conversation history for context-aware follow-up.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.agent import AgentSession, AgentMessage, SessionStatus
from app.services.agent.supervisor import run_supervisor
from app.services.name_confirmation_service import create_pending

logger = logging.getLogger(__name__)


# --- Session management ----------------------------------------------------


def create_session(
    db: Session,
    user_id: str,
    title: str = "new chat",
) -> AgentSession:
    """Create a new chat session."""
    sess = AgentSession(
        id=uuid.uuid4(),
        user_id=uuid.UUID(user_id) if not isinstance(user_id, uuid.UUID) else user_id,
        title=title,
        status=SessionStatus.active,
        message_count=0,
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    logger.info(f"Created new chat session: {sess.id}")
    return sess


def list_sessions(
    db: Session,
    user_id: str,
    limit: int = 20,
) -> List[dict]:
    """List all active sessions for a user."""
    uid = uuid.UUID(user_id) if not isinstance(user_id, uuid.UUID) else user_id
    sessions = (
        db.query(AgentSession)
        .filter(
            AgentSession.user_id == uid,
            AgentSession.status == SessionStatus.active,
        )
        .order_by(AgentSession.updated_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": str(s.id),
            "title": s.title,
            "message_count": s.message_count,
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
        }
        for s in sessions
    ]


def get_session(db: Session, session_id: str) -> Optional[AgentSession]:
    """Get a session by ID."""
    sid = uuid.UUID(session_id) if not isinstance(session_id, uuid.UUID) else session_id
    return db.query(AgentSession).filter(AgentSession.id == sid).first()


def get_messages(
    db: Session,
    session_id: str,
    limit: int = 50,
) -> List[dict]:
    """Get message history for a session."""
    sid = uuid.UUID(session_id) if not isinstance(session_id, uuid.UUID) else session_id
    msgs = (
        db.query(AgentMessage)
        .filter(AgentMessage.session_id == sid)
        .order_by(AgentMessage.created_at.asc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": json.loads(m.content) if m.role == "assistant" else m.content,
            "tool_calls": m.tool_calls,
            "created_at": m.created_at.isoformat(),
        }
        for m in msgs
    ]


# --- Message send & processing ---------------------------------------------


def send_message(
    db: Session,
    user_id: str,
    session_id: str,
    message: str,
    image_bytes: Optional[bytes] = None,
) -> dict:
    """Send user message -> Supervisor routes to specialists -> return reply.

    Flow:
      1. Save user message to AgentMessage.
      2. Get conversation history.
      3. Call Supervisor Agent to route and execute.
      4. Save assistant reply to AgentMessage.
      5. Update session metadata.

    Returns:
        {"reply": str, "results": list, "total": int, "message_id": int}
    """
    # 1. Save user message
    sid = uuid.UUID(session_id) if not isinstance(session_id, uuid.UUID) else session_id
    user_content = (
        json.dumps({"text": message, "has_image": image_bytes is not None}, ensure_ascii=False)
        if image_bytes else message
    )
    user_msg = AgentMessage(
        session_id=sid,
        role="user",
        content=user_content,
    )
    db.add(user_msg)

    # 2. Get conversation history
    recent_msgs = get_messages(db, session_id, limit=20)
    history = []
    for m in recent_msgs:
        content = m["content"]
        if isinstance(content, dict):
            content = content.get("text", json.dumps(content, ensure_ascii=False))
        history.append({"role": m["role"], "content": content})

    # 3. Execute Supervisor Agent
    agent_result = run_supervisor(
        user_message=message,
        db=db,
        owner_id=user_id,
        session_id=session_id,
        history=history,
        image_bytes=image_bytes,
    )

    reply = agent_result["reply"]
    results = agent_result["results"]
    total = agent_result["total"]
    tool_calls_log = agent_result.get("tool_calls", [])

    # 4. Save assistant reply
    assistant_payload = {
        "text": reply,
        "results": results,
        "total": total,
    }

    assistant_msg = AgentMessage(
        session_id=sid,
        role="assistant",
        content=json.dumps(assistant_payload, ensure_ascii=False),
        tool_calls=tool_calls_log,
    )
    db.add(assistant_msg)

    # 5. Update session
    sess = db.query(AgentSession).filter(AgentSession.id == sid).first()
    if sess:
        sess.message_count = (sess.message_count or 0) + 2
        sess.updated_at = datetime.now()
        if sess.message_count <= 2 and len(message) <= 50:
            sess.title = message
        elif sess.message_count <= 2:
            sess.title = message[:50] + "..."

    db.commit()

    return {
        "reply": reply,
        "results": results,
        "total": total,
        "needs_confirmation": False,
        "pending_candidates": [],
        "message_id": assistant_msg.id,
    }


def delete_session(db: Session, session_id: str) -> bool:
    """Delete a chat session (cascade auto-cleans related messages)."""
    sid = uuid.UUID(session_id) if not isinstance(session_id, uuid.UUID) else session_id
    sess = db.query(AgentSession).filter(AgentSession.id == sid).first()
    if not sess:
        return False
    db.delete(sess)
    db.commit()
    logger.info(f"Deleted chat session: {session_id}")
    return True


__all__ = [
    "create_session",
    "list_sessions",
    "get_session",
    "get_messages",
    "send_message",
    "delete_session",
]