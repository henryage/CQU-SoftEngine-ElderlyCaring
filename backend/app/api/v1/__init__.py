"""聚合所有 v1 路由。"""
from fastapi import APIRouter
from app.api.v1 import admin, alert, auth, child, comm, health, media, memory, qa, reminder


api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(media.router)
api_router.include_router(qa.router)
api_router.include_router(memory.router)
api_router.include_router(alert.router)
api_router.include_router(reminder.router)
api_router.include_router(comm.router)
api_router.include_router(child.router)
api_router.include_router(admin.router)
