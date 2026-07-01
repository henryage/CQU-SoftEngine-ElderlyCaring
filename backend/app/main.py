"""FastAPI 应用入口。

启动：uvicorn app.main:app --reload --port 8000
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings, BACKEND_DIR
from app.api.v1 import api_router


logging.basicConfig(
    level=logging.DEBUG if settings.app_debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动与关闭。"""
    logger.info("=== %s 启动 ===", settings.app_name)
    logger.info("env=%s dev_mode=%s", settings.app_env, settings.is_dev)
    if settings.is_dev:
        logger.warning("⚠️  开发模式：微信登录/订阅消息均为 mock，不可用于生产")
        logger.info("dev 管理员创建：GET /api/v1/auth/dev/create-admin（admin/admin）")
        logger.info("dev 老人登录：POST /api/v1/auth/wx-login {\"code\":\"任意字符串\",\"user_type\":\"user\"}")
        logger.info("dev 子女登录：POST /api/v1/auth/wx-login {\"code\":\"任意字符串\",\"user_type\":\"child\"}")
    # 初始化 Chroma
    try:
        from app.db.chroma import get_memory_collection
        get_memory_collection()
        logger.info("Chroma 向量库已就绪: %s", settings.chroma_persist_path)
    except Exception as e:
        logger.error("Chroma 初始化失败: %s", e)

    # 启动后台定时任务（离线检测 + 向量清理）
    from app.tasks.monitor import run_loop as background_tasks
    monitor_task = asyncio.create_task(background_tasks())
    logger.info("后台任务已启动（离线检测 60s + 向量清理 3600s）")

    yield

    # 关离线检测
    monitor_task.cancel()
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass
    logger.info("=== %s 关闭 ===", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    description="""
# 模糊视觉辅助问答系统后端

面向老年人关爱场景的多模态辅助智能问答系统，前端为微信小程序（老人端 + 子女端）+ Web 控制台。

## 技术栈
- **框架**：FastAPI 0.115（异步）
- **数据库**：MySQL 8.0 + SQLAlchemy 2.0（async）
- **向量库**：Chroma（RAG 知识库 = 长期记忆）
- **图像处理**：OpenCV-headless + Pillow
- **鉴权**：微信 wx.login + JWT（Access 30min + Refresh 7d）+ RBAC

## 三角色
| 角色 | user_type | 端 | 说明 |
|------|-----------|-----|------|
| 老人 | `user` | 微信小程序·老人端 | 多模态问答、用药提醒、紧急呼叫 |
| 子女 | `child` | 微信小程序·子女端 | 看板、配置下发、预警处置 |
| 管理员 | `admin` | Web 控制台 | 用户/记忆/审计运维 |

## 统一响应格式
所有业务接口返回 `R` 包装：
```json
{"code": 0, "msg": "ok", "data": {...}}
```
- `code=0` 表示成功，非 0 表示业务错误
- HTTP 异常（401/403/404/422/500）返回 `{"detail": "..."}`

## 鉴权
除 `/auth/wx-login`、`/auth/refresh`、`/auth/admin-login`、`/auth/dev/create-admin`、`/health`、`/info` 外，
所有接口需在 Header 携带 `Authorization: Bearer <token>`。

## dev 模式说明
当前 `DEV_MODE=true`，以下能力降级：
- 微信登录：code 传任意字符串即可，不调微信
- 订阅消息推送：仅打日志，不真实推送
- 手机号绑定：直接传手机号，不走微信解密
""".strip(),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=[
        {"name": "system", "description": "系统健康检查与信息"},
        {"name": "auth", "description": "鉴权与身份：微信登录、token 刷新、管理员登录、订阅授权、老人端心跳"},
        {"name": "media", "description": "媒体上传与图像预处理：图片上传、OpenCV 增强、语音上传"},
        {"name": "qa", "description": "智能问答：多模态提问、流式回答、合规拦截、预警触发、历史查询"},
        {"name": "memory", "description": "长期记忆（RAG知识库）：CRUD、语义检索、Chroma向量库"},
        {"name": "alert", "description": "预警：老人端紧急呼叫、子女端处置（后续扩展）"},
        {"name": "reminder", "description": "用药提醒：老人端查看、子女端配置（后续扩展）"},
        {"name": "child", "description": "子女端：绑定老人、健康看板、问答下钻、适老化配置下发"},
        {"name": "comm", "description": "通信：子女→老人留言（后续扩展语音/问候）"},
        {"name": "admin", "description": "管理端：用户/子女/审计日志/订阅模板管理"},
    ],
    lifespan=lifespan,
)

# 全局异常捕获
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("未处理异常 [%s %s]: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": str(exc)})

# CORS
origins = ["*"] if settings.cors_origins == "*" else settings.cors_origins.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载路由
app.include_router(api_router, prefix=settings.app_prefix)

# 挂载静态文件（让 /files/xxx 能访问上传的图片/语音）
upload_dir = BACKEND_DIR / "data" / "uploads"
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/files", StaticFiles(directory=str(upload_dir)), name="files")


@app.get(
    "/",
    summary="根路径",
    description="返回应用名、版本、文档地址，无需鉴权。",
    response_description="应用基本信息",
)
async def root():
    return {
        "app": settings.app_name,
        "version": "0.1.0",
        "docs": "/docs",
        "api": settings.app_prefix,
    }
