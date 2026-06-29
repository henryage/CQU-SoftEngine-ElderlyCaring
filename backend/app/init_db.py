"""数据库初始化：建表 + 灌入 dev 种子数据。

用法：
    python -m app.init_db
"""
import asyncio
import logging
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.models import *  # noqa: F401,F403  注册所有模型
from app.models.user import AdminUser
from app.models.config import ApiConfig, PromptTemplate
from app.core.security import hash_password


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_all_tables():
    """根据模型自动建表（开发用，生产走 Alembic）。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✓ 所有表已创建（已存在的表跳过）")


async def seed_dev_data():
    """灌入 dev 种子数据：管理员、默认 API 配置、默认 Prompt。"""
    from sqlalchemy import select
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        # 管理员 admin/admin
        admin = (await db.execute(select(AdminUser).where(AdminUser.username == "admin"))).scalar_one_or_none()
        if admin is None:
            db.add(AdminUser(username="admin", password_hash=hash_password("admin"), role="SUPER"))
            logger.info("✓ 创建管理员 admin/admin")

        # 默认 API 配置
        api_cfg = (await db.execute(select(ApiConfig).where(ApiConfig.code == "default"))).scalar_one_or_none()
        if api_cfg is None:
            db.add(ApiConfig(
                code="default",
                name="默认大模型",
                endpoint=settings.llm_api_base,
                api_key_enc=settings.llm_api_key or "dev-placeholder",
                model=settings.llm_model,
                timeout=settings.llm_timeout,
                enabled=1,
                is_default=1,
            ))
            logger.info("✓ 创建默认 API 配置")

        # 默认 Prompt
        prompt = (await db.execute(select(PromptTemplate).where(PromptTemplate.code == "default"))).scalar_one_or_none()
        if prompt is None:
            db.add(PromptTemplate(
                code="default",
                name="默认系统提示词",
                content=(
                    "你是一只陪伴老人的棕色小猫助手，语气温暖、简洁、耐心。"
                    "老人可能视力不好、操作不熟练，回答要：1) 用短句；2) 重点信息前置；"
                    "3) 涉及药品/医疗时务必提醒『请遵医嘱』。"
                    "识别图片时优先描述老人最可能关心的信息（药品名、用法、保质期等）。"
                ),
                version="1.0",
                enabled=1,
            ))
            logger.info("✓ 创建默认 Prompt")

        await db.commit()


async def main():
    logger.info("=== 初始化数据库 ===")
    logger.info("DSN: %s", settings.mysql_dsn.replace(settings.mysql_password or "", "***") if settings.mysql_password else settings.mysql_dsn)
    await create_all_tables()
    if settings.is_dev:
        await seed_dev_data()
        logger.info("✓ dev 种子数据已灌入")
    logger.info("=== 初始化完成 ===")


if __name__ == "__main__":
    asyncio.run(main())
