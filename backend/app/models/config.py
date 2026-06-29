"""配置类模型：API接口配置、提示词模板、订阅模板、审计日志。"""
from datetime import datetime
from sqlalchemy import (
    BigInteger, String, DateTime, JSON, Text, Integer,
)
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin


class ApiConfig(Base, TimestampMixin):
    """大模型 API 接口配置（服务端集中管理）。"""

    api_config_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key_enc: Mapped[str] = mapped_column(Text, nullable=False)  # 加密存储
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    timeout: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    enabled: Mapped[int] = mapped_column(TINYINT, default=1, nullable=False)
    is_default: Mapped[int] = mapped_column(TINYINT, default=0, nullable=False)


class PromptTemplate(Base, TimestampMixin):
    """提示词模板。"""

    prompt_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(String(32), default="1.0", nullable=False)
    enabled: Mapped[int] = mapped_column(TINYINT, default=1, nullable=False)


class SubscribeTemplate(Base, TimestampMixin):
    """订阅消息模板登记。"""

    subscribe_template_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    template_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)  # medication.remind / alert.urgent 等
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    scene: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[int] = mapped_column(TINYINT, default=1, nullable=False)


class AuditLog(Base):
    """审计日志（保留 180 天）。"""

    audit_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    operator_type: Mapped[str] = mapped_column(String(16), nullable=False)  # user/child/admin/system
    operator_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    operation: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ua: Mapped[str | None] = mapped_column(String(255), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
