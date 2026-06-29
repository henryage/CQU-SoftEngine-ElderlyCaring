"""Embedding 服务：文本 → 向量。

策略：
1. 优先用 chromadb 内置 embedding（all-MiniLM-L6-v2，~80MB，自动下载）
2. chroma 不可用时降级 numpy 随机向量（仅 dev 测试用，语义检索退化）

调用方式：
    from app.services.embedding import embed
    vec = embed("爸爸对青霉素过敏")
"""
import logging
import numpy as np

logger = logging.getLogger(__name__)

_embed_fn: object | None = None
_use_chroma_embed: bool | None = None
VECTOR_DIM = 384  # all-MiniLM-L6-v2 输出维度


def get_embedding_function():
    """获取 embedding 函数单例。

    优先 chroma 内置 SentenceTransformer，降级 numpy 随机向量。
    """
    global _embed_fn, _use_chroma_embed
    if _embed_fn is not None:
        return _embed_fn

    # 尝试 chroma 内置 embedding
    try:
        from chromadb.utils import embedding_functions
        _embed_fn = embedding_functions.DefaultEmbeddingFunction()
        # 预热：确保模型下载成功
        _embed_fn(["test"])
        _use_chroma_embed = True
        logger.info("✓ 使用 chromadb 内置 embedding（all-MiniLM-L6-v2）")
        return _embed_fn
    except Exception as e:
        logger.warning("chroma embedding 不可用，降级 numpy mock: %s", e)
        _use_chroma_embed = False

    # 降级：numpy 随机向量（mock，语义检索退化但功能可用）
    class _MockEmbedding:
        def __call__(self, texts: list[str]) -> list[list[float]]:
            # 对相同文本始终返回相同向量（基于文本 hash 种子的随机）
            vecs = []
            for t in texts:
                rng = np.random.RandomState(hash(t) % (2**31))
                vec = rng.randn(VECTOR_DIM).astype(np.float32)
                vec = vec / (np.linalg.norm(vec) + 1e-8)
                vecs.append(vec.tolist())
            return vecs

    _embed_fn = _MockEmbedding()
    logger.info("使用 numpy mock embedding（维度 %d）", VECTOR_DIM)
    return _embed_fn


def embed(text: str) -> list[float]:
    """单文本 → 向量。"""
    fn = get_embedding_function()
    return fn([text])[0]


def embed_batch(texts: list[str]) -> list[list[float]]:
    """批量文本 → 向量。"""
    fn = get_embedding_function()
    return fn(texts)


def is_mock_embedding() -> bool:
    """是否使用 mock embedding（语义检索退化）。"""
    get_embedding_function()
    return not bool(_use_chroma_embed)
