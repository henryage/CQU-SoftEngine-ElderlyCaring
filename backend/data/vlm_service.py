"""VLM Service - Qwen3-VL-30B-A3B-Instruct (MoE, INT8)
端口 :8002
接口 GET /health  POST /chat

支持纯文本和图片+文本问答。
图片以 base64 方式传入。
"""
import logging, time, os, base64, io
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from transformers import Qwen3VLForConditionalGeneration, AutoProcessor
from contextlib import asynccontextmanager
from PIL import Image

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vlm")

MODEL_NAME = "Qwen/Qwen3-VL-30B-A3B-Instruct"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

_model = None
_processor = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _model, _processor
    logger.info("正在加载 %s (INT8) to %s...", MODEL_NAME, DEVICE)
    t0 = time.time()
    _model = Qwen3VLForConditionalGeneration.from_pretrained(
        MODEL_NAME, trust_remote_code=True,
        torch_dtype=torch.float16, device_map="auto",
        load_in_8bit=True,
    )
    _processor = AutoProcessor.from_pretrained(MODEL_NAME, trust_remote_code=True)
    logger.info("模型加载完成 (%.1fs), device=%s", time.time() - t0, _model.device)
    yield


app = FastAPI(title="VLM Service", lifespan=lifespan)


class Message(BaseModel):
    role: str = Field(default="user", description="system / user / assistant")
    content: str = Field(..., description="消息内容")

class ChatRequest(BaseModel):
    messages: list[Message] = Field(..., description="对话历史（至少包含一条 user 消息）")
    image_b64: str | None = Field(default=None, description="图片 base64（可选，用于视觉问答）")
    max_tokens: int = Field(default=1024, ge=1, le=4096)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)

class ChatResponse(BaseModel):
    answer: str
    elapsed_ms: float


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_NAME, "device": str(_model.device)}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    t0 = time.time()

    # 构建消息
    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    # 准备输入
    if req.image_b64:
        try:
            img_bytes = base64.b64decode(req.image_b64)
            image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        except Exception as e:
            raise HTTPException(400, f"image_b64 解码失败: {e}")
        inputs = _processor(
            text=_processor.apply_chat_template(messages, add_generation_prompt=True),
            images=[image], return_tensors="pt",
        )
        # 截取最后一条 user 消息的文本作为大模型的实际输入提示
        user_text = messages[-1]["content"] if messages else ""
        inputs["input_ids"] = inputs["input_ids"].to(_model.device)
    else:
        text = _processor.apply_chat_template(messages, add_generation_prompt=True)
        inputs = _processor(text=[text], return_tensors="pt", padding=True)
        inputs["input_ids"] = inputs["input_ids"].to(_model.device)

    with torch.no_grad():
        outputs = _model.generate(
            **inputs,
            max_new_tokens=req.max_tokens,
            temperature=req.temperature,
            do_sample=req.temperature > 0,
        )

    answer = _processor.decode(outputs[0], skip_special_tokens=True)
    # 去掉输入部分的回显（Qwen3-VL 可能把 prompt 也输出）
    if "assistant\n" in answer:
        answer = answer.split("assistant\n")[-1].strip()

    return ChatResponse(
        answer=answer,
        elapsed_ms=(time.time() - t0) * 1000,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
