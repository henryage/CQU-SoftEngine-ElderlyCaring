"""子女端相关 schema。"""
from datetime import datetime
from pydantic import BaseModel, Field


class BindIn(BaseModel):
    """绑定老人入参——使用验证码替代直接传 user_id。"""
    code: str = Field(..., description="老人端生成的 6 位绑定验证码", min_length=6, max_length=6, examples=["385721"])
    relation: str = Field(default="子女", description="关系：子女/亲属/医生", examples=["母亲"])


class BindedUserOut(BaseModel):
    """绑定的老人概要。"""
    user_id: int = Field(..., description="老人ID")
    nickname: str = Field(..., description="昵称")
    relation: str = Field(..., description="关系")
    is_online: bool = Field(default=False, description="是否在线")
    last_heartbeat_at: str | None = Field(None, description="最后心跳时间")
    unread_alerts: int = Field(default=0, description="未读预警数")
    today_qa_count: int = Field(default=0, description="今日问答次数")


class DashboardOut(BaseModel):
    """健康看板。"""
    user_id: int
    nickname: str
    is_online: bool
    today_qa_count: int = Field(default=0)
    pending_alerts: int = Field(default=0)
    active_reminders: int = Field(default=0)
    recent_messages: list[dict] = Field(default_factory=list)
    health_tags: list[str] = Field(default_factory=list)


class MessageItem(BaseModel):
    """问答记录条目。"""
    msg_id: int
    input_type: str
    question: str | None
    answer: str | None
    intercepted: bool
    risk_tags: list | None
    created_at: str | None


class SettingsIn(BaseModel):
    """适老化配置入参。"""
    font_size: str = Field(default="normal", description="normal / large / xlarge")
    voice_enabled: bool = Field(default=True)
    simplified_mode: bool = Field(default=False)
