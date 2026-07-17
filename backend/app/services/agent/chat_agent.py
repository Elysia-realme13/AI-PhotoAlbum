"""
对话式检索代理

使用 LLM Agent 驱动照片检索与相册管理，提供完整的对话式会话管理：
  1. 创建/管理对话 session（持久化到 AgentSession / AgentMessage 表）
  2. LLM 理解意图并调用搜索、相册、统计等工具
  3. 将工具执行结果格式化为自然语言回复
  4. 保存对话历史（支持上下文追问）
""" 

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.agent import AgentSession, AgentMessage, SessionStatus
from app.services.agent.llm_agent import run_llm_agent
from app.services.name_confirmation_service import create_pending

logger = logging.getLogger(__name__)


# ── 会话管理 ────────────────────────────────────────────────


def create_session(
    db: Session,
    user_id: str,
    title: str = "新对话",
) -> AgentSession:
    """创建一个新的对话 session"""
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
    logger.info(f"创建新对话 session: {sess.id}")
    return sess


def list_sessions(
    db: Session,
    user_id: str,
    limit: int = 20,
) -> List[dict]:
    """获取用户的所有活跃 session 列表"""
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
    """按 ID 获取 session"""
    sid = uuid.UUID(session_id) if not isinstance(session_id, uuid.UUID) else session_id
    return db.query(AgentSession).filter(AgentSession.id == sid).first()


def get_messages(
    db: Session,
    session_id: str,
    limit: int = 50,
) -> List[dict]:
    """获取某 session 的消息历史"""
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


# ── 消息发送与处理 ──────────────────────────────────────────


def _build_text_reply(agent_result: dict) -> str:
    """
    将 agent 的检索结果格式化为自然语言回复
    """
    nouns = agent_result.get("nouns", [])
    person_names = agent_result.get("person_names", [])
    merged = agent_result.get("merged_results", [])
    total = len(merged)

    parts = []

    # 理解摘要
    summary_parts = []
    if nouns:
        summary_parts.append(f"我理解你想找的是关于「{'、'.join(nouns[:3])}」")
    if person_names:
        summary_parts.append(f"涉及「{'、'.join(person_names)}」")
    if summary_parts:
        parts.append(" ".join(summary_parts) + "的照片。")

    # 结果统计
    if total > 0:
        top3 = merged[:3]
        examples = "、".join(
            [f"「{p.get('photo_id', '?')[:8]}…」(匹配度 {p['score']:.0%})" for p in top3]
        )
        parts.append(
            f"共找到 {total} 张相关照片。"
            f"最匹配的例如：{examples}。"
        )
    else:
        if person_names and not agent_result.get("needs_confirmation"):
            parts.append("没有找到包含这些人物的照片。你可以换个说法试试。")
        else:
            parts.append("没有找到匹配的照片，请尝试更具体的描述。")

    return "\n".join(parts)


def send_message(
    db: Session,
    user_id: str,
    session_id: str,
    message: str,
    image_bytes: Optional[bytes] = None,
) -> dict:
    """
    发送用户消息 → 执行检索流程 → 返回回复

    流程：
      1. 保存用户消息到 AgentMessage
      2. 调用 run_search_agent 执行检索
      3. 若需要名称确认，创建 pending
      4. 格式化回复文本
      5. 保存 assistant 回复到 AgentMessage
      6. 更新 session 的 message_count / title

    Args:
        db: 数据库会话
        user_id: 用户 ID
        session_id: 对话 session ID
        message: 用户输入的文本

    Returns:
        {
            "reply": str,                    # 自然语言回复
            "results": [{"photo_id": str, "score": float}, ...],  # 检索结果
            "total": int,
            "needs_confirmation": bool,
            "pending_candidates": List[dict],
            "message_id": int,               # assistant 消息 ID
        }
    """
    # 1. 保存用户消息
    sid = uuid.UUID(session_id) if not isinstance(session_id, uuid.UUID) else session_id
    user_content = json.dumps({"text": message, "has_image": image_bytes is not None}, ensure_ascii=False) if image_bytes else message
    user_msg = AgentMessage(
        session_id=sid,
        role="user",
        content=user_content,
    )
    db.add(user_msg)

    # 2. 获取对话历史
    recent_msgs = get_messages(db, session_id, limit=20)
    history = []
    for m in recent_msgs:
        content = m["content"]
        if isinstance(content, dict):
            content = content.get("text", json.dumps(content, ensure_ascii=False))
        history.append({"role": m["role"], "content": content})

    # 3. 执行 LLM Agent
    agent_result = run_llm_agent(
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

    # 4. 保存 assistant 回复
    assistant_payload = {
        "text": reply,
        "results": results[:20],
        "total": total,
    }

    assistant_msg = AgentMessage(
        session_id=sid,
        role="assistant",
        content=json.dumps(assistant_payload, ensure_ascii=False),
        tool_calls=tool_calls_log,
    )
    db.add(assistant_msg)

    # 5. 更新 session
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
        "results": results[:20],
        "total": total,
        "needs_confirmation": False,
        "pending_candidates": [],
        "message_id": assistant_msg.id,
    }


def delete_session(db: Session, session_id: str) -> bool:
    """删除一个对话 session（cascade 自动清理关联消息）"""
    sid = uuid.UUID(session_id) if not isinstance(session_id, uuid.UUID) else session_id
    sess = db.query(AgentSession).filter(AgentSession.id == sid).first()
    if not sess:
        return False
    db.delete(sess)
    db.commit()
    logger.info(f"删除对话 session: {session_id}")
    return True


__all__ = [
    "create_session",
    "list_sessions",
    "get_session",
    "get_messages",
    "send_message",
    "delete_session",
]
