"""大模型客户端：调用远程 VLM / 本地 mock。

- USE_REMOTE_INFERENCE=true → POST :8002/chat（远程 Qwen3-VL-30B）
- USE_REMOTE_INFERENCE=false → mock 回答

图片以 base64 传入，文本/图片统一走同一接口。
"""
import logging
import base64
import asyncio
from pathlib import Path
from typing import AsyncGenerator
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

MEDICAL_KEYWORDS = [
    "药品", "药物", "吃药", "服用", "剂量", "副作用", "禁忌",
    "处方", "医嘱", "诊断", "治疗", "症状", "高血压", "糖尿病",
    "降压药", "降糖药", "布洛芬", "阿司匹林", "感冒药",
]

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
    image_path: str | None = None,
    system_prompt: str | None = None,
    stream: bool = False,
) -> str | AsyncGenerator[str, None]:
    if settings.use_remote_inference:
        return await _remote_vlm(prompt, image_path, system_prompt)
    return await _mock_call(prompt, image_path, stream)


async def _remote_vlm(
    prompt: str, image_path: str | None, system_prompt: str | None,
) -> str:
    """调远程 VLM :8002/chat。图片读文件转 base64。"""
    image_b64: str | None = None
    if image_path:
        try:
            path = Path(image_path)
            if not path.is_absolute():
                # image_path 是 URL 路径如 /files/img_xxx.jpg，去掉前缀拼到 upload_dir
                rel = image_path.lstrip("/").removeprefix("files/")
                path = Path(settings.upload_dir) / rel
            image_b64 = base64.b64encode(path.read_bytes()).decode()
        except Exception as e:
            logger.warning("图片读取失败，降级纯文本: %s", e)

    body = {"messages": [], "max_tokens": 1024}
    if system_prompt:
        body["messages"].append({"role": "system", "content": system_prompt})
    body["messages"].append({"role": "user", "content": prompt or "请描述这张图片"})
    if image_b64:
        body["image_b64"] = image_b64

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{settings.vlm_api_url.rstrip('/')}/chat", json=body,
        )
        if resp.status_code != 200:
            logger.error("VLM 调用失败 (%d): %s", resp.status_code, resp.text[:500])
            return f"【推理服务异常：{resp.status_code}】"
        return resp.json()["answer"]


async def _mock_call(
    prompt: str, image_path: str | None, stream: bool
) -> str | AsyncGenerator[str, None]:
    await asyncio.sleep(0.3)
    if image_path:
        answer = f"【模拟回答】图片 {image_path} — {prompt or '（未提供文字）'}。dev 模式 mock。"
    else:
        answer = f"【模拟回答】{prompt}。dev 模式 mock。"

    for kw in MEDICAL_KEYWORDS:
        if kw in (prompt or ""):
            answer += "\n\n⚠️ 以上信息仅供参考，请遵医嘱。"
            break

    if stream:
        async def _gen():
            for char in answer:
                await asyncio.sleep(0.02)
                yield char
        return _gen()
    return answer


def check_medical_intercept(text: str) -> tuple[bool, list[str]]:
    hits = [kw for kw in MEDICAL_KEYWORDS if kw in text]
    return (len(hits) > 0, hits)


def check_alert_signal(text: str) -> dict | None:
    for kw, signal in ALERT_KEYWORDS.items():
        if kw in text:
            return {"alert_type": signal["alert_type"], "alert_level": signal["alert_level"], "detail": f"老人输入中含关键词『{kw}』"}
    return None


def append_disclaimer(answer: str) -> str:
    if "请遵医嘱" not in answer:
        return answer + "\n\n⚠️ 温馨提示：以上信息仅供参考，具体用药请遵医嘱。"
    return answer
