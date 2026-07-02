"""长期记忆路由（RAG 知识库）。

接口：
- GET    /memory                    记忆列表（分页/筛选）
- POST   /memory                    手动新增记忆
- GET    /memory/{memory_id}        记忆详情
- PUT    /memory/{memory_id}        编辑记忆
- DELETE /memory/{memory_id}        删除记忆（软删）
- PATCH  /memory/{memory_id}/importance  调整重要度
- POST   /memory/search             语义检索（Chroma）
"""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Body, HTTPException, Query, status
from sqlalchemy import select, func, and_

from app.core.deps import DB, AnyRole
from app.models.message import LongTermMemory
from app.schemas.common import R, Page
from app.schemas.memory import (
    MemoryIn, MemoryOut, MemoryImportanceIn, MemorySearchIn, MemorySearchOut,
)
from app.services.embedding import embed, embed_batch, is_mock_embedding


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/memory", tags=["memory"])

# Chroma collection 名称（与 db/chroma.py 一致）
COLLECTION_NAME = "long_term_memory"


# ============ 辅助函数 ============

def _mem_to_dict(m: LongTermMemory) -> dict:
    def _ts(dt) -> str | None:
        if dt is None:
            return None
        if isinstance(dt, str):
            return dt
        return dt.isoformat()

    return {
        "memory_id": m.memory_id,
        "user_id": m.user_id,
        "memory_type": m.memory_type,
        "source": m.source,
        "content": m.content,
        "summary": m.summary,
        "vector_id": m.vector_id,
        "importance": m.importance,
        "source_msg_id": m.source_msg_id,
        "is_deleted": bool(m.is_deleted),
        "created_at": _ts(m.created_at),
        "updated_at": _ts(m.updated_at),
    }


async def _add_to_chroma(memory_id: int, content: str) -> str:
    """将记忆写入 Chroma 向量库，返回 vector_id。

    dev mock 时用 memory_id 做 vector_id，语义搜索降级为关键词。
    """
    try:
        from app.db.chroma import get_memory_collection
        collection = get_memory_collection()
        vec = embed(content)
        vid = f"mem_{memory_id}"
        collection.upsert(
            ids=[vid],
            embeddings=[vec],
            metadatas=[{"memory_id": memory_id}],
        )
        logger.debug("Chroma 写入: vector_id=%s", vid)
        return vid
    except Exception as e:
        logger.warning("Chroma 写入失败（降级，搜索退化）: %s", e)
        # 降级：用 memory_id 做 vector_id，搜索时 database fallback
        return f"mem_{memory_id}"


async def _delete_from_chroma(vector_id: str):
    """从 Chroma 删除向量。"""
    try:
        from app.db.chroma import get_memory_collection
        collection = get_memory_collection()
        collection.delete(ids=[vector_id])
        logger.debug("Chroma 删除: vector_id=%s", vector_id)
    except Exception as e:
        logger.warning("Chroma 删除失败: %s", e)


def _build_list_query(db, user_id: int | None = None, memory_type: str | None = None,
                      source: str | None = None, min_importance: int | None = None,
                      page: int = 1, page_size: int = 20):
    """构造记忆列表查询（公用）。"""
    conditions = [LongTermMemory.is_deleted == 0]
    if user_id is not None:
        conditions.append(LongTermMemory.user_id == user_id)
    if memory_type:
        conditions.append(LongTermMemory.memory_type == memory_type)
    if source:
        conditions.append(LongTermMemory.source == source)
    if min_importance is not None:
        conditions.append(LongTermMemory.importance >= min_importance)

    total_stmt = select(func.count()).select_from(LongTermMemory).where(*conditions)
    items_stmt = (
        select(LongTermMemory)
        .where(*conditions)
        .order_by(LongTermMemory.importance.desc(), LongTermMemory.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return total_stmt, items_stmt


# ============ 接口 ============

@router.get("", response_model=R, summary="记忆列表", description="""
分页查询记忆列表，可按老人/类型/来源/重要度筛选。

**权限**：老人端查自己；子女端查绑定老人（需传 user_id）；管理端查任意。
""".strip())
async def list_memory(
    cur: AnyRole, db: DB,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    user_id: int | None = Query(None, description="老人ID。老人端不传=查自己；子女/管理端必传"),
    memory_type: str | None = Query(None, description="类型：用药/健康/偏好/医嘱/通用"),
    source: str | None = Query(None, description="来源：dialog/admin/system"),
    min_importance: int | None = Query(None, ge=1, le=5, description="最低重要度"),
):
    target_uid = _resolve_user_id(cur, user_id)
    total_stmt, items_stmt = _build_list_query(
        db, user_id=target_uid, memory_type=memory_type, source=source,
        min_importance=min_importance, page=page, page_size=page_size,
    )
    total = (await db.execute(total_stmt)).scalar() or 0
    items = (await db.execute(items_stmt)).scalars().all()

    return R.ok(Page(
        total=total, page=page, page_size=page_size,
        items=[_mem_to_dict(m) for m in items],
    ).model_dump(mode="json"))


@router.post("", response_model=R, summary="新增记忆", description="""
手动新增一条记忆。写入 MySQL 并同步写入 Chroma 向量库。

**权限**：子女端 / 管理端。source 默认 admin。
""".strip(), responses={
    201: {"description": "新增成功"},
    400: {"description": "参数错误"},
})
async def create_memory(payload: MemoryIn, cur: AnyRole, db: DB):
    if not cur.is_child and not cur.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "仅子女端/管理端可手动新增记忆")

    # 自动推断来源
    source = payload.source if payload.source != "admin" else ("child" if cur.is_child else "admin")

    summary = payload.summary or payload.content[:100]
    mem = LongTermMemory(
        user_id=payload.user_id,
        memory_type=payload.memory_type,
        source=source,
        content=payload.content,
        summary=summary,
        importance=payload.importance,
        # TODO: source_msg_id 后续大模型自动抽取记忆时从对话消息关联
        source_msg_id=None,
    )
    db.add(mem)
    await db.flush()

    # 写入 Chroma（importance=1 仅存库，不进向量检索）
    if payload.importance and payload.importance > 1:
        try:
            vid = await _add_to_chroma(mem.memory_id, payload.content)
            mem.vector_id = vid
            await db.flush()
        except Exception:
            pass

    await db.refresh(mem)

    return R.ok(_mem_to_dict(mem), msg="新增成功")


@router.get("/{memory_id}", response_model=R, summary="记忆详情")
async def get_memory(memory_id: int, cur: AnyRole, db: DB):
    mem = await db.get(LongTermMemory, memory_id)
    if mem is None or mem.is_deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "记忆不存在")
    return R.ok(_mem_to_dict(mem))


@router.put("/{memory_id}", response_model=R, summary="编辑记忆")
async def update_memory(memory_id: int, payload: MemoryIn, cur: AnyRole, db: DB):
    if not cur.is_child and not cur.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "仅子女端/管理端可编辑")

    mem = await db.get(LongTermMemory, memory_id)
    if mem is None or mem.is_deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "记忆不存在")

    old_vid = mem.vector_id
    mem.user_id = payload.user_id
    mem.memory_type = payload.memory_type
    mem.source = payload.source if payload.source != "admin" else ("child" if cur.is_child else "admin")
    mem.content = payload.content
    mem.summary = payload.summary or payload.content[:100]
    mem.importance = payload.importance
    # TODO: source_msg_id 编辑时保持不变，暂不支持修改

    # 更新 Chroma：importance=1 不写向量
    if old_vid:
        await _delete_from_chroma(old_vid)
    if payload.importance and payload.importance > 1:
        try:
            vid = await _add_to_chroma(mem.memory_id, payload.content)
            mem.vector_id = vid
        except Exception:
            pass

    return R.ok(_mem_to_dict(mem), msg="编辑成功")


@router.delete("/{memory_id}", response_model=R, summary="删除记忆（软删）")
async def delete_memory(memory_id: int, cur: AnyRole, db: DB):
    """软删除：设 is_deleted=1，不清 Chroma（定时任务异步清理）。"""
    if not cur.is_child and not cur.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "仅子女端/管理端可删除")

    mem = await db.get(LongTermMemory, memory_id)
    if mem is None or mem.is_deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "记忆不存在")

    mem.is_deleted = 1
    return R.ok(msg="已删除")


@router.patch("/{memory_id}/importance", response_model=R, summary="调整重要度")
async def set_importance(memory_id: int, payload: MemoryImportanceIn, cur: AnyRole, db: DB):
    """仅子女端/管理端可调。1-5。importance=1 仅存库不进向量，>1 进 Chroma。"""
    mem = await db.get(LongTermMemory, memory_id)
    if mem is None or mem.is_deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "记忆不存在")

    old_imp = mem.importance
    mem.importance = payload.importance

    # 跨阈值更新 Chroma
    if old_imp <= 1 and payload.importance > 1:
        try:
            vid = await _add_to_chroma(mem.memory_id, mem.content)
            mem.vector_id = vid
        except Exception:
            pass
    elif old_imp > 1 and payload.importance <= 1 and mem.vector_id:
        await _delete_from_chroma(mem.vector_id)
        mem.vector_id = None

    return R.ok(_mem_to_dict(mem), msg="重要度已更新")


@router.post("/search", response_model=R, summary="语义检索（RAG 核心）", description="""
根据自然语言问题检索最相关的记忆条目。

**流程**：
1. query 向量化
2. Chroma 搜 top-K 相似向量
3. MySQL 回查完整内容

**用途**：QA 问答时自动调用，拼接进 system_prompt；管理端也可手动搜。

**注意**：当前 Chroma 不可用时降级为数据库关键词匹配（搜索退化）。
""".strip())
async def search_memory(payload: MemorySearchIn, cur: AnyRole, db: DB):
    results: list[dict] = []

    try:
        from app.db.chroma import get_memory_collection, is_using_chroma
        collection = get_memory_collection()
        query_vec = embed(payload.query)

        chroma_results = collection.query(
            query_embeddings=[query_vec],
            n_results=payload.top_k,
            where={"memory_id": {"$gte": 0}},
        )
        # chroma_results["ids"][0] = [vid1, vid2, ...]
        # chroma_results["distances"][0] = [d1, d2, ...]  (cosine distance, 越小越相似)
        ids_list = chroma_results.get("ids", [[]])[0]
        distances = chroma_results.get("distances", [[]])[0]

        scored: list[tuple[int, float]] = []
        for i, vid in enumerate(ids_list):
            try:
                mid = int(vid.replace("mem_", ""))
                score = 1.0 - min(float(distances[i]) if i < len(distances) else 0.5, 1.0)
                scored.append((mid, score))
            except (ValueError, IndexError):
                continue

        # 按 similarity 降序
        scored.sort(key=lambda x: x[1], reverse=True)

        if scored:
            mids = [m[0] for m in scored]
            score_map = {m[0]: m[1] for m in scored}
            stmt = (
                select(LongTermMemory)
                .where(LongTermMemory.memory_id.in_(mids), LongTermMemory.is_deleted == 0)
            )
            memories = (await db.execute(stmt)).scalars().all()
            for m in memories:
                if m.memory_id in score_map:
                    results.append({
                        "memory_id": m.memory_id,
                        "content": m.content,
                        "summary": m.summary,
                        "memory_type": m.memory_type,
                        "importance": m.importance,
                        "score": round(score_map[m.memory_id], 4),
                    })

    except Exception as e:
        logger.warning("Chroma 检索失败，降级数据库关键词搜索: %s", e)
        # 降级：数据库 LIKE 搜索
        stmt = (
            select(LongTermMemory)
            .where(
                LongTermMemory.user_id == payload.user_id,
                LongTermMemory.is_deleted == 0,
                LongTermMemory.importance > 1,
                LongTermMemory.content.like(f"%{payload.query}%"),
            )
            .order_by(LongTermMemory.importance.desc())
            .limit(payload.top_k)
        )
        memories = (await db.execute(stmt)).scalars().all()
        for m in memories:
            results.append({
                "memory_id": m.memory_id,
                "content": m.content,
                "summary": m.summary,
                "memory_type": m.memory_type,
                "importance": m.importance,
                "score": 0.5,
            })

    return R.ok([MemorySearchOut(**r).model_dump() for r in results])


def _resolve_user_id(cur, user_id: int | None) -> int | None:
    """解析查询目标老人ID。"""
    if cur.is_elder:
        return cur.ref_id
    if cur.is_child or cur.is_admin:
        return user_id  # None 也行，查所有（管理端）
    raise HTTPException(status.HTTP_403_FORBIDDEN, "无权访问")
