"""QA 相关 schema。"""
from datetime import datetime
from pydantic import BaseModel, Field


class QAAskIn(BaseModel):
    """提交问答入参。"""
    input_type: str = Field(
        default="text",
        description="输入类型：text / image / voice",
    )
    text: str | None = Field(
        default=None,
        max_length=2000,
        description="文本提问（input_type=text 时必填）；image/voice 时可作为补充说明",
    )
    media_url: str | None = Field(
        default=None,
        description="图片或语音的 URL（input_type=image/voice 时必填。上传图片时已自动增强，传 enhanced_url 即可）",
    )
    session_id: str | None = Field(
        default=None,
        description="会话 ID。不填则后端生成新会话；填了则归入同一会话",
    )


class QAAskOut(BaseModel):
    """问答响应（同步模式）。"""
    msg_id: int = Field(..., description="消息记录 ID", examples=[1])
    session_id: str = Field(..., description="会话 ID", examples=["sess_20260627_a1b2c3"])
    answer: str = Field(..., description="大模型回答", examples=["这是一盒布洛芬缓释胶囊..."])
    intercepted: bool = Field(..., description="是否触发医疗合规拦截", examples=[False])
    risk_tags: list[str] | None = Field(None, description="风险标签", examples=[["药品"]])
    latency_ms: int = Field(..., description="调用耗时（毫秒）", examples=[2350])
    cat_action: str = Field(..., description="小猫动作状态：listen/think/speak/confuse/soothe", examples=["speak"])
    alert_signal: dict | None = Field(
        default=None,
        description="大模型识别的预警信号（如有），格式 {alert_type, alert_level, detail}",
        examples=[{"alert_type": "fall", "alert_level": "紧急", "detail": "老人提到跌倒"}],
    )


class QAHistoryQuery(BaseModel):
    """历史问答查询参数。"""
    page: int = Field(default=1, ge=1, description="页码", examples=[1])
    page_size: int = Field(default=20, ge=1, le=100, description="每页条数", examples=[20])
    input_type: str | None = Field(default=None, description="按输入类型筛选：text/image/voice", examples=["image"])
    keyword: str | None = Field(default=None, description="关键字模糊匹配（问题+回答）", examples=["布洛芬"])
    start_date: str | None = Field(default=None, description="开始日期 YYYY-MM-DD", examples=["2026-06-01"])
    end_date: str | None = Field(default=None, description="结束日期 YYYY-MM-DD", examples=["2026-06-27"])
