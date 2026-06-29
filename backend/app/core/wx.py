"""微信能力封装：code2session、订阅消息推送。

dev 模式（不注册小程序）下：
- code2session 直接返回 mock openid
- subscribe_message.send 仅打印日志（不真实推送）
"""
import logging
from typing import Any
import httpx
from app.core.config import settings


logger = logging.getLogger(__name__)


async def code2session(code: str) -> dict[str, Any]:
    """小程序 code 换 openid + session_key。

    dev 模式：直接用 code 当作 mock openid 返回，方便本地测试。
    prod 模式：调用微信开放接口。
    """
    if settings.is_dev:
        # dev 模式：code 即 openid，方便测试
        mock_openid = code or settings.mock_openid_eldery
        return {
            "openid": mock_openid,
            "session_key": "dev_session_key",
            "unionid": None,
        }

    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": settings.wx_app_id,
        "secret": settings.wx_app_secret,
        "js_code": code,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
    if "openid" not in data:
        raise RuntimeError(f"code2session 失败: {data}")
    return data


async def get_access_token() -> str:
    """获取微信 access_token（prod 用，需缓存）。dev 模式返回占位。"""
    if settings.is_dev:
        return "dev_access_token"

    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {
        "grant_type": "client_credential",
        "appid": settings.wx_app_id,
        "secret": settings.wx_app_secret,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
    return data.get("access_token", "")


async def send_subscribe_message(
    openid: str,
    template_id: str,
    data: dict[str, Any],
    page: str = "pages/index/index",
) -> bool:
    """推送订阅消息。

    dev 模式：仅打印日志，返回 True（不真实推送，因为没有真实小程序）。
    prod 模式：调用微信 subscribeMessage.send。
    """
    if settings.is_dev:
        logger.info(
            "[DEV] 订阅消息推送（模拟） -> openid=%s template=%s page=%s data=%s",
            openid, template_id, page, data,
        )
        return True

    token = await get_access_token()
    url = f"https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token={token}"
    body = {
        "touser": openid,
        "template_id": template_id,
        "page": page,
        "data": data,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, json=body)
        resp.raise_for_status()
        result = resp.json()
    if result.get("errcode", 0) != 0:
        logger.error("订阅消息推送失败: %s", result)
        return False
    return True
