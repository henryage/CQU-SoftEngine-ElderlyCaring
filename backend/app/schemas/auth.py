"""鉴权相关 schema。

包含微信登录、绑定手机号、token 刷新、管理员登录、订阅授权上报的入参，
以及登录成功后的 token 出参。
"""
from datetime import datetime
from pydantic import BaseModel, Field


class WxLoginIn(BaseModel):
    """小程序登录入参。

    - **dev 模式**：`code` 可传任意字符串（或留空走 mock openid），用于本地测试不接微信
    - **prod 模式**：`code` 是小程序 `wx.login()` 返回的临时登录凭证，5 分钟有效
    """
    code: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="小程序登录凭证。dev 模式可传任意字符串；prod 模式为 wx.login() 返回的 code",
        examples=["0a3xPP000xxx"],
    )
    user_type: str = Field(
        default="user",
        description="登录端类型：user=老人端，child=子女端",
        examples=["user"],
    )


class BindPhoneIn(BaseModel):
    """绑定手机号入参（子女端）。

    - **dev 模式**：直接传手机号字符串，不走微信 getPhoneNumber 解密
    - **prod 模式**：应传微信 getPhoneNumber 回调里的 encryptedData + iv，
      由后端用 session_key 解密；当前为简化版本，直接收手机号
    """
    phone: str = Field(
        ...,
        min_length=11,
        max_length=11,
        description="手机号（11 位）",
        examples=["13800138000"],
    )
    name: str | None = Field(
        default=None,
        max_length=64,
        description="子女姓名（可选，首次绑定建议填）",
        examples=["小明"],
    )
    relation: str | None = Field(
        default=None,
        max_length=32,
        description="与老人的关系：子女/亲属/医生",
        examples=["子女"],
    )


class TokenOut(BaseModel):
    """登录/刷新成功后返回的 token 信息。"""
    token: str = Field(..., description="访问令牌（Access Token），有效期 30 分钟", examples=["eyJhbGciOi..."])
    refresh_token: str = Field(..., description="刷新令牌（Refresh Token），有效期 7 天", examples=["eyJhbGciOi..."])
    token_type: str = Field(default="Bearer", description="令牌类型，固定 Bearer", examples=["Bearer"])
    user_type: str = Field(..., description="用户类型：user/child/admin", examples=["user"])
    ref_id: int | None = Field(..., description="关联的业务 ID（老人 user_id / 子女 child_id / 管理员 admin_id）", examples=[6])
    nickname: str | None = Field(default=None, description="昵称", examples=["老人6"])


class RefreshIn(BaseModel):
    """token 刷新入参。"""
    refresh_token: str = Field(
        ...,
        description="登录时返回的 refresh_token，有效期 7 天",
        examples=["eyJhbGciOi..."],
    )


class AdminLoginIn(BaseModel):
    """管理员登录入参（Web 控制台用）。"""
    username: str = Field(..., min_length=1, max_length=64, description="管理员用户名", examples=["admin"])
    password: str = Field(..., min_length=1, max_length=128, description="管理员密码", examples=["admin"])


class SubscribeGrantIn(BaseModel):
    """订阅消息授权上报入参。

    小程序调用 `wx.requestSubscribeMessage` 后，将用户授权结果上报后端，
    后端据此记录剩余可推送次数（一次性模板按次数计）。
    """
    template_id: str = Field(
        ...,
        max_length=64,
        description="订阅消息模板 ID（在微信公众平台申请后获得）",
        examples=["tpl_alert_urgent"],
    )
    grant_status: str = Field(
        ...,
        description="授权结果：accept=同意，reject=拒绝，ban=被禁止（用户勾选了不再询问）",
        examples=["accept"],
    )


class HeartbeatOut(BaseModel):
    """心跳上报成功响应数据。"""
    heartbeat_at: datetime = Field(..., description="本次心跳时间（ISO 8601，UTC）", examples=["2026-06-27T03:43:50Z"])
    online_status: str = Field(..., description="在线状态：online=在线", examples=["online"])
