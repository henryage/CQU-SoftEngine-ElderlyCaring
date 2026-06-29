"""Embedding Service - Qwen3-Embedding-8B (INT8)
端口 :8001
接口 GET /health  POST /embed
"""
import logging, time, os
import torch
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from transformers import AutoModel, AutoTokenizer
from contextlib import asynccontextmanager

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("embedding")

MODEL_NAME = "Qwen/Qwen3-Embedding-8B"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

_model = None
_tokenizer = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _model, _tokenizer
    logger.info("正在加载 %s (INT8) to %s...", MODEL_NAME, DEVICE)
    t0 = time.time()
    _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    _model = AutoModel.from_pretrained(
        MODEL_NAME, trust_remote_code=True,
        torch_dtype=torch.float16, device_map="auto",
        load_in_8bit=True,
    )
    _model.eval()
    logger.info("模型加载完成 (%.1fs), device=%s", time.time() - t0, _model.device)
    yield


app = FastAPI(title="Embedding Service", lifespan=lifespan)


class EmbedRequest(BaseModel):
    text: str = Field(..., description="待向量化的文本")
    normalize: bool = Field(default=True, description="是否归一化")


class EmbedResponse(BaseModel):
    vector: list[float]
    dim: int
    elapsed_ms: float


def last_token_pool(last_hidden_states: torch.Tensor, attention_mask: torch.Tensor):
    """取最后一个有效 token 的 hidden state 作为句子向量"""
    sequence_lengths = attention_mask.sum(dim=1) - 1
    batch_size = last_hidden_states.shape[0]
    return last_hidden_states[
        torch.arange(batch_size, device=last_hidden_states.device), sequence_lengths
    ]


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_NAME, "device": str(_model.device)}


@app.post("/embed", response_model=EmbedResponse)
def embed(req: EmbedRequest):
    if not req.text.strip():
        raise HTTPException(400, "text 不能为空")
    t0 = time.time()
    inputs = _tokenizer(req.text, return_tensors="pt", padding=True, truncation=True, max_length=8192).to(_model.device)
    with torch.no_grad():
        outputs = _model(**inputs)
        vec = last_token_pool(outputs.last_hidden_state, inputs["attention_mask"]).cpu().float().numpy()
    if req.normalize:
        vec = vec / (np.linalg.norm(vec) + 1e-8)
    return EmbedResponse(
        vector=vec[0].tolist(),
        dim=vec.shape[1],
        elapsed_ms=(time.time() - t0) * 1000,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
