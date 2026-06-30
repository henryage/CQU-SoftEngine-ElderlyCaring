"""Embedding 服务：文本 → 向量。

- USE_REMOTE_INFERENCE=true → POST :8001/embed（Qwen3-Embedding-8B, 4096维）
- USE_REMOTE_INFERENCE=false → chroma 内置 all-MiniLM-L6-v2 (384维)

切换模式后需删 data/chroma/ 重建。
"""
import logging
import numpy as np
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

_embed_fn: object | None = None
_use_remote: bool | None = None
REMOTE_DIM = 4096
LOCAL_DIM = 384


def get_vector_dim() -> int:
    return REMOTE_DIM if settings.use_remote_inference else LOCAL_DIM


def _fallback_vec() -> list[float]:
    return [0.0] * get_vector_dim()


def get_embedding_function():
    global _embed_fn, _use_remote
    if _embed_fn is not None:
        return _embed_fn

    if settings.use_remote_inference:
        _use_remote = True
        logger.info("远程 embedding Qwen3-Embedding-8B @ %s", settings.embedding_api_url)

        class _RemoteEmbedding:
            def __call__(self, texts):
                vecs = []
                for t in texts:
                    try:
                        resp = httpx.post(
                            f"{settings.embedding_api_url.rstrip('/')}/embed",
                            json={"text": t, "normalize": True}, timeout=30,
                        )
                        if resp.status_code == 200:
                            vecs.append(resp.json()["vector"])
                        else:
                            logger.error("embed %d: %s", resp.status_code, resp.text[:200])
                            vecs.append(_fallback_vec())
                    except Exception as e:
                        logger.error("embed error: %s", e)
                        vecs.append(_fallback_vec())
                return vecs

        _embed_fn = _RemoteEmbedding()
        return _embed_fn

    try:
        from chromadb.utils import embedding_functions
        _embed_fn = embedding_functions.DefaultEmbeddingFunction()
        _embed_fn(["test"])
        _use_remote = False
        logger.info("本地 chroma embedding all-MiniLM-L6-v2")
        return _embed_fn
    except Exception as e:
        logger.warning("chroma embedding 不可用，降级: %s", e)

    class _MockEmbedding:
        def __call__(self, texts):
            return [_fallback_vec() for _ in texts]

    _embed_fn = _MockEmbedding()
    _use_remote = False
    logger.info("numpy mock embedding 维度=%d", LOCAL_DIM)
    return _embed_fn


def embed(text: str) -> list[float]:
    return get_embedding_function()([text])[0]


def embed_batch(texts: list[str]) -> list[list[float]]:
    return get_embedding_function()(texts)


def is_mock_embedding() -> bool:
    get_embedding_function()
    return bool(_use_remote is False)
