"""管理端路由。

接口：
- GET  /admin/users               老人用户列表
- GET  /admin/children             子女账号列表
- GET  /admin/audit                审计日志查询
- GET  /admin/audit/export         审计导出（csv/json）
- GET  /admin/subscribe/templates  订阅模板列表
- POST /admin/subscribe/templates  新增订阅模板
"""
from datetime import datetime, timezone
import json, csv, io
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func

from app.core.deps import DB, AdminRole
from app.models.user import User, ChildUser, UserChildRelation
from app.models.config import SubscribeTemplate, AuditLog
from app.schemas.common import R

router = APIRouter(prefix="/admin", tags=["admin"])


# ── 老人列表 ──────────────────────────────────────

@router.get("/users", response_model=R, summary="老人用户列表")
async def list_users(
    cur: AdminRole, db: DB,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    keyword: str = Query(None, description="搜索昵称"),
):
    conds = []
    if keyword:
        conds.append(User.nickname.like(f"%{keyword}%"))
    total = (await db.execute(select(func.count()).select_from(User).where(*conds))).scalar() or 0
    rows = (await db.execute(
        select(User).where(*conds).order_by(User.user_id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    return R.ok({
        "total": int(total), "page": page, "page_size": page_size,
        "items": [{"user_id": u.user_id, "nickname": u.nickname, "online_status": u.online_status,
                    "last_heartbeat_at": u.last_heartbeat_at.isoformat() if u.last_heartbeat_at else None,
                    "status": u.status, "created_at": u.created_at.isoformat() if u.created_at else None}
                   for u in rows],
    })


# ── 子女列表 ──────────────────────────────────────

@router.get("/children", response_model=R, summary="子女账号列表")
async def list_children(
    cur: AdminRole, db: DB,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    total = (await db.execute(select(func.count()).select_from(ChildUser))).scalar() or 0
    rows = (await db.execute(
        select(ChildUser).order_by(ChildUser.child_id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    return R.ok({
        "total": int(total), "page": page, "page_size": page_size,
        "items": [{"child_id": c.child_id, "name": c.name, "phone": c.phone,
                    "created_at": c.created_at.isoformat() if c.created_at else None}
                   for c in rows],
    })


# ── 绑定关系 ──────────────────────────────────────

@router.get("/relations", response_model=R, summary="绑定关系查询")
async def relations(
    cur: AdminRole, db: DB,
    user_id: int = Query(None, description="按老人ID查 → 返回绑定子女"),
    child_id: int = Query(None, description="按子女ID查 → 返回绑定老人"),
):
    if user_id is None and child_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "请传 user_id 或 child_id")

    conds = []
    if user_id:
        conds.append(UserChildRelation.user_id == user_id)
    if child_id:
        conds.append(UserChildRelation.child_id == child_id)

    rows = (await db.execute(
        select(UserChildRelation, User, ChildUser)
        .join(User, UserChildRelation.user_id == User.user_id)
        .join(ChildUser, UserChildRelation.child_id == ChildUser.child_id)
        .where(*conds)
    )).all()

    results = []
    for rel, u, ch in rows:
        results.append({
            "relation_id": rel.relation_id,
            "elderly": {"user_id": u.user_id, "nickname": u.nickname, "online_status": u.online_status},
            "child": {"child_id": ch.child_id, "name": ch.name, "phone": ch.phone},
            "relation": rel.relation,
            "is_primary": bool(rel.is_primary),
            "created_at": rel.created_at.isoformat() if rel.created_at else None,
        })

    return R.ok({"count": len(results), "items": results})


# ── 审计日志 ──────────────────────────────────────

@router.get("/audit", response_model=R, summary="审计日志查询")
async def audit_log(
    cur: AdminRole, db: DB,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    operation: str = Query(None),
    operator_type: str = Query(None, description="user/child/admin/system"),
):
    conds = []
    if operation:
        conds.append(AuditLog.operation == operation)
    if operator_type:
        conds.append(AuditLog.operator_type == operator_type)
    total = (await db.execute(select(func.count()).select_from(AuditLog).where(*conds))).scalar() or 0
    rows = (await db.execute(
        select(AuditLog).where(*conds).order_by(AuditLog.audit_id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    return R.ok({
        "total": int(total), "page": page, "page_size": page_size,
        "items": [{"audit_id": a.audit_id, "operator_type": a.operator_type,
                    "operator_id": a.operator_id, "operation": a.operation,
                    "target_type": a.target_type, "target_id": a.target_id,
                    "detail": a.detail, "ip": a.ip_address,
                    "created_at": a.created_at.isoformat() if a.created_at else None}
                   for a in rows],
    })


@router.get("/audit/export", response_class=StreamingResponse, summary="审计日志导出")
async def audit_export(
    cur: AdminRole, db: DB,
    format: str = Query("json", description="json/csv"),
):
    rows = (await db.execute(
        select(AuditLog).order_by(AuditLog.audit_id.desc()).limit(10000)
    )).scalars().all()
    items = [{"audit_id": a.audit_id, "operator_type": a.operator_type,
              "operator_id": a.operator_id, "operation": a.operation,
              "target_type": a.target_type, "target_id": a.target_id,
              "detail": a.detail, "ip": a.ip_address,
              "created_at": a.created_at.isoformat() if a.created_at else None}
             for a in rows]

    if format == "csv":
        output = io.StringIO()
        if items:
            w = csv.DictWriter(output, fieldnames=items[0].keys())
            w.writeheader(); w.writerows(items)
        return StreamingResponse(iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=audit_export.csv"})
    else:
        return StreamingResponse(iter([json.dumps(items, ensure_ascii=False, indent=2)]),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=audit_export.json"})


# ── 订阅模板 ──────────────────────────────────────

@router.get("/subscribe/templates", response_model=R, summary="订阅模板列表")
async def list_templates(cur: AdminRole, db: DB):
    rows = (await db.execute(select(SubscribeTemplate))).scalars().all()
    return R.ok([{"template_id": t.template_id, "code": t.code, "name": t.name,
                   "scene": t.scene, "status": t.status} for t in rows])


@router.post("/subscribe/templates", response_model=R, summary="新增订阅模板", status_code=201)
async def create_template(
    cur: AdminRole, db: DB,
    template_id: str = Query(..., description="微信模板ID"),
    code: str = Query(..., description="业务标识,如 medication.remind"),
    name: str = Query(...),
    scene: str = Query(None),
):
    existing = (await db.execute(
        select(SubscribeTemplate).where(SubscribeTemplate.template_id == template_id)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "模板已存在")
    t = SubscribeTemplate(template_id=template_id, code=code, name=name, scene=scene)
    db.add(t)
    return R.ok({"template_id": template_id, "code": code}, msg="已添加")
