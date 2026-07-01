"""预警路由。

老人端：
- POST /alert/emergency/call  一键紧急呼叫

子女端：
- GET    /alert                    预警列表
- GET    /alert/{alert_id}         预警详情
- PATCH  /alert/{alert_id}/handle  处置预警
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select, func, and_

from app.core.deps import DB, ElderUser, ChildRole
from app.models.interaction import AlertEvent
from app.models.user import ChildUser, UserChildRelation, WxAccount
from app.schemas.common import R, Page


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/alert", tags=["alert"])


# ── 老人端：紧急呼叫 ──────────────────────────

@router.post("/emergency/call", response_model=R, summary="一键紧急呼叫（老人端）")
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
    await _notify_children(db, cur.ref_id, "紧急呼叫", "紧急", f"老人 {cur.ref_id} 主动发起紧急呼叫")
    logger.warning("⚠️ 老人 %s 发起紧急呼叫！alert_id=%s", cur.ref_id, alert.alert_id)
    return R.ok({"alert_id": alert.alert_id, "alert_time": now.isoformat()})


async def _notify_children(db, user_id: int, alert_type: str, alert_level: str, detail: str):
    relations = (await db.execute(
        select(UserChildRelation).where(UserChildRelation.user_id == user_id)
    )).scalars().all()
    if not relations:
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
                openid=acc.openid, template_id="tpl_alert_urgent",
                data={
                    "thing1": {"value": f"老人{user_id}"},
                    "thing2": {"value": alert_type},
                    "time3": {"value": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")},
                    "thing4": {"value": detail[:20]},
                },
            )
        except Exception as e:
            logger.warning("推送紧急呼叫给子女 %s 失败: %s", rel.child_id, e)


# ── 子女端：预警列表/详情/处置 ─────────────────

def _alert_out(a: AlertEvent) -> dict:
    return {
        "alert_id": a.alert_id,
        "user_id": a.user_id,
        "alert_type": a.alert_type,
        "alert_level": a.alert_level,
        "trigger_source": a.trigger_source,
        "detail": a.detail,
        "handling_status": a.handling_status,
        "handled_by": a.handled_by,
        "handled_at": a.handled_at.isoformat() if a.handled_at else None,
        "handle_remark": a.handle_remark,
        "alert_time": a.alert_time.isoformat() if a.alert_time else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@router.get("", response_model=R, summary="预警列表（子女端）")
async def list_alerts(
    cur: ChildRole, db: DB,
    user_id: int = Query(..., description="老人ID"),
    status_filter: str = Query(None, alias="status", description="待处理/已确认/转医生/已忽略"),
    level: str = Query(None, description="提醒/警告/紧急"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    # 校验绑定
    rel = (await db.execute(
        select(UserChildRelation).where(
            UserChildRelation.child_id == cur.ref_id,
            UserChildRelation.user_id == user_id,
        )
    )).scalar_one_or_none()
    if rel is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "未绑定该老人")

    conds = [AlertEvent.user_id == user_id]
    if status_filter:
        conds.append(AlertEvent.handling_status == status_filter)
    if level:
        conds.append(AlertEvent.alert_level == level)

    total = (await db.execute(select(func.count()).select_from(AlertEvent).where(*conds))).scalar() or 0
    rows = (await db.execute(
        select(AlertEvent).where(*conds).order_by(AlertEvent.alert_time.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    return R.ok(Page(
        total=int(total), page=page, page_size=page_size,
        items=[_alert_out(r) for r in rows],
    ).model_dump())


@router.get("/{alert_id}", response_model=R, summary="预警详情")
async def alert_detail(alert_id: int, cur: ChildRole, db: DB):
    a = await db.get(AlertEvent, alert_id)
    if a is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "预警不存在")
    rel = (await db.execute(
        select(UserChildRelation).where(
            UserChildRelation.child_id == cur.ref_id,
            UserChildRelation.user_id == a.user_id,
        )
    )).scalar_one_or_none()
    if rel is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "无权查看此预警")
    return R.ok(_alert_out(a))


@router.patch("/{alert_id}/handle", response_model=R, summary="处置预警")
async def handle_alert(
    alert_id: int,
    cur: ChildRole, db: DB,
    handling_status: str = Query(..., description="已确认/转医生/已忽略"),
    handle_remark: str = Query(None, description="处置备注"),
):
    a = await db.get(AlertEvent, alert_id)
    if a is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "预警不存在")
    rel = (await db.execute(
        select(UserChildRelation).where(
            UserChildRelation.child_id == cur.ref_id,
            UserChildRelation.user_id == a.user_id,
        )
    )).scalar_one_or_none()
    if rel is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "无权处置此预警")

    a.handling_status = handling_status
    a.handled_by = cur.ref_id
    a.handled_at = datetime.now(timezone.utc)
    if handle_remark:
        a.handle_remark = handle_remark

    return R.ok(_alert_out(a), msg="已处置")
