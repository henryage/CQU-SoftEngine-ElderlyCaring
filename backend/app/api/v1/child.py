"""子女端路由。

接口：
- POST   /child/bind                      绑定老人
- DELETE /child/unbind/{user_id}          解绑老人
- GET    /child/binded-users              我绑定的老人列表
- GET    /child/dashboard/{user_id}       健康看板
- GET    /child/messages/{user_id}        问答记录下钻
- GET    /child/settings/{user_id}        查看配置
- PUT    /child/settings/{user_id}        下发配置
- GET    /child/settings/{user_id}/changes 配置变更历史
"""
import logging
from datetime import datetime, timedelta, timezone, date

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select, func, and_, or_

from app.core.deps import DB, ChildRole
from app.models.user import User, ChildUser, UserChildRelation
from app.models.message import Message
from app.models.interaction import AlertEvent, SettingChange, UserSetting, MedicationReminder
from app.schemas.common import R, Page
from app.schemas.child import BindIn, BindedUserOut, DashboardOut, MessageItem, SettingsIn

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/child", tags=["child"])


# ── 辅助 ──────────────────────────────────────────

def _resolve_child_id(cur) -> int:
    """当前登录的子女 ID。"""
    if not cur.is_child:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "仅子女端可访问")
    return cur.ref_id


async def _check_bind(db, child_id: int, user_id: int):
    """验证绑定关系存在。"""
    rel = (await db.execute(
        select(UserChildRelation).where(
            UserChildRelation.child_id == child_id,
            UserChildRelation.user_id == user_id,
        )
    )).scalar_one_or_none()
    if rel is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "未绑定该老人")
    return rel


# ── 绑定 ──────────────────────────────────────────

@router.post("/bind", response_model=R, summary="绑定老人（验证码）")
async def bind(payload: BindIn, cur: ChildRole, db: DB):
    """子女用老人出示的 6 位验证码绑定。验证码 5 分钟有效。"""
    child_id = _resolve_child_id(cur)

    # 查验证码对应的老人
    user = (await db.execute(
        select(User).where(
            User.bind_code == payload.code,
            User.bind_code_expires_at > datetime.now(timezone.utc),
        )
    )).scalar_one_or_none()

    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "验证码无效或已过期")

    existing = (await db.execute(
        select(UserChildRelation).where(
            UserChildRelation.child_id == child_id,
            UserChildRelation.user_id == user.user_id,
        )
    )).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "已绑定该老人")

    # 绑定 + 清验证码（一次性使用）
    rel = UserChildRelation(
        child_id=child_id,
        user_id=user.user_id,
        relation=payload.relation,
    )
    user.bind_code = None
    user.bind_code_expires_at = None
    db.add(rel)
    return R.ok({"user_id": user.user_id, "nickname": user.nickname, "relation": payload.relation}, msg="绑定成功")


@router.delete("/unbind/{user_id}", response_model=R, summary="解绑老人")
async def unbind(user_id: int, cur: ChildRole, db: DB):
    child_id = _resolve_child_id(cur)
    rel = await _check_bind(db, child_id, user_id)
    await db.delete(rel)
    return R.ok(msg="已解绑")


# ── 绑定列表 ──────────────────────────────────────

@router.get("/binded-users", response_model=R, summary="我绑定的老人列表")
async def binded_users(cur: ChildRole, db: DB):
    child_id = _resolve_child_id(cur)
    rows = (await db.execute(
        select(UserChildRelation, User).join(User, UserChildRelation.user_id == User.user_id)
        .where(UserChildRelation.child_id == child_id)
    )).all()

    users: list[dict] = []
    for rel, user in rows:
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        pending = (await db.execute(
            select(func.count()).select_from(AlertEvent).where(
                AlertEvent.user_id == user.user_id,
                AlertEvent.handling_status == "待处理",
            )
        )).scalar() or 0
        today_qa = (await db.execute(
            select(func.count()).select_from(Message).where(
                Message.user_id == user.user_id,
                Message.created_at >= today_start,
            )
        )).scalar() or 0
        users.append(BindedUserOut(
            user_id=user.user_id,
            nickname=user.nickname,
            relation=rel.relation,
            is_online=user.online_status == "online",
            last_heartbeat_at=user.last_heartbeat_at.isoformat() if user.last_heartbeat_at else None,
            unread_alerts=int(pending),
            today_qa_count=int(today_qa),
        ).model_dump())
    return R.ok(users)


# ── 看板 ──────────────────────────────────────────

@router.get("/dashboard/{user_id}", response_model=R, summary="健康看板")
async def dashboard(user_id: int, cur: ChildRole, db: DB):
    child_id = _resolve_child_id(cur)
    await _check_bind(db, child_id, user_id)

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "老人不存在")

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    today_qa = (await db.execute(
        select(func.count()).select_from(Message).where(
            Message.user_id == user_id, Message.created_at >= today_start,
        )
    )).scalar() or 0
    pending = (await db.execute(
        select(func.count()).select_from(AlertEvent).where(
            AlertEvent.user_id == user_id, AlertEvent.handling_status == "待处理",
        )
    )).scalar() or 0
    active_reminders = (await db.execute(
        select(func.count()).select_from(MedicationReminder).where(
            MedicationReminder.user_id == user_id, MedicationReminder.active == 1,
        )
    )).scalar() or 0

    recent = (await db.execute(
        select(Message).where(Message.user_id == user_id)
        .order_by(Message.created_at.desc()).limit(3)
    )).scalars().all()

    health_tags: list[str] = []
    if pending:
        health_tags.append("有待处理预警")

    return R.ok(DashboardOut(
        user_id=user.user_id,
        nickname=user.nickname,
        is_online=user.online_status == "online",
        today_qa_count=int(today_qa),
        pending_alerts=int(pending),
        active_reminders=int(active_reminders),
        recent_messages=[{
            "msg_id": m.msg_id,
            "question": m.content_text,
            "answer": (m.answer_text or "")[:100],
            "time": m.created_at.isoformat() if m.created_at else None,
        } for m in recent],
        health_tags=health_tags,
    ).model_dump(mode="json"))


# ── 问答下钻 ──────────────────────────────────────

@router.get("/messages/{user_id}", response_model=R, summary="问答记录下钻")
async def messages(
    user_id: int, cur: ChildRole, db: DB,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None, description="模糊搜索问题或回答"),
    start_date: str | None = Query(None, description="YYYY-MM-DD"),
    end_date: str | None = Query(None, description="YYYY-MM-DD"),
):
    child_id = _resolve_child_id(cur)
    await _check_bind(db, child_id, user_id)

    conditions = [Message.user_id == user_id]
    if keyword:
        conditions.append(or_(
            Message.content_text.like(f"%{keyword}%"),
            Message.answer_text.like(f"%{keyword}%"),
        ))
    if start_date:
        conditions.append(Message.created_at >= datetime.fromisoformat(start_date))
    if end_date:
        conditions.append(Message.created_at < datetime.fromisoformat(end_date) + timedelta(days=1))

    total = (await db.execute(select(func.count()).select_from(Message).where(*conditions))).scalar() or 0
    rows = (await db.execute(
        select(Message).where(*conditions).order_by(Message.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    return R.ok(Page(
        total=int(total), page=page, page_size=page_size,
        items=[{
            "msg_id": m.msg_id, "input_type": m.input_type,
            "question": m.content_text, "answer": m.answer_text,
            "intercepted": bool(m.intercepted) if m.intercepted else False,
            "risk_tags": m.risk_tags,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        } for m in rows],
    ).model_dump(mode="json"))


# ── 适老化配置 ─────────────────────────────────────

@router.get("/settings/{user_id}", response_model=R, summary="查看配置")
async def get_settings(user_id: int, cur: ChildRole, db: DB):
    child_id = _resolve_child_id(cur)
    await _check_bind(db, child_id, user_id)

    rows = (await db.execute(
        select(UserSetting).where(UserSetting.user_id == user_id)
    )).scalars().all()

    cfg = {}
    for r in rows:
        cfg[r.setting_key] = r.setting_value

    return R.ok({
        "font_size": cfg.get("font_size", "normal"),
        "voice_enabled": cfg.get("voice_enabled", "true") == "true",
        "simplified_mode": cfg.get("simplified_mode", "false") == "true",
    } if cfg else {
        "font_size": "normal", "voice_enabled": True, "simplified_mode": False,
    })


@router.put("/settings/{user_id}", response_model=R, summary="下发配置")
async def update_settings(user_id: int, payload: SettingsIn, cur: ChildRole, db: DB):
    child_id = _resolve_child_id(cur)
    await _check_bind(db, child_id, user_id)

    settings_map = {
        "font_size": payload.font_size,
        "voice_enabled": str(payload.voice_enabled).lower(),
        "simplified_mode": str(payload.simplified_mode).lower(),
    }
    now = datetime.now(timezone.utc)

    for key, val in settings_map.items():
        existing = (await db.execute(
            select(UserSetting).where(UserSetting.user_id == user_id, UserSetting.setting_key == key)
        )).scalar_one_or_none()
        if existing:
            if existing.setting_value != val:
                db.add(SettingChange(
                    child_id=child_id, user_id=user_id,
                    setting_key=key, old_value=existing.setting_value,
                    new_value=val, change_time=now,
                ))
                existing.setting_value = val
                existing.synced_at = now
        else:
            db.add(UserSetting(user_id=user_id, setting_key=key, setting_value=val, synced_at=now))
            db.add(SettingChange(
                child_id=child_id, user_id=user_id,
                setting_key=key, old_value=None, new_value=val, change_time=now,
            ))

    return R.ok(settings_map, msg="配置已更新")


@router.get("/settings/{user_id}/changes", response_model=R, summary="配置变更历史")
async def settings_changes(user_id: int, cur: ChildRole, db: DB):
    child_id = _resolve_child_id(cur)
    await _check_bind(db, child_id, user_id)

    rows = (await db.execute(
        select(SettingChange).where(SettingChange.user_id == user_id)
        .order_by(SettingChange.change_time.desc()).limit(50)
    )).scalars().all()

    return R.ok([{
        "change_id": c.change_id,
        "setting_key": c.setting_key,
        "old_value": c.old_value,
        "new_value": c.new_value,
        "change_time": c.change_time.isoformat(),
        "changed_by": c.child_id,
    } for c in rows])
