"""向量库客户端单例 - 优先 chromadb，失败降级 SimpleVectorStore。

记忆库 = RAG 知识库，所有 long_term_memory 的向量都存这里。
Python 3.13 下 chromadb 的 hnswlib 可能因缺 MSVC 无法编译，
此时自动降级到 SimpleVectorStore（numpy + pickle），
接口兼容，后续装好 MSVC 后无需改业务代码即可切回 chromadb。
"""
import logging
from typing import Any
from app.core.config import settings


logger = logging.getLogger(__name__)

_client: Any = None
_collection: Any = None
_use_chroma: bool | None = None


def _try_init_chroma():
    """尝试初始化 chromadb，成功返回 client，失败返回 None。"""
    global _use_chroma
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        client = chromadb.PersistentClient(
            path=str(settings.chroma_persist_path),
            settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True),
        )
        # 触发一次实际调用验证可用
        client.heartbeat()
        _use_chroma = True
        logger.info("✓ 使用 chromadb 作为向量库")
        return client
    except Exception as e:
        logger.warning("chromadb 不可用，降级到 SimpleVectorStore: %s", e)
        _use_chroma = False
        return None


def get_vector_client():
    """获取向量库客户端单例。"""
    global _client
    if _client is None:
        _client = _try_init_chroma()
        if _client is None:
            from app.db.simple_vector import SimpleVectorStore
            _client = SimpleVectorStore(settings.chroma_persist_path)
    return _client


def get_memory_collection():
    """获取长期记忆 collection（= RAG 知识库）。不存在则创建。"""
    global _collection
    if _collection is None:
        client = get_vector_client()
        _collection = client.get_or_create_collection(
            name=settings.chroma_collection_memory,
            metadata={"hnsw:space": "cosine"} if _use_chroma else None,
        )
    return _collection


def is_using_chroma() -> bool:
    """是否使用 chromadb（True）还是降级方案（False）。"""
    return bool(_use_chroma)
