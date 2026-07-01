"""通信路由（子女端 ↔ 老人端）。

接口：
- POST /comm/text              发送文字留言
- POST /comm/voice             上传语音消息
- POST /comm/greeting/schedule 定时问候配置
- GET  /comm/history           通信历史
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select, func, or_

from app.core.deps import DB, ChildRole
from app.models.user import UserChildRelation
from app.models.interaction import CommunicationLog, GreetingSchedule
from app.schemas.common import R

router = APIRouter(prefix="/comm", tags=["comm"])


async def _check_bind(db, child_id: int, user_id: int):
    rel = (await db.execute(
        select(UserChildRelation).where(
            UserChildRelation.child_id == child_id,
            UserChildRelation.user_id == user_id,
        )
    )).scalar_one_or_none()
    if rel is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "未绑定该老人")


# ── 文字留言 ──────────────────────────────────────

@router.post("/text", response_model=R, summary="发送文字留言")
async def send_text(
    cur: ChildRole, db: DB,
    user_id: int = Query(..., description="老人ID"),
    content: str = Query(..., description="留言内容"),
):
    await _check_bind(db, cur.ref_id, user_id)
    log = CommunicationLog(
        child_id=cur.ref_id, user_id=user_id,
        comm_type="text", direction="child_to_user",
        content=content, comm_time=datetime.now(timezone.utc),
    )
    db.add(log)
    return R.ok({"comm_id": log.comm_id, "content": content}, msg="留言已发送")


# ── 语音消息 ──────────────────────────────────────

@router.post("/voice", response_model=R, summary="发送语音消息")
async def send_voice(
    cur: ChildRole, db: DB,
    user_id: int = Query(..., description="老人ID"),
    content: str = Query(None, description="语音 ASR 文本（可选）"),
    duration_sec: int = Query(0, description="语音时长（秒）"),
):
    await _check_bind(db, cur.ref_id, user_id)
    log = CommunicationLog(
        child_id=cur.ref_id, user_id=user_id,
        comm_type="voice", direction="child_to_user",
        content=content, duration_sec=duration_sec,
        comm_time=datetime.now(timezone.utc),
    )
    db.add(log)
    return R.ok({"comm_id": log.comm_id, "duration_sec": duration_sec}, msg="语音已发送")


# ── 通信历史 ──────────────────────────────────────

@router.get("/history", response_model=R, summary="通信历史")
async def history(
    cur: ChildRole, db: DB,
    user_id: int = Query(..., description="老人ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    await _check_bind(db, cur.ref_id, user_id)
    total = (await db.execute(
        select(func.count()).select_from(CommunicationLog).where(
            CommunicationLog.child_id == cur.ref_id,
            CommunicationLog.user_id == user_id,
        )
    )).scalar() or 0
    rows = (await db.execute(
        select(CommunicationLog).where(
            CommunicationLog.child_id == cur.ref_id,
            CommunicationLog.user_id == user_id,
        ).order_by(CommunicationLog.comm_time.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    return R.ok({
        "total": int(total), "page": page, "page_size": page_size,
        "items": [{"comm_id": c.comm_id, "comm_type": c.comm_type, "direction": c.direction,
                    "content": c.content, "duration_sec": c.duration_sec,
                    "comm_time": c.comm_time.isoformat()}
                   for c in rows],
    })


# ── 定时问候 ──────────────────────────────────────

@router.post("/greeting/schedule", response_model=R, summary="定时问候配置")
async def greeting_schedule(
    cur: ChildRole, db: DB,
    user_id: int = Query(..., description="老人ID"),
    content: str = Query(..., description="问候语"),
    cron_expr: str = Query(..., description="Cron 表达式，如 0 8 * * * （每天8点）"),
    greeting_id: int = Query(None, description="修改时传已有ID"),
):
    await _check_bind(db, cur.ref_id, user_id)

    if greeting_id:
        g = await db.get(GreetingSchedule, greeting_id)
        if g is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "问候配置不存在")
        if g.child_id != cur.ref_id or g.user_id != user_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "无权修改")
        g.content = content
        g.cron_expr = cron_expr
        return R.ok({"greeting_id": g.greeting_id}, msg="已更新")
    else:
        g = GreetingSchedule(
            child_id=cur.ref_id, user_id=user_id,
            content=content, cron_expr=cron_expr,
        )
        db.add(g)
        return R.ok({"greeting_id": g.greeting_id, "content": content}, msg="已创建")


@router.get("/greeting/schedule", response_model=R, summary="查询定时问候")
async def list_greetings(
    cur: ChildRole, db: DB,
    user_id: int = Query(..., description="老人ID"),
):
    await _check_bind(db, cur.ref_id, user_id)
    rows = (await db.execute(
        select(GreetingSchedule).where(
            GreetingSchedule.child_id == cur.ref_id,
            GreetingSchedule.user_id == user_id,
        )
    )).scalars().all()
    return R.ok([{"greeting_id": g.greeting_id, "content": g.content,
                   "cron_expr": g.cron_expr, "created_at": g.created_at.isoformat() if g.created_at else None}
                  for g in rows])
