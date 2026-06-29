"""预警路由。

老人端接口：
- POST /alert/emergency/call  一键紧急呼叫

子女端/管理端接口后续补充：预警列表/详情/处置/实时推送WS
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import DB, ElderUser
from app.models.interaction import AlertEvent
from app.models.user import ChildUser, UserChildRelation, WxAccount
from app.schemas.common import R


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/alert", tags=["alert"])


@router.post(
    "/emergency/call",
    response_model=R,
    summary="一键紧急呼叫（老人端）",
    description="""
老人端点击紧急按钮后调用，**仅老人端可调**。

**流程**：
1. 写 `alert_event`（类型=紧急呼叫，级别=紧急，来源=manual）
2. 推送所有绑定子女的订阅消息
3. 返回 alert_id

**子女端响应**：收到 `alert.urgent` 类型订阅消息；30s 未确认→短信；60s 未确认→电话（见 05 文档 5.8 节）。
""".strip(),
    response_description="呼叫成功，返回预警 ID",
    responses={
        200: {"description": "呼叫成功", "content": {"application/json": {"example": {
            "code": 0, "msg": "ok",
            "data": {"alert_id": 1, "alert_time": "2026-06-29T09:00:00Z"},
        }}}},
        401: {"description": "未认证"},
        403: {"description": "非老人端 token"},
    },
)
async def emergency_call(cur: ElderUser, db: DB):
    now = datetime.now(timezone.utc)
    alert = AlertEvent(
        user_id=cur.ref_id,
        alert_type="紧急呼叫",
        alert_level="紧急",
        trigger_source="manual",
        alert_time=now,
        detail=f"老人 {cur.ref_id} 主动发起紧急呼叫",
        handling_status="待处理",
        notify_channels=[{"channel": "subscribe", "status": "pending"}],
    )
    db.add(alert)
    await db.flush()

    # 推送所有绑定子女
    await _notify_children(db, cur.ref_id, "紧急呼叫", "紧急", f"老人 {cur.ref_id} 主动发起紧急呼叫")

    logger.warning("⚠️ 老人 %s 发起紧急呼叫！alert_id=%s", cur.ref_id, alert.alert_id)
    return R.ok({"alert_id": alert.alert_id, "alert_time": now.isoformat()})


async def _notify_children(db, user_id: int, alert_type: str, alert_level: str, detail: str):
    """通知所有绑定子女（dev 模式仅打日志）。"""
    relations = (await db.execute(
        select(UserChildRelation).where(UserChildRelation.user_id == user_id)
    )).scalars().all()

    if not relations:
        logger.warning("老人 %s 无绑定子女，无法推送紧急呼叫", user_id)
        return

    from app.core.wx import send_subscribe_message
    for rel in relations:
        child = await db.get(ChildUser, rel.child_id)
        if not child or not child.wx_account_id:
            continue
        acc = await db.get(WxAccount, child.wx_account_id)
        if not acc:
            continue
        try:
            await send_subscribe_message(
                openid=acc.openid,
                template_id="tpl_alert_urgent",
                data={
                    "thing1": {"value": f"老人{user_id}"},
                    "thing2": {"value": alert_type},
                    "time3": {"value": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")},
                    "thing4": {"value": detail[:20]},
                },
            )
        except Exception as e:
            logger.warning("推送紧急呼叫给子女 %s 失败: %s", rel.child_id, e)
