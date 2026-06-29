"""媒体路由：图片上传、图像增强、语音上传。

设计要点：
- 图片上传后存到 data/uploads/，返回相对 URL（/files/xxx）
- 增强接口接收原图 URL，输出增强后图 URL
- 文件名用 media_id 命名，避免冲突；保留原扩展名
- 静态文件挂载在 main.py 中通过 StaticFiles 实现
"""
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, status
from app.core.deps import AnyRole, ElderUser
from app.schemas.common import R
from app.schemas.media import ImageUploadOut, ImageEnhanceIn, ImageEnhanceOut, VoiceUploadOut
from app.services.image_processor import (
    enhance_image, get_upload_dir, is_allowed_image, get_image_size,
    ALLOWED_IMAGE_EXTS,
)
from app.services.speech_recognition import transcribe as asr_transcribe


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/media", tags=["media"])

# 允许的语音扩展名
ALLOWED_VOICE_EXTS = {".wav", ".mp3", ".m4a", ".aac", ".amr"}
MAX_VOICE_SIZE = 25 * 1024 * 1024  # 25MB（微信小程序录音上限）


@router.post(
    "/upload/image",
    response_model=R,
    summary="上传图片",
    description="""
上传图片文件（老人端拍照/相册选择后调用）。

**支持的格式**：jpg / jpeg / png / bmp / webp
**大小限制**：10MB
**权限**：老人端 / 子女端均可（子女端上传老人图片做对比等场景）

**返回**：media_id + 原图 URL + **增强后图 URL**（上传即 Gamma 增强，后续 QA 直接传 enhanced_url）
""".strip(),
    response_description="上传成功，返回 media_id 与 URL",
    responses={
        200: {"description": "上传成功"},
        400: {"description": "文件格式不支持 / 文件过大", "content": {"application/json": {"example": {"detail": "不支持的图片格式：.gif"}}}},
        401: {"description": "未认证"},
        422: {"description": "未上传文件"},
    },
)
async def upload_image(file: UploadFile = File(..., description="图片文件"), cur: AnyRole = None):
    # 校验扩展名
    if not file.filename or not is_allowed_image(file.filename):
        ext = Path(file.filename or "").suffix.lower() if file.filename else "无"
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"不支持的图片格式：{ext}，仅支持 {sorted(ALLOWED_IMAGE_EXTS)}")

    # 读取内容
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "图片大小不能超过 10MB")
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "文件内容为空")

    # 生成 media_id 与存储路径
    ext = Path(file.filename).suffix.lower()
    media_id = f"img_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    filename = f"{media_id}{ext}"
    upload_dir = get_upload_dir()
    dst_path = upload_dir / filename

    # 写文件
    with open(dst_path, "wb") as f:
        f.write(content)

    # 上传即增强：默认 Gamma 校正
    enhanced_filename = f"{media_id}_enhanced{ext}"
    enhanced_path = upload_dir / enhanced_filename
    ops = enhance_image(src_path=dst_path, dst_path=enhanced_path, brightness=1.3, denoise=False, sharpen=False)

    # 获取宽高
    size = get_image_size(dst_path)
    width, height = (size[0], size[1]) if size else (None, None)

    out = ImageUploadOut(
        media_id=media_id,
        url=f"/files/{filename}",
        enhanced_url=f"/files/{enhanced_filename}",
        filename=file.filename,
        size=len(content),
        width=width,
        height=height,
        operations=ops,
        uploaded_at=datetime.now(timezone.utc),
    )
    logger.info("图片上传成功: %s (%d bytes) by account=%s", filename, len(content), cur.account_id if cur else "anonymous")
    return R.ok(out.model_dump(mode="json"))


@router.post(
    "/image/enhance",
    response_model=R,
    summary="图像增强（手动调参）",
    description="""
对已上传图片手动执行 Gamma 校正增强。

**注意**：上传图片时已自动增强（默认 gamma=1.3），一般不需要调此接口。
仅在需要不同亮度参数时使用。

**参数**：
- brightness：Gamma 校正系数。1.0=原图，>1增亮（老人拍照暗建议 1.3-1.5），<1 变暗
""".strip(),
    response_description="增强成功，返回原图与增强后图 URL",
    responses={
        200: {"description": "增强成功"},
        400: {"description": "原图不存在"},
        401: {"description": "未认证"},
        404: {"description": "原图文件未找到", "content": {"application/json": {"example": {"detail": "原图文件未找到：/files/xxx.jpg"}}}},
    },
)
async def enhance_image_endpoint(payload: ImageEnhanceIn, cur: AnyRole):
    # 从 URL 解析出文件名
    filename = payload.url.replace("/files/", "").lstrip("/")
    upload_dir = get_upload_dir()
    src_path = upload_dir / filename

    if not src_path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"原图文件未找到：{payload.url}")

    # 输出文件名
    ext = src_path.suffix.lower()
    enhanced_filename = f"{src_path.stem}_enhanced{ext}"
    dst_path = upload_dir / enhanced_filename

    # 执行增强
    try:
        operations = enhance_image(
            src_path=src_path,
            dst_path=dst_path,
            brightness=payload.brightness,
            denoise=False,
            sharpen=False,
        )
    except Exception as e:
        logger.error("图像增强失败: %s", e, exc_info=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"图像增强处理失败：{e}")

    out = ImageEnhanceOut(
        original_url=payload.url,
        enhanced_url=f"/files/{enhanced_filename}",
        operations=operations,
    )
    return R.ok(out.model_dump())


@router.post(
    "/upload/voice",
    response_model=R,
    summary="上传语音并转写为文本",
    description="""
上传语音文件（老人端录音后调用），**上传即转写**。

**流程**：
1. 接收语音文件（wav/mp3/m4a/aac/amr，最大 25MB）
2. 存储到 data/uploads/
3. 自动调用 faster-whisper 转写为中文文本
4. 返回 media_id + URL + **asr_text（转写文本）**

**支持的格式**：wav / mp3 / m4a / aac / amr
**大小限制**：25MB（微信小程序录音上限）
**权限**：老人端 / 子女端均可

**返回**：media_id + URL + asr_text，后续调 `/qa/ask` 时用 asr_text 做文本问答。
""".strip(),
    response_description="上传成功，返回 media_id 与 URL",
    responses={
        200: {"description": "上传成功"},
        400: {"description": "文件格式不支持 / 文件过大"},
        401: {"description": "未认证"},
        422: {"description": "未上传文件"},
    },
)
async def upload_voice(file: UploadFile = File(..., description="语音文件"), cur: AnyRole = None):
    if not file.filename:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "文件名为空")
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_VOICE_EXTS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"不支持的语音格式：{ext}，仅支持 {sorted(ALLOWED_VOICE_EXTS)}")

    content = await file.read()
    if len(content) > MAX_VOICE_SIZE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"语音大小不能超过 {MAX_VOICE_SIZE // 1024 // 1024}MB")
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "文件内容为空")

    media_id = f"voice_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    filename = f"{media_id}{ext}"
    upload_dir = get_upload_dir()
    dst_path = upload_dir / filename

    with open(dst_path, "wb") as f:
        f.write(content)

    # 语音转写（faster-whisper）
    asr_text = ""
    try:
        asr_text = asr_transcribe(dst_path)
        logger.info("语音转写完成: %s → %s", filename, asr_text[:50])
    except Exception as e:
        logger.warning("语音转写失败（继续上传）: %s", e)

    out = VoiceUploadOut(
        media_id=media_id,
        url=f"/files/{filename}",
        filename=file.filename,
        size=len(content),
        duration_sec=None,
        asr_text=asr_text,
        uploaded_at=datetime.now(timezone.utc),
    )
    logger.info("语音上传成功: %s (%d bytes)", filename, len(content))
    return R.ok(out.model_dump(mode="json"))
