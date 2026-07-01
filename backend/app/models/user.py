"""用户体系模型：user(老人) / child_user / wx_account / user_child_relation / admin_user。"""
from datetime import datetime
from sqlalchemy import (
    BigInteger, String, Date, DateTime, JSON, ForeignKey, Text,
)
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class WxAccount(Base, TimestampMixin):
    """微信账号绑定 - openid/unionid 与系统用户的桥。"""

    account_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    openid: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    unionid: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    session_key: Mapped[str | None] = mapped_column(String(128), nullable=True)  # 加密存储
    user_type: Mapped[str] = mapped_column(String(8), nullable=False)  # user / child
    ref_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # 关联 user_id 或 child_id
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class User(Base, TimestampMixin):
    """老人用户。"""

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    nickname: Mapped[str] = mapped_column(String(64), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    birth_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    gender: Mapped[int | None] = mapped_column(TINYINT, nullable=True)  # 0未知 1男 2女
    wx_account_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("wx_account.account_id"), nullable=True)
    status: Mapped[int] = mapped_column(TINYINT, default=1, nullable=False)  # 1正常 0禁用
    # 心跳与在线状态（用于网络断开自动预警）
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    online_status: Mapped[str] = mapped_column(String(16), default="offline", nullable=False)  # online/offline
    # 绑定验证码（老人端生成，子女端输入后绑定）
    bind_code: Mapped[str | None] = mapped_column(String(8), nullable=True, index=True)
    bind_code_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    wx_account = relationship("WxAccount", lazy="joined")


class ChildUser(Base, TimestampMixin):
    """子女/亲属/医生。"""

    child_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(128), nullable=True)
    wx_account_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("wx_account.account_id"), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)  # dev 模式可空
    relation: Mapped[str | None] = mapped_column(String(32), nullable=True)

    wx_account = relationship("WxAccount", lazy="joined")


class UserChildRelation(Base, TimestampMixin):
    """老人-子女多对多绑定。"""

    relation_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.user_id"), nullable=False, index=True)
    child_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("child_user.child_id"), nullable=False, index=True)
    relation: Mapped[str] = mapped_column(String(32), nullable=False)  # 子女/亲属/医生
    is_primary: Mapped[int] = mapped_column(TINYINT, default=0, nullable=False)


class AdminUser(Base, TimestampMixin):
    """管理员。"""

    admin_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="OPERATOR", nullable=False)  # SUPER / OPERATOR
