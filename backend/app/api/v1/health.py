"""健康检查与系统信息路由。"""
from fastapi import APIRouter
from app.core.config import settings
from app.schemas.common import R


router = APIRouter(tags=["system"])


@router.get(
    "/health",
    response_model=R,
    summary="健康检查",
    description="""
服务存活探针，**无需鉴权**。

用于负载均衡 / K8s liveness probe / 监控系统定期探测服务是否在线。
返回服务名、环境、dev 模式开关等基础信息。
""".strip(),
    response_description="服务状态",
    responses={
        200: {
            "description": "服务在线",
            "content": {"application/json": {"example": {
                "code": 0, "msg": "ok",
                "data": {"status": "up", "app": "模糊视觉辅助问答系统后端", "env": "dev", "dev_mode": True},
            }}},
        },
    },
)
async def health():
    return R.ok({
        "status": "up",
        "app": settings.app_name,
        "env": settings.app_env,
        "dev_mode": settings.is_dev,
    })


@router.get(
    "/info",
    response_model=R,
    summary="系统信息",
    description="""
返回系统基本信息，**无需鉴权**。

包含应用名、环境、API 前缀、文档地址等，便于前端初始化时探测。
""".strip(),
    response_description="系统信息",
    responses={
        200: {
            "description": "系统信息",
            "content": {"application/json": {"example": {
                "code": 0, "msg": "ok",
                "data": {
                    "app": "模糊视觉辅助问答系统后端",
                    "env": "dev",
                    "dev_mode": True,
                    "api_prefix": "/api/v1",
                    "docs": "/docs",
                    "redoc": "/redoc",
                },
            }}},
        },
    },
)
async def info():
    return R.ok({
        "app": settings.app_name,
        "env": settings.app_env,
        "dev_mode": settings.is_dev,
        "api_prefix": settings.app_prefix,
        "docs": "/docs",
        "redoc": "/redoc",
    })
