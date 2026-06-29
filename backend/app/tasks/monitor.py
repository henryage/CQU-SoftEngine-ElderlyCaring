"""定时任务：老人离线检测 + 软删向量清理。

- 每 60 秒扫描一次老人心跳，超 180 秒未心跳判离线
- 每 3600 秒（1 小时）扫描 is_deleted=1 的记忆，清理 Chroma 向量

启动方式：在 main.py 的 lifespan 中启动，或单独脚本运行。
"""
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, and_
from app.db.session import AsyncSessionLocal
from app.models.user import User, ChildUser, WxAccount, UserChildRelation
from app.models.message import LongTermMemory
from app.models.interaction import AlertEvent
from app.core.config import settings


logger = logging.getLogger(__name__)

# 离线判定阈值
OFFLINE_THRESHOLD_SECONDS = 180
SCAN_INTERVAL_SECONDS = 60
# 软删向量清理间隔（1 小时）
VECTOR_CLEAN_INTERVAL_SECONDS = 3600


async def scan_offline_users():
    """扫描离线老人，触发网络断开预警。

    只对 online_status=online 但 last_heartbeat_at 超过阈值的老人触发：
    - 改 online_status=offline
    - 写 alert_event(网络断开, 警告级, rule)
    - 推送子女端订阅消息
    """
    threshold = datetime.now(timezone.utc) - timedelta(seconds=OFFLINE_THRESHOLD_SECONDS)

    async with AsyncSessionLocal() as db:
        # 找出"标记在线但心跳超时"的老人
        stmt = select(User).where(
            and_(
                User.online_status == "online",
                User.last_heartbeat_at.is_not(None),
                User.last_heartbeat_at < threshold,
                User.status == 1,  # 仅正常状态账号
            )
        )
        result = await db.execute(stmt)
        offline_users = result.scalars().all()

        if not offline_users:
            return 0

        count = 0
        for u in offline_users:
            u.online_status = "offline"

            # 去重：检查是否已有未处理的"网络断开"预警（避免重复发）
            existing = (await db.execute(
                select(AlertEvent).where(
                    and_(
                        AlertEvent.user_id == u.user_id,
                        AlertEvent.alert_type == "网络断开",
                        AlertEvent.handling_status == "待处理",
                    )
                ).limit(1)
            )).scalar_one_or_none()

            if existing is not None:
                # 已有待处理断开预警，不重复发
                continue

            alert = AlertEvent(
                user_id=u.user_id,
                alert_type="网络断开",
                alert_level="警告",
                trigger_source="rule",
                alert_time=datetime.now(timezone.utc),
                detail=f"老人 {u.nickname} 网络连接已断开（超过 {OFFLINE_THRESHOLD_SECONDS} 秒未收到心跳）",
                handling_status="待处理",
                notify_channels=[{"channel": "subscribe", "status": "pending"}],
            )
            db.add(alert)
            await db.flush()

            # 推送子女端
            await _notify_children(db, u, alert, "网络断开")

            count += 1
            logger.warning(
                "⚠️ 老人 %s(%s) 离线！最后心跳: %s",
                u.user_id, u.nickname, u.last_heartbeat_at,
            )

        await db.commit()
        return count


async def _notify_children(db, user: User, alert: AlertEvent, alert_type: str):
    """通知所有绑定子女。dev 模式仅打日志。"""
    from app.core.wx import send_subscribe_message

    relations = (await db.execute(
        select(UserChildRelation).where(UserChildRelation.user_id == user.user_id)
    )).scalars().all()

    template_code = "alert.warn" if alert_type == "网络断开" else "alert.handled"
    for rel in relations:
        child = await db.get(ChildUser, rel.child_id)
        if not child or not child.wx_account_id:
            continue
        acc = await db.get(WxAccount, child.wx_account_id)
        if not acc:
            continue
        try:
            await send_subscribe_message(
                openid=acc.openid,
                template_id=f"tpl_{template_code.replace('.', '_')}",
                data={
                    "thing1": {"value": user.nickname[:20]},
                    "thing2": {"value": alert_type},
                    "time3": {"value": alert.alert_time.strftime("%Y-%m-%d %H:%M")},
                    "thing4": {"value": alert.detail[:20]},
                },
            )
        except Exception as e:
            logger.warning("推送离线预警给子女 %s 失败: %s", rel.child_id, e)


async def clean_deleted_vectors():
    """清理软删记忆对应的 Chroma 向量，并清空 vector_id。

    每天扫描一次 is_deleted=1 且 vector_id 非空的 long_term_memory 记录，
    从 Chroma 中删除对应向量，然后置 vector_id=NULL。
    """
    async with AsyncSessionLocal() as db:
        stmt = select(LongTermMemory).where(
            LongTermMemory.is_deleted == 1,
            LongTermMemory.vector_id.is_not(None),
        ).limit(500)
        memories = (await db.execute(stmt)).scalars().all()

        if not memories:
            return 0

        count = 0
        try:
            from app.db.chroma import get_memory_collection
            collection = get_memory_collection()
            vids = [m.vector_id for m in memories]
            collection.delete(ids=vids)
            logger.info("Chroma 清理 %d 条已删除记忆的向量", len(vids))

            for m in memories:
                m.vector_id = None
                count += 1
            await db.commit()
        except Exception as e:
            logger.warning("Chroma 清理失败: %s", e)

        return count


async def run_loop():
    """定时任务主循环：离线检测（60s）+ 向量清理（3600s）。"""
    logger.info("=== 离线检测（%ds）+ 向量清理（%ds）任务启动 ===",
                SCAN_INTERVAL_SECONDS, VECTOR_CLEAN_INTERVAL_SECONDS)
    tick = 0
    import asyncio
    while True:
        try:
            n = await scan_offline_users()
            if n > 0:
                logger.info("本轮检测到 %d 位老人离线", n)

            tick += 1
            # 每 N 个 tick 跑一次向量清理
            if tick % (VECTOR_CLEAN_INTERVAL_SECONDS // SCAN_INTERVAL_SECONDS) == 0:
                nd = await clean_deleted_vectors()
                if nd > 0:
                    logger.info("清理 %d 条软删记忆的 Chroma 向量", nd)
        except Exception as e:
            logger.error("定时任务异常: %s", e, exc_info=True)
        await asyncio.sleep(SCAN_INTERVAL_SECONDS)


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_loop())
