"""用药提醒路由。

老人端接口：
- GET /reminder/medication  查看自己的用药提醒

子女端 CRUD 后续补充。
"""
from fastapi import APIRouter
from sqlalchemy import select

from app.core.deps import DB, ElderUser
from app.models.interaction import MedicationReminder
from app.schemas.common import R


router = APIRouter(prefix="/reminder", tags=["reminder"])


@router.get(
    "/medication",
    response_model=R,
    summary="查看用药提醒（老人端）",
    description="""
老人端查看自己的用药提醒列表，**仅老人端可调**。

只返回 `active=1` 的提醒，按提醒时间排序。
""".strip(),
    response_description="用药提醒列表",
    responses={
        200: {"description": "查询成功", "content": {"application/json": {"example": {
            "code": 0, "msg": "ok",
            "data": [
                {"reminder_id": 1, "drug_name": "硝苯地平", "dosage": "1片", "remind_time": "08:00"},
                {"reminder_id": 2, "drug_name": "阿司匹林", "dosage": "1片", "remind_time": "12:00"},
            ],
        }}}},
        401: {"description": "未认证"},
        403: {"description": "非老人端 token"},
    },
)
async def my_medications(cur: ElderUser, db: DB):
    stmt = (
        select(MedicationReminder)
        .where(
            MedicationReminder.user_id == cur.ref_id,
            MedicationReminder.active == 1,
        )
        .order_by(MedicationReminder.remind_time)
    )
    items = (await db.execute(stmt)).scalars().all()

    return R.ok([{
        "reminder_id": r.reminder_id,
        "drug_name": r.drug_name,
        "dosage": r.dosage,
        "remind_time": r.remind_time,
    } for r in items])
