"""媒体相关 schema：图片上传、图像增强、语音上传。"""
from datetime import datetime
from pydantic import BaseModel, Field


class ImageUploadOut(BaseModel):
    """图片上传成功响应。上传即增强，返回原图与增强图两个 URL。"""
    media_id: str = Field(..., description="媒体 ID（用于后续引用）", examples=["img_20260627_a1b2c3"])
    url: str = Field(..., description="原图 URL", examples=["/files/img_20260627_a1b2c3.jpg"])
    enhanced_url: str = Field(..., description="增强后图 URL（Gamma 校正），QA 问答时传此 URL", examples=["/files/img_20260627_a1b2c3_enhanced.jpg"])
    filename: str = Field(..., description="原始文件名", examples=["pill_box.jpg"])
    size: int = Field(..., description="文件大小（字节）", examples=[102400])
    width: int | None = Field(None, description="图片宽度（px）", examples=[1920])
    height: int | None = Field(None, description="图片高度（px）", examples=[1080])
    operations: list[str] = Field(default_factory=list, description="执行的增强操作列表", examples=[["gamma_1.3"]])
    uploaded_at: datetime = Field(..., description="上传时间", examples=["2026-06-27T07:00:00Z"])


class ImageEnhanceIn(BaseModel):
    """图像增强入参（手动调参用，一般不需要调，上传即增强）。"""
    url: str = Field(..., description="待增强的图片 URL", examples=["/files/img_xxx.jpg"])
    brightness: float = Field(
        default=1.3, ge=0.3, le=3.0,
        description="Gamma 校正系数。1.0=原图，>1 增亮（老人拍照暗建议 1.3-1.5），<1 变暗",
        examples=[1.3],
    )


class ImageEnhanceOut(BaseModel):
    """图像增强响应。"""
    original_url: str = Field(..., description="原图 URL", examples=["/files/img_xxx.jpg"])
    enhanced_url: str = Field(..., description="增强后图 URL", examples=["/files/img_xxx_enhanced.jpg"])
    operations: list[str] = Field(..., description="执行的操作列表", examples=[["gamma_1.3"]])


class VoiceUploadOut(BaseModel):
    """语音上传成功响应。上传即转写，返回 asr_text。"""
    media_id: str = Field(..., description="媒体 ID", examples=["voice_20260627_d4e5f6"])
    url: str = Field(..., description="可访问的语音 URL", examples=["/files/voice_20260627_d4e5f6.wav"])
    filename: str = Field(..., description="原始文件名", examples=["question.wav"])
    size: int = Field(..., description="文件大小（字节）", examples=[204800])
    duration_sec: int | None = Field(None, description="语音时长（秒），未解析时为 null", examples=[5])
    asr_text: str = Field(..., description="语音转写文本（faster-whisper 自动识别）", examples=["我今天头疼，该吃什么药？"])
    uploaded_at: datetime = Field(..., description="上传时间", examples=["2026-06-27T07:00:00Z"])
