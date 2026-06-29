"""大模型客户端：封装对外部大模型 API 的调用。

dev 模式：mock 答题器（返回固定话术），不真实调用大模型
prod 模式：调 OpenAI 兼容接口（/v1/chat/completions）

支持：
- 多模态（文本 + 图片 URL）
- 流式输出（generator）
- 超时控制
- 医疗合规拦截（关键词匹配）
- 预警信号抽取（让大模型在回答末尾输出结构化 JSON）
"""
import logging
import json
import asyncio
from typing import AsyncGenerator
import httpx
from app.core.config import settings


logger = logging.getLogger(__name__)

# 医疗合规关键词（命中即追加免责声明）
MEDICAL_KEYWORDS = [
    "药品", "药物", "吃药", "服用", "剂量", "副作用", "禁忌",
    "处方", "医嘱", "诊断", "治疗", "症状", "高血压", "糖尿病",
    "降压药", "降糖药", "布洛芬", "阿司匹林", "感冒药",
]

# 预警关键词（命中即触发预警）
ALERT_KEYWORDS = {
    "跌倒": {"alert_type": "跌倒", "alert_level": "紧急"},
    "摔倒": {"alert_type": "跌倒", "alert_level": "紧急"},
    "起不来": {"alert_type": "跌倒", "alert_level": "紧急"},
    "救命": {"alert_type": "紧急呼叫", "alert_level": "紧急"},
    "难受": {"alert_type": "情绪低落", "alert_level": "警告"},
    "不想活": {"alert_type": "情绪低落", "alert_level": "紧急"},
}


async def call_llm(
    prompt: str,
    image_url: str | None = None,
    system_prompt: str | None = None,
    stream: bool = False,
) -> str | AsyncGenerator[str, None]:
    """调用大模型。

    Args:
        prompt: 用户问题
        image_url: 图片 URL（多模态），None 则纯文本
        system_prompt: 系统提示词
        stream: 是否流式

    Returns:
        stream=False: 完整回答字符串
        stream=True: 异步生成器，yield 每个 chunk
    """
    if not settings.llm_api_key:
        return await _mock_call(prompt, image_url, stream)
    return await _real_call(prompt, image_url, system_prompt, stream)


async def _mock_call(
    prompt: str, image_url: str | None, stream: bool
) -> str | AsyncGenerator[str, None]:
    """dev 模式 mock 答题器。"""
    # 模拟网络延迟
    await asyncio.sleep(0.3)

    # 根据问题构造 mock 回答
    if image_url:
        answer = (
            f"【模拟回答】我看到你发了一张图片（{image_url}）。"
            f"你问的是：{prompt or '（未提供文字问题）'}。\n\n"
            "由于当前是开发模式（未配置大模型 API Key），这是模拟回答。"
            "配置 .env 里的 LLM_API_KEY 后可接入真实大模型。"
        )
    else:
        answer = (
            f"【模拟回答】你问的是：{prompt}\n\n"
            "由于当前是开发模式（未配置大模型 API Key），这是模拟回答。"
            "配置 .env 里的 LLM_API_KEY 后可接入真实大模型。"
        )

    # 关键词检测：如果问题含医疗关键词，模拟合规拦截
    for kw in MEDICAL_KEYWORDS:
        if kw in (prompt or ""):
            answer += "\n\n⚠️ 提示：以上信息仅供参考，具体用药请遵医嘱。"
            break

    if stream:
        async def _gen():
            # 模拟逐字流式
            for char in answer:
                await asyncio.sleep(0.02)
                yield char
        return _gen()
    return answer


async def _real_call(
    prompt: str,
    image_url: str | None,
    system_prompt: str | None,
    stream: bool,
) -> str | AsyncGenerator[str, None]:
    """真实调用大模型（OpenAI 兼容接口）。

    支持 ChatGPT / DeepSeek / 通义千问 / Kimi 等 OpenAI 格式的 API。
    可配置 .env 中的 LLM_API_BASE / LLM_API_KEY / LLM_MODEL 切换。

    图片 URL 需要是公网可访问的完整 URL。
    本地测试时可配置 .env PUBLIC_URL，会自动把 /files/ 拼接为完整 URL。
    """
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }

    # 构造消息体
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    if image_url:
        # 多模态：文本 + 图片
        # 转换相对路径为完整 URL（prod 需要）
        full_image_url = _resolve_image_url(image_url)
        user_content = [
            {"type": "text", "text": prompt or "请描述这张图片的内容"},
            {"type": "image_url", "image_url": {"url": full_image_url}},
        ]
        messages.append({"role": "user", "content": user_content})
    else:
        messages.append({"role": "user", "content": prompt})

    body = {
        "model": settings.llm_model,
        "messages": messages,
        "stream": stream,
        "max_tokens": 2000,
    }

    url = f"{settings.llm_api_base.rstrip('/')}/chat/completions"

    if stream:
        async def _stream_gen():
            async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
                async with client.stream("POST", url, headers=headers, json=body) as resp:
                    if resp.status_code != 200:
                        err_body = await resp.aread()
                        logger.error("大模型流式调用失败: %s %s", resp.status_code, err_body[:500])
                        raise RuntimeError(f"大模型返回 {resp.status_code}: {err_body[:300]}")
                    async for line in resp.aiter_lines():
                        if line.startswith("data: ") and line != "data: [DONE]":
                            try:
                                chunk = json.loads(line[6:])
                                delta = chunk["choices"][0]["delta"].get("content", "")
                                if delta:
                                    yield delta
                            except (json.JSONDecodeError, KeyError, IndexError):
                                continue
        return _stream_gen()
    else:
        async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
            resp = await client.post(url, headers=headers, json=body)
            if resp.status_code != 200:
                err_text = resp.text[:500]
                logger.error("大模型调用失败: %s %s", resp.status_code, err_text)
                raise RuntimeError(f"大模型返回 {resp.status_code}: {err_text}")
            data = resp.json()
            return data["choices"][0]["message"]["content"]


def _resolve_image_url(url: str) -> str:
    """将相对路径图片 URL 转为完整公网 URL。

    本地 /files/xxx.jpg → PUBLIC_URL/files/xxx.jpg
    已是完整 URL 的保持不变。
    """
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if hasattr(settings, "public_url") and settings.public_url:
        return settings.public_url.rstrip("/") + url
    return url  # dev 模式原样返回，mock 不用真 URL


def check_medical_intercept(text: str) -> tuple[bool, list[str]]:
    """检查文本是否命中医疗合规关键词。

    Returns:
        (是否命中, 命中的关键词列表)
    """
    hits = [kw for kw in MEDICAL_KEYWORDS if kw in text]
    return (len(hits) > 0, hits)


def check_alert_signal(text: str) -> dict | None:
    """检查文本是否包含预警关键词。

    Returns:
        预警信号 dict 或 None
    """
    for kw, signal in ALERT_KEYWORDS.items():
        if kw in text:
            return {
                "alert_type": signal["alert_type"],
                "alert_level": signal["alert_level"],
                "detail": f"老人输入中包含关键词『{kw}』",
            }
    return None


def append_disclaimer(answer: str) -> str:
    """给涉医回答追加免责声明。"""
    disclaimer = "\n\n⚠️ 温馨提示：以上信息仅供参考，具体用药请遵医嘱，如有不适请及时就医。"
    if "请遵医嘱" not in answer:
        return answer + disclaimer
    return answer
