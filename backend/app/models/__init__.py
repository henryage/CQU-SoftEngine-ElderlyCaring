"""统一导出所有模型，供 Alembic 与 app 引用。"""
from app.models.user import (
    WxAccount, User, ChildUser, UserChildRelation, AdminUser,
)
from app.models.message import Message, LongTermMemory
from app.models.profile import UserProfile, UserProfileDimension
from app.models.interaction import (
    BehaviorTrace, AlertEvent, CommunicationLog, SettingChange,
    UserSetting, MedicationReminder, GreetingSchedule, SubscribeGrant,
)
from app.models.config import ApiConfig, PromptTemplate, SubscribeTemplate, AuditLog

__all__ = [
    # 用户体系
    "WxAccount", "User", "ChildUser", "UserChildRelation", "AdminUser",
    # 消息与记忆
    "Message", "LongTermMemory",
    # 画像
    "UserProfile", "UserProfileDimension",
    # 交互
    "BehaviorTrace", "AlertEvent", "CommunicationLog", "SettingChange",
    "UserSetting", "MedicationReminder", "GreetingSchedule", "SubscribeGrant",
    # 配置
    "ApiConfig", "PromptTemplate", "SubscribeTemplate", "AuditLog",
]
