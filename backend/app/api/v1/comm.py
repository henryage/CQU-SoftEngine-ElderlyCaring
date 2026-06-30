"""通信路由（子女端 ↔ 老人端）。"""
from fastapi import APIRouter
from app.core.deps import AnyRole
from app.schemas.common import R


router = APIRouter(prefix="/child", tags=["comm"])


@router.post("/send-message", response_model=R, summary="发送留言（临时桩）")
async def send_message(cur: AnyRole):
    """TODO: 实现子女→老人文字留言写入 communication_log 表"""
    return R.ok({"status": "sent"}, msg="留言已发送（dev模式仅确认）")
