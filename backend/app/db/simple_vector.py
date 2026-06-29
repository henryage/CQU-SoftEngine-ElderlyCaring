"""简易向量存储 - chromadb 不可用时的降级方案。

Python 3.13 下 chromadb 的 hnswlib 依赖可能因缺少 MSVC 无法编译。
此实现用 numpy 余弦相似度 + pickle 持久化，接口模仿 chromadb collection，
保证 RAG 功能可用。后续装好 MSVC 后可无缝切回 chromadb。

性能：本地测试数据量（千级）足够，生产环境请用 chromadb。
"""
import json
import pickle
import logging
from pathlib import Path
from typing import Any
import numpy as np
from app.core.config import settings


logger = logging.getLogger(__name__)


class SimpleCollection:
    """模仿 chromadb Collection 的简易实现。"""

    def __init__(self, name: str, persist_path: Path):
        self.name = name
        self.persist_path = persist_path
        self._ids: list[str] = []
        self._embeddings: list[list[float]] = []
        self._documents: list[str] = []
        self._metadatas: list[dict] = []
        self._load()

    def _load(self):
        if self.persist_path.exists():
            try:
                with open(self.persist_path, "rb") as f:
                    data = pickle.load(f)
                self._ids = data.get("ids", [])
                self._embeddings = data.get("embeddings", [])
                self._documents = data.get("documents", [])
                self._metadatas = data.get("metadatas", [])
                logger.info("SimpleCollection[%s] 加载 %d 条向量", self.name, len(self._ids))
            except Exception as e:
                logger.warning("SimpleCollection[%s] 加载失败，重置: %s", self.name, e)
                self._ids = self._embeddings = self._documents = self._metadatas = []

    def _save(self):
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.persist_path, "wb") as f:
            pickle.dump({
                "ids": self._ids,
                "embeddings": self._embeddings,
                "documents": self._documents,
                "metadatas": self._metadatas,
            }, f)

    def add(self, ids, embeddings, documents=None, metadatas=None):
        for i, eid in enumerate(ids):
            if eid in self._ids:
                idx = self._ids.index(eid)
                self._embeddings[idx] = list(embeddings[i])
                if documents:
                    self._documents[idx] = documents[i]
                if metadatas:
                    self._metadatas[idx] = metadatas[i]
            else:
                self._ids.append(eid)
                self._embeddings.append(list(embeddings[i]))
                self._documents.append(documents[i] if documents else "")
                self._metadatas.append(metadatas[i] if metadatas else {})
        self._save()

    def query(self, query_embeddings, n_results=5, where=None):
        if not self._ids:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
        matrix = np.array(self._embeddings, dtype=np.float32)
        # 归一化做余弦相似度
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1
        matrix_norm = matrix / norms

        results = {"ids": [], "documents": [], "metadatas": [], "distances": []}
        for qe in query_embeddings:
            q = np.array(qe, dtype=np.float32)
            q = q / (np.linalg.norm(q) or 1)
            sims = matrix_norm @ q  # 余弦相似度
            # 过滤 where 条件
            candidates = []
            for idx, sim in enumerate(sims):
                if where and isinstance(where, dict):
                    ok = all(self._metadatas[idx].get(k) == v for k, v in where.items())
                    if not ok:
                        continue
                candidates.append((idx, sim))
            candidates.sort(key=lambda x: -x[1])
            top = candidates[:n_results]
            results["ids"].append([self._ids[i] for i, _ in top])
            results["documents"].append([self._documents[i] for i, _ in top])
            results["metadatas"].append([self._metadatas[i] for i, _ in top])
            # chromadb distance 是 1-similarity（越小越相似）
            results["distances"].append([float(1 - s) for _, s in top])
        return results

    def get(self, ids=None, where=None):
        out_ids, out_docs, out_metas = [], [], []
        for i, eid in enumerate(self._ids):
            if ids and eid not in ids:
                continue
            if where and isinstance(where, dict):
                if not all(self._metadatas[i].get(k) == v for k, v in where.items()):
                    continue
            out_ids.append(eid)
            out_docs.append(self._documents[i])
            out_metas.append(self._metadatas[i])
        return {"ids": out_ids, "documents": out_docs, "metadatas": out_metas}

    def delete(self, ids=None):
        if not ids:
            return
        keep = [i for i, eid in enumerate(self._ids) if eid not in ids]
        self._ids = [self._ids[i] for i in keep]
        self._embeddings = [self._embeddings[i] for i in keep]
        self._documents = [self._documents[i] for i in keep]
        self._metadatas = [self._metadatas[i] for i in keep]
        self._save()

    def count(self):
        return len(self._ids)


class SimpleVectorStore:
    """模仿 chromadb PersistentClient。"""

    def __init__(self, path: str):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)

    def get_or_create_collection(self, name: str, metadata=None):
        return SimpleCollection(name, self.path / f"{name}.pkl")
