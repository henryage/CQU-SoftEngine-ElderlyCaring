"""用药提醒路由。

老人端：GET  /reminder/medication  查看自己的用药提醒
子女端：GET  /reminder/medication/list?user_id=6  查看老人的用药列表
        POST /reminder/medication                 新增
        PUT  /reminder/medication/{id}            修改
        DELETE /reminder/medication/{id}          删除
"""
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.core.deps import DB, ElderUser, ChildRole
from app.models.user import UserChildRelation
from app.models.interaction import MedicationReminder
from app.schemas.common import R


router = APIRouter(prefix="/reminder", tags=["reminder"])


# ── 辅助 ──────────────────────────────────────────

async def _check_bind(db, child_id: int, user_id: int):
    rel = (await db.execute(
        select(UserChildRelation).where(
            UserChildRelation.child_id == child_id,
            UserChildRelation.user_id == user_id,
        )
    )).scalar_one_or_none()
    if rel is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "未绑定该老人")


def _reminder_out(r: MedicationReminder) -> dict:
    return {
        "reminder_id": r.reminder_id,
        "user_id": r.user_id,
        "drug_name": r.drug_name,
        "dosage": r.dosage,
        "remind_time": r.remind_time,
        "active": r.active,
    }


# ── 老人端：查看自己的 ──────────────────────────

@router.get("/medication", response_model=R, summary="查看用药提醒（老人端）")
async def my_medications(cur: ElderUser, db: DB):
    stmt = (
        select(MedicationReminder)
        .where(MedicationReminder.user_id == cur.ref_id, MedicationReminder.active == 1)
        .order_by(MedicationReminder.remind_time)
    )
    items = (await db.execute(stmt)).scalars().all()
    return R.ok([_reminder_out(r) for r in items])


# ── 子女端：CRUD ──────────────────────────────────

@router.get("/medication/list", response_model=R, summary="查看老人的用药列表（子女端）")
async def list_medications(
    user_id: int = Query(..., description="老人ID"),
    cur: ChildRole = None, db: DB = None,
):
    await _check_bind(db, cur.ref_id, user_id)
    stmt = (
        select(MedicationReminder)
        .where(MedicationReminder.user_id == user_id)
        .order_by(MedicationReminder.remind_time)
    )
    items = (await db.execute(stmt)).scalars().all()
    return R.ok([_reminder_out(r) for r in items])


@router.post("/medication", response_model=R, summary="新增用药提醒（子女端）", status_code=201)
async def create_medication(
    drug_name: str = Query(..., description="药品名称"),
    remind_time: str = Query(..., description="提醒时间 HH:MM"),
    user_id: int = Query(..., description="老人ID"),
    dosage: str = Query(None, description="每次剂量"),
    cur: ChildRole = None, db: DB = None,
):
    await _check_bind(db, cur.ref_id, user_id)
    r = MedicationReminder(
        user_id=user_id, drug_name=drug_name, dosage=dosage,
        remind_time=remind_time, active=1,
    )
    db.add(r)
    return R.ok(_reminder_out(r), msg="已添加")


@router.put("/medication/{reminder_id}", response_model=R, summary="修改用药提醒（子女端）")
async def update_medication(
    reminder_id: int,
    drug_name: str = Query(None, description="药品名称"),
    remind_time: str = Query(None, description="提醒时间 HH:MM"),
    dosage: str = Query(None, description="每次剂量"),
    active: int = Query(None, ge=0, le=1, description="1启用 0停用"),
    cur: ChildRole = None, db: DB = None,
):
    r = await db.get(MedicationReminder, reminder_id)
    if r is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "提醒不存在")
    await _check_bind(db, cur.ref_id, r.user_id)

    if drug_name is not None: r.drug_name = drug_name
    if remind_time is not None: r.remind_time = remind_time
    if dosage is not None: r.dosage = dosage
    if active is not None: r.active = active
    return R.ok(_reminder_out(r), msg="已更新")


@router.delete("/medication/{reminder_id}", response_model=R, summary="删除用药提醒（子女端）")
async def delete_medication(reminder_id: int, cur: ChildRole = None, db: DB = None):
    r = await db.get(MedicationReminder, reminder_id)
    if r is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "提醒不存在")
    await _check_bind(db, cur.ref_id, r.user_id)
    await db.delete(r)
    return R.ok(msg="已删除")
