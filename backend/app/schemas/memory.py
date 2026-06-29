"""记忆相关 schema：列表、新增、编辑、语义检索。"""
from datetime import datetime
from pydantic import BaseModel, Field


class MemoryIn(BaseModel):
    """新增/编辑记忆入参。"""
    user_id: int = Field(..., description="老人 ID", examples=[6])
    memory_type: str = Field(..., description="类型：用药/健康/偏好/医嘱/通用", examples=["用药"])
    source: str = Field(
        default="admin",
        description="来源：admin=手动 / dialog=对话抽取 / system=系统",
        examples=["admin"],
    )
    content: str = Field(..., max_length=5000, description="记忆内容", examples=["爸爸对青霉素过敏，不能使用。2025年确诊。"])
    summary: str | None = Field(default=None, max_length=255, description="摘要（不填自动截取前100字）", examples=["爸爸对青霉素过敏"])
    importance: int = Field(default=3, ge=1, le=5, description="重要度 1-5，5最重要", examples=[5])
    # TODO: source_msg_id 暂不暴露。后续大模型自动从对话抽取记忆时补充此字段


class MemoryOut(BaseModel):
    """记忆响应。"""
    memory_id: int = Field(..., description="记忆 ID", examples=[1])
    user_id: int | None = Field(None, description="老人 ID（通用知识为 null）")
    memory_type: str = Field(..., description="类型")
    source: str = Field(..., description="来源")
    content: str = Field(..., description="内容")
    summary: str | None = Field(None, description="摘要")
    vector_id: str | None = Field(None, description="Chroma 向量 ID")
    importance: int = Field(..., description="重要度 1-5")
    source_msg_id: int | None = Field(None, description="来源消息ID")
    is_deleted: bool = Field(default=False, description="是否已删除")
    created_at: str | None = Field(None, description="创建时间", examples=["2026-06-29T10:00:00Z"])
    updated_at: str | None = Field(None, description="更新时间")


class MemoryImportanceIn(BaseModel):
    """重要度调整入参。"""
    importance: int = Field(..., ge=1, le=5, description="重要度 1-5", examples=[5])


class MemorySearchIn(BaseModel):
    """语义检索入参。"""
    user_id: int = Field(..., description="老人 ID（限定检索范围）", examples=[6])
    query: str = Field(..., max_length=1000, description="检索问题", examples=["爸爸对什么过敏？"])
    top_k: int = Field(default=5, ge=1, le=10, description="返回条数", examples=[5])


class MemorySearchOut(BaseModel):
    """语义检索结果。"""
    memory_id: int = Field(..., description="记忆 ID")
    content: str = Field(..., description="完整内容")
    summary: str | None = Field(None, description="摘要")
    memory_type: str = Field(..., description="类型")
    importance: int = Field(..., description="重要度")
    score: float = Field(..., description="语义相似度得分（0-1）", examples=[0.89])
