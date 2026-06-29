"""消息与长期记忆模型。"""
from datetime import datetime
from sqlalchemy import (
    BigInteger, String, DateTime, INT, JSON, ForeignKey, Text, DECIMAL,
)
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class Message(Base, TimestampMixin):
    """问答消息（多模态）。"""

    msg_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.user_id"), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # user/assistant/system
    input_type: Mapped[str] = mapped_column(String(16), nullable=False)  # image/voice/text
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_media_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    processed_media_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    asr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("prompt_template.prompt_id"), nullable=True)
    api_config_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("api_config.api_config_id"), nullable=True)
    intercepted: Mapped[int] = mapped_column(TINYINT, default=0, nullable=False)
    risk_tags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(INT, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="success", nullable=False)  # success/timeout/error


class LongTermMemory(Base, TimestampMixin):
    """长期记忆 = RAG 知识库。"""

    memory_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("user.user_id"), nullable=True, index=True)  # 通用知识可空
    memory_type: Mapped[str] = mapped_column(String(32), nullable=False)  # 用药/健康/偏好/医嘱/通用
    source: Mapped[str] = mapped_column(String(16), default="dialog", nullable=False)  # dialog/admin/system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vector_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)  # Chroma 对应 ID
    importance: Mapped[int] = mapped_column(TINYINT, default=3, nullable=False)  # 1-5
    source_msg_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("message.msg_id"), nullable=True)
    is_deleted: Mapped[int] = mapped_column(TINYINT, default=0, nullable=False)
