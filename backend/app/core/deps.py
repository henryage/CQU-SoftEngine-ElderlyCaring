"""FastAPI 依赖：当前登录用户、角色校验、DB 注入。"""
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User, ChildUser, AdminUser, WxAccount


bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser:
    """统一的"当前用户"上下文。"""

    def __init__(
        self,
        account_id: int,
        user_type: str,  # user / child / admin
        ref_id: int | None,
        openid: str | None = None,
    ):
        self.account_id = account_id
        self.user_type = user_type
        self.ref_id = ref_id
        self.openid = openid

    @property
    def is_elder(self) -> bool:
        return self.user_type == "user"

    @property
    def is_child(self) -> bool:
        return self.user_type == "child"

    @property
    def is_admin(self) -> bool:
        return self.user_type == "admin"


async def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CurrentUser:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "缺少认证令牌")
    payload = decode_token(creds.credentials)
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "令牌无效或已过期")
    if payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "令牌类型错误")

    account_id = int(payload.get("sub"))
    user_type = payload.get("user_type")
    ref_id = payload.get("ref_id")
    openid = payload.get("openid")

    # 校验账号仍存在
    acc = await db.get(WxAccount, account_id)
    if acc is None and user_type != "admin":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "账号不存在")

    return CurrentUser(
        account_id=account_id,
        user_type=user_type,
        ref_id=ref_id,
        openid=openid,
    )


def require_role(*roles: str):
    """角色校验依赖工厂。用法：Depends(require_role("user","child"))"""

    async def _check(cur: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if cur.user_type not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "权限不足")
        return cur

    return _check


# 常用别名
ElderUser = Annotated[CurrentUser, Depends(require_role("user"))]
ChildRole = Annotated[CurrentUser, Depends(require_role("child"))]
AdminRole = Annotated[CurrentUser, Depends(require_role("admin"))]
AnyRole = Annotated[CurrentUser, Depends(get_current_user)]
DB = Annotated[AsyncSession, Depends(get_db)]
