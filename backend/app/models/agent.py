"""
Agent 对话模型
"""
import uuid
import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, ForeignKey, DateTime, Text, JSON, Integer, Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database.session import Base


class SessionStatus(str, enum.Enum):
    active = "active"
    archived = "archived"


class AgentSession(Base):
    """Agent 对话会话"""
    __tablename__ = "agent_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), comment="会话标题")
    status = Column(SAEnum(SessionStatus), default=SessionStatus.active)
    message_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联关系
    user = relationship("User", back_populates="agent_sessions")
    messages = relationship(
        "AgentMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="AgentMessage.created_at",
    )


class AgentMessage(Base):
    """Agent 对话消息"""
    __tablename__ = "agent_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        UUID(as_uuid=True), ForeignKey("agent_sessions.id"), nullable=False, index=True
    )
    role = Column(String(20), nullable=False, comment="user / assistant / tool")
    content = Column(Text, nullable=False, comment="消息内容")
    tool_calls = Column(JSON, comment="工具调用记录")
    created_at = Column(DateTime, default=datetime.now, index=True)

    # 关联关系
    session = relationship("AgentSession", back_populates="messages")
