"""鉴权路由。

覆盖：微信小程序登录、手机号绑定、token 刷新、登出、管理员登录、
订阅消息授权上报、老人端心跳上报。

统一响应格式：`R`（{code, msg, data}）
鉴权方式：除 wx-login/refresh/admin-login/dev-create-admin 外，均需 `Authorization: Bearer <token>`
"""
import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from app.core.config import settings
from app.core.deps import DB, AnyRole, ElderUser
from app.core.security import (
    create_access_token, create_refresh_token, decode_token,
    hash_password, verify_password,
)
from app.core.wx import code2session
from app.models.user import WxAccount, User, ChildUser, AdminUser, UserChildRelation
from app.models.interaction import SubscribeGrant, AlertEvent
from app.schemas.auth import (
    WxLoginIn, BindPhoneIn, TokenOut, RefreshIn,
    AdminLoginIn, SubscribeGrantIn, HeartbeatOut,
)
from app.schemas.common import R


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


# 通用响应码说明（所有需要鉴权的接口复用）
AUTH_RESPONSES = {
    401: {"description": "未认证 / token 无效或过期", "content": {"application/json": {"examples": {
        "no_token": {"summary": "缺少 token", "value": {"detail": "缺少认证令牌"}},
        "invalid_token": {"summary": "token 无效", "value": {"detail": "令牌无效或已过期"}},
    }}}},
    403: {"description": "权限不足（角色不允许）", "content": {"application/json": {"examples": {
        "forbidden": {"summary": "权限不足", "value": {"detail": "权限不足"}},
    }}}},
}


@router.post(
    "/wx-login",
    response_model=R,
    summary="小程序登录",
    description="""
小程序登录入口（老人端 / 子女端共用）。

**流程**：
1. 小程序调用 `wx.login()` 拿到临时 code
2. 调用本接口提交 code + user_type
3. 后端用 code 调微信 `code2session` 换 openid + session_key
4. 查/建 `wx_account` + 自动建老人/子女记录
5. 签发 JWT（Access 30min + Refresh 7d）

**dev 模式**：code 可传任意字符串，后端直接当 mock openid 用，不调微信。
**prod 模式**：code 是 `wx.login()` 返回的临时凭证，5 分钟有效。

**首次登录自动建号**：
- user_type=user → 自动建 User 记录，昵称默认"老人{account_id}"
- user_type=child → 自动建 ChildUser 记录，手机号占位（需后续调 /bind-phone）
""".strip(),
    response_description="登录成功，返回 token 与用户信息",
    responses={
        200: {
            "description": "登录成功",
            "content": {"application/json": {"example": {
                "code": 0, "msg": "ok",
                "data": {
                    "token": "eyJhbGciOi...",
                    "refresh_token": "eyJhbGciOi...",
                    "token_type": "Bearer",
                    "user_type": "user",
                    "ref_id": 6,
                    "nickname": "老人6",
                },
            }}},
        },
        422: {"description": "参数校验失败（code 缺失 / user_type 非法）"},
    },
)
async def wx_login(payload: WxLoginIn, db: DB):
    session_info = await code2session(payload.code)
    openid = session_info["openid"]
    session_key = session_info.get("session_key")

    acc = (await db.execute(select(WxAccount).where(WxAccount.openid == openid))).scalar_one_or_none()
    if acc is None:
        acc = WxAccount(
            openid=openid,
            unionid=session_info.get("unionid"),
            session_key=session_key,
            user_type=payload.user_type,
            ref_user_id=None,
            last_login_at=datetime.now(timezone.utc),
        )
        db.add(acc)
        await db.flush()

        if payload.user_type == "user":
            u = User(nickname=f"老人{acc.account_id}", wx_account_id=acc.account_id)
            db.add(u)
            await db.flush()
            acc.ref_user_id = u.user_id
            nickname = u.nickname
            ref_id = u.user_id
        else:
            ch = ChildUser(name=f"子女{acc.account_id}", phone=f"dev_{openid}", wx_account_id=acc.account_id)
            db.add(ch)
            await db.flush()
            acc.ref_user_id = ch.child_id
            nickname = ch.name
            ref_id = ch.child_id
    else:
        acc.session_key = session_key
        acc.last_login_at = datetime.now(timezone.utc)
        nickname = None
        ref_id = acc.ref_user_id
        if acc.user_type == "user" and ref_id:
            u = await db.get(User, ref_id)
            nickname = u.nickname if u else None
        elif acc.user_type == "child" and ref_id:
            ch = await db.get(ChildUser, ref_id)
            nickname = ch.name if ch else None

    token = create_access_token(
        subject=str(acc.account_id),
        extra={"user_type": acc.user_type, "ref_id": acc.ref_user_id, "openid": openid},
    )
    refresh = create_refresh_token(str(acc.account_id))

    return R.ok(TokenOut(
        token=token,
        refresh_token=refresh,
        user_type=acc.user_type,
        ref_id=ref_id,
        nickname=nickname,
    ).model_dump())


@router.get(
    "/me",
    response_model=R,
    summary="当前用户信息",
    description="返回当前登录用户的 ref_id、昵称、角色。老人可在此看到自己的 user_id 告知子女。",
)
async def my_info(cur: AnyRole):
    return R.ok({
        "ref_id": cur.ref_id,
        "user_type": cur.user_type,
        "is_child": cur.is_child,
        "is_elder": cur.is_elder,
        "is_admin": cur.is_admin,
    })


@router.post(
    "/generate-bind-code",
    response_model=R,
    summary="生成绑定验证码（老人端）",
    description="""
老人端调用，生成 6 位数字验证码，5 分钟有效。
子女端凭此验证码进行绑定（替代直接输入 user_id）。
""".strip(),
)
async def generate_bind_code(cur: ElderUser, db: DB):
    import random
    user = await db.get(User, cur.ref_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "用户不存在")

    code = str(random.randint(100000, 999999))
    user.bind_code = code
    user.bind_code_expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    return R.ok({
        "code": code,
        "expires_in_seconds": 300,
        "user_id": user.user_id,
    }, msg=f"验证码 {code}，5 分钟内有效")


@router.put(
    "/nickname",
    response_model=R,
    summary="修改昵称（老人端）",
    description="老人修改自己的昵称，子女端可同步看到。",
)
async def update_nickname(nickname: str = Query(..., min_length=1, max_length=64), cur: ElderUser = None, db: DB = None):
    user = await db.get(User, cur.ref_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "用户不存在")
    old = user.nickname
    user.nickname = nickname
    return R.ok({"user_id": user.user_id, "old": old, "new": nickname}, msg="昵称已更新")


@router.post(
    "/bind-phone",
    response_model=R,
    summary="绑定/更新手机号（子女端）",
    description="""
子女端绑定或更新手机号。

**权限**：仅 `user_type=child` 的 token 可调。
**dev 模式**：直接传手机号字符串，不走微信 getPhoneNumber 解密。
**prod 模式**：应传微信 getPhoneNumber 回调里的加密数据，由后端用 session_key 解密（当前简化版本直接收手机号）。
""".strip(),
    response_description="绑定成功，返回新手机号",
    responses={
        200: {"description": "绑定成功", "content": {"application/json": {"example": {"code": 0, "msg": "ok", "data": {"phone": "13800138000"}}}}},
        401: {"description": "未认证"},
        403: {"description": "非子女端 token", "content": {"application/json": {"example": {"detail": "仅子女端可绑定手机号"}}}},
        404: {"description": "子女账号不存在", "content": {"application/json": {"example": {"detail": "子女账号不存在"}}}},
        422: {"description": "参数校验失败（手机号非 11 位等）"},
    },
)
async def bind_phone(payload: BindPhoneIn, cur: AnyRole, db: DB):
    if cur.user_type != "child":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "仅子女端可绑定手机号")
    ch = await db.get(ChildUser, cur.ref_id)
    if ch is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "子女账号不存在")
    ch.phone = payload.phone
    if payload.name:
        ch.name = payload.name
    if payload.relation:
        ch.relation = payload.relation
    return R.ok({"phone": ch.phone})


@router.post(
    "/refresh",
    response_model=R,
    summary="刷新 Access Token",
    description="""
用 refresh_token 换取新的 access_token。

**规则**：
- refresh_token 有效期 7 天
- access_token 有效期 30 分钟
- refresh_token 不能用来访问业务接口，只能调本接口
- 旧 refresh_token 不做失效（如需严格单次使用，可在 refresh_token 表加状态字段）
""".strip(),
    response_description="刷新成功，返回新 token",
    responses={
        200: {"description": "刷新成功", "content": {"application/json": {"example": {"code": 0, "msg": "ok", "data": {"token": "eyJhbGciOi...", "token_type": "Bearer"}}}}},
        401: {"description": "refresh_token 无效或过期", "content": {"application/json": {"example": {"detail": "refresh token 无效"}}}},
    },
)
async def refresh_token(payload: RefreshIn, db: DB):
    data = decode_token(payload.refresh_token)
    if data is None or data.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "refresh token 无效")
    account_id = int(data.get("sub"))
    acc = await db.get(WxAccount, account_id)
    if acc is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "账号不存在")
    token = create_access_token(
        subject=str(account_id),
        extra={"user_type": acc.user_type, "ref_id": acc.ref_user_id, "openid": acc.openid},
    )
    return R.ok({"token": token, "token_type": "Bearer"})


@router.post(
    "/logout",
    response_model=R,
    summary="登出",
    description="""
登出当前会话。

**说明**：JWT 是无状态的，后端不维护 token 黑名单，前端清除本地 token 即可。
如需严格登出（防止 token 泄露后被利用），可后续加 Redis token 黑名单。
""".strip(),
    response_description="登出成功",
    responses={
        200: {"description": "登出成功", "content": {"application/json": {"example": {"code": 0, "msg": "已登出", "data": None}}}},
        401: {"description": "未认证"},
    },
)
async def logout(cur: AnyRole):
    return R.ok(msg="已登出")


@router.post(
    "/admin/login",
    response_model=R,
    summary="管理员登录（Web 控制台）",
    description="""
管理端 Web 控制台账号密码登录。

**账号来源**：dev 模式调 `GET /auth/dev/create-admin` 一键创建 admin/admin；
prod 模式由超级管理员在数据库或后台脚本创建。

**返回**：与小程序登录一致的 token 结构，user_type=admin。
""".strip(),
    response_description="登录成功，返回管理员 token",
    responses={
        200: {"description": "登录成功", "content": {"application/json": {"example": {
            "code": 0, "msg": "ok",
            "data": {"token": "eyJhbGciOi...", "refresh_token": "eyJhbGciOi...", "token_type": "Bearer", "user_type": "admin", "ref_id": 1, "nickname": "admin"},
        }}}},
        401: {"description": "用户名或密码错误", "content": {"application/json": {"example": {"detail": "用户名或密码错误"}}}},
        422: {"description": "参数校验失败"},
    },
)
async def admin_login(payload: AdminLoginIn, db: DB):
    admin = (await db.execute(select(AdminUser).where(AdminUser.username == payload.username))).scalar_one_or_none()
    if admin is None or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户名或密码错误")
    token = create_access_token(
        subject=str(admin.admin_id),
        extra={"user_type": "admin", "ref_id": admin.admin_id},
    )
    refresh = create_refresh_token(str(admin.admin_id))
    return R.ok(TokenOut(
        token=token, refresh_token=refresh, user_type="admin", ref_id=admin.admin_id, nickname=admin.username,
    ).model_dump())


@router.post(
    "/subscribe/grant",
    response_model=R,
    summary="上报订阅消息授权结果",
    description="""
小程序调用 `wx.requestSubscribeMessage` 后，将用户授权结果上报后端。

**作用**：
- 后端记录 `subscribe_grant` 表，跟踪每个模板的剩余可推送次数
- 一次性模板：每次 accept = 1 次推送配额，用完需重新授权
- 配额不足时，定时任务推送会降级为短信通知子女

**权限**：老人端 / 子女端均可调（上报自己的授权）。
""".strip(),
    response_description="上报成功",
    responses={
        200: {"description": "上报成功", "content": {"application/json": {"example": {"code": 0, "msg": "ok", "data": {"granted": True}}}}},
        401: {"description": "未认证"},
        422: {"description": "参数校验失败"},
    },
)
async def report_subscribe_grant(payload: SubscribeGrantIn, cur: AnyRole, db: DB):
    g = SubscribeGrant(
        account_id=cur.account_id,
        template_id=payload.template_id,
        grant_status=payload.grant_status,
        granted_at=datetime.now(timezone.utc),
        expire_count=1 if payload.grant_status == "accept" else 0,
    )
    db.add(g)
    return R.ok({"granted": payload.grant_status == "accept"})


@router.get(
    "/dev/create-admin",
    response_model=R,
    summary="[DEV] 一键创建测试管理员",
    description="""
**仅 dev 模式可用**。一键创建测试管理员账号 `admin` / `admin`。

**用途**：本地测试时快速拿到管理员 token 调管理端接口。
**生产环境**：此接口返回 403，管理员需通过数据库或后台脚本创建。
""".strip(),
    response_description="创建结果（已存在则返回提示）",
    responses={
        200: {"description": "创建成功或已存在", "content": {"application/json": {"examples": {
            "created": {"summary": "新建成功", "value": {"code": 0, "msg": "ok", "data": {"msg": "管理员已创建", "username": "admin", "password": "admin", "admin_id": 1}}},
            "exists": {"summary": "已存在", "value": {"code": 0, "msg": "ok", "data": {"msg": "管理员已存在", "username": "admin"}}},
        }}}},
        403: {"description": "非 dev 模式", "content": {"application/json": {"example": {"detail": "仅 dev 模式可用"}}}},
    },
)
async def dev_create_admin(db: DB):
    if not settings.is_dev:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "仅 dev 模式可用")
    admin = (await db.execute(select(AdminUser).where(AdminUser.username == "admin"))).scalar_one_or_none()
    if admin is None:
        admin = AdminUser(username="admin", password_hash=hash_password("admin"), role="SUPER")
        db.add(admin)
        await db.flush()
        return R.ok({"msg": "管理员已创建", "username": "admin", "password": "admin", "admin_id": admin.admin_id})
    return R.ok({"msg": "管理员已存在", "username": "admin"})


@router.post(
    "/heartbeat",
    response_model=R,
    summary="老人端心跳上报",
    description="""
老人端小程序前台运行时**每 30 秒**调用一次，用于网络断开自动预警。

**机制**：
1. 更新 `user.last_heartbeat_at` 与 `online_status=online`
2. 若之前是 offline 状态，则发"网络恢复"预警通知子女端
3. 后端定时任务（每 60 秒扫描）检查超 180 秒未心跳的老人，判定离线并发"网络断开"预警

**权限**：仅 `user_type=user`（老人端）的 token 可调，子女端/管理端调返回 403。

**触发场景**：
- 老人小程序被杀后台 / 手机断网 / 手机关机 → 心跳中断 → 180 秒后自动告警子女
- 老人重新打开小程序 → 心跳恢复 → 自动发"网络恢复"通知
""".strip(),
    response_description="心跳成功，返回当前时间与在线状态",
    responses={
        200: {"description": "心跳成功", "content": {"application/json": {"example": {"code": 0, "msg": "ok", "data": {"heartbeat_at": "2026-06-27T03:43:50.970526+00:00", "online_status": "online"}}}}},
        401: {"description": "未认证"},
        403: {"description": "非老人端 token", "content": {"application/json": {"example": {"detail": "权限不足"}}}},
        404: {"description": "老人账号不存在", "content": {"application/json": {"example": {"detail": "老人账号不存在"}}}},
    },
)
async def heartbeat(cur: ElderUser, db: DB):
    u = await db.get(User, cur.ref_id)
    if u is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "老人账号不存在")

    now = datetime.now(timezone.utc)
    was_offline = u.online_status == "offline"
    u.last_heartbeat_at = now
    u.online_status = "online"

    if was_offline:
        await _create_network_alert(
            db, user_id=u.user_id, alert_type="网络恢复",
            alert_level="提醒", detail=f"老人 {u.nickname} 网络已恢复，小程序重新连接",
        )
        logger.info("老人 %s(%s) 网络恢复", u.user_id, u.nickname)

    return R.ok(HeartbeatOut(heartbeat_at=now, online_status="online").model_dump())


async def _create_network_alert(
    db, user_id: int, alert_type: str, alert_level: str, detail: str
):
    """写网络类预警事件，并尝试推送子女端订阅消息（dev 模式仅日志）。"""
    alert = AlertEvent(
        user_id=user_id,
        alert_type=alert_type,
        alert_level=alert_level,
        trigger_source="rule",
        alert_time=datetime.now(timezone.utc),
        detail=detail,
        handling_status="已确认" if alert_type == "网络恢复" else "待处理",
        notify_channels=[{"channel": "subscribe", "status": "pending"}],
    )
    db.add(alert)
    await db.flush()

    relations = (await db.execute(
        select(UserChildRelation).where(UserChildRelation.user_id == user_id)
    )).scalars().all()

    from app.core.wx import send_subscribe_message
    template_code = "alert.warn" if alert_type == "网络断开" else "alert.handled"
    for rel in relations:
        child = await db.get(ChildUser, rel.child_id)
        if child and child.wx_account_id:
            acc = await db.get(WxAccount, child.wx_account_id)
            if acc:
                try:
                    await send_subscribe_message(
                        openid=acc.openid,
                        template_id=f"tpl_{template_code.replace('.', '_')}",
                        data={
                            "thing1": {"value": f"老人{user_id}"},
                            "thing2": {"value": alert_type},
                            "time3": {"value": alert.alert_time.strftime("%Y-%m-%d %H:%M")},
                            "thing4": {"value": detail[:20]},
                        },
                    )
                except Exception as e:
                    logger.warning("推送网络预警给子女 %s 失败: %s", rel.child_id, e)
