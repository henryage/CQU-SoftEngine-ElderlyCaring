"""行为轨迹、预警、通信、设置模型。"""
from datetime import datetime
from sqlalchemy import (
    BigInteger, String, DateTime, INT, JSON, ForeignKey, Text,
)
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin


class BehaviorTrace(Base):
    """老人行为轨迹。"""

    trace_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.user_id"), nullable=False, index=True)
    trace_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    trace_type: Mapped[str] = mapped_column(String(32), nullable=False)  # 问答/陪伴/用药咨询/通信
    content_summary: Mapped[str | None] = mapped_column(String(255), nullable=True)
    identified_object: Mapped[str | None] = mapped_column(String(64), nullable=True)
    risk_level: Mapped[str] = mapped_column(String(8), default="无", nullable=False)  # 无/低/中/高


class AlertEvent(Base, TimestampMixin):
    """预警事件（大模型触发 + 规则触发 + 主动触发）。"""

    alert_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.user_id"), nullable=False, index=True)
    alert_type: Mapped[str] = mapped_column(String(32), nullable=False)  # 无活动/用药异常/跌倒/情绪低落/紧急呼叫/网络断开/网络恢复
    alert_level: Mapped[str] = mapped_column(String(8), nullable=False)  # 提醒/警告/紧急
    trigger_source: Mapped[str] = mapped_column(String(16), nullable=False)  # llm/rule/manual
    trigger_msg_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("message.msg_id"), nullable=True)
    alert_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    handling_status: Mapped[str] = mapped_column(String(16), default="待处理", nullable=False)  # 待处理/已确认/转医生/已忽略
    handled_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("child_user.child_id"), nullable=True)
    handled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    handle_remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    notify_channels: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class CommunicationLog(Base):
    """通信记录（仅 text/voice）。"""

    comm_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    child_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("child_user.child_id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.user_id"), nullable=False, index=True)
    comm_type: Mapped[str] = mapped_column(String(16), nullable=False)  # text/voice
    direction: Mapped[str] = mapped_column(String(16), nullable=False)  # child_to_user/user_to_child
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_sec: Mapped[int | None] = mapped_column(INT, nullable=True)
    comm_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)


class SettingChange(Base):
    """适老化设置变更记录。"""

    change_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    child_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("child_user.child_id"), nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.user_id"), nullable=False, index=True)
    setting_key: Mapped[str] = mapped_column(String(64), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    change_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    sync_status: Mapped[str] = mapped_column(String(16), default="待同步", nullable=False)  # 已同步/待同步


class UserSetting(Base):
    """老人当前生效配置（与 setting_change 配套）。"""

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.user_id"), primary_key=True)
    setting_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    setting_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class MedicationReminder(Base, TimestampMixin):
    """用药提醒。"""

    reminder_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.user_id"), nullable=False, index=True)
    drug_name: Mapped[str] = mapped_column(String(128), nullable=False)
    dosage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    remind_time: Mapped[str] = mapped_column(String(16), nullable=False)  # HH:MM
    cron_expr: Mapped[str | None] = mapped_column(String(64), nullable=True)
    active: Mapped[int] = mapped_column(TINYINT, default=1, nullable=False)


class GreetingSchedule(Base, TimestampMixin):
    """定时问候。"""

    greeting_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.user_id"), nullable=False, index=True)
    child_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("child_user.child_id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    cron_expr: Mapped[str] = mapped_column(String(64), nullable=False)
    active: Mapped[int] = mapped_column(TINYINT, default=1, nullable=False)


class SubscribeGrant(Base, TimestampMixin):
    """订阅消息授权记录。"""

    grant_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("wx_account.account_id"), nullable=False, index=True)
    template_id: Mapped[str] = mapped_column(String(64), nullable=False)
    grant_status: Mapped[str] = mapped_column(String(16), nullable=False)  # accept/reject/ban
    granted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expire_count: Mapped[int] = mapped_column(INT, default=0, nullable=False)
