"""图像预处理服务：基于 OpenCV + Pillow。

针对老年人手抖、视力衰退导致的图像模糊问题。

当前实现：
- Gamma 校正（亮度增强）：避免简单线性拉伸丢失细节，暗部提得多、亮部提得少

后续可扩展：
- CLAHE（自适应直方图均衡）：解决局部过暗/过曝
- Unsharp Masking（锐化）：提升文字边缘清晰度，利于 OCR
- Non-Local Means（降噪）：去除暗光拍照的 ISO 噪点
"""
import logging
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from app.core.config import settings, BACKEND_DIR


logger = logging.getLogger(__name__)

# 允许的图片扩展名
ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
# 单文件大小上限（10MB）
MAX_IMAGE_SIZE = 10 * 1024 * 1024


def get_upload_dir() -> Path:
    """获取上传目录（绝对路径），不存在则创建。"""
    # settings.upload_dir 是相对 backend 的路径，如 ./data/uploads
    upload_dir = BACKEND_DIR / "data" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def is_allowed_image(filename: str) -> bool:
    """检查文件扩展名是否允许。"""
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_IMAGE_EXTS


def enhance_image(
    src_path: Path,
    dst_path: Path,
    brightness: float = 1.3,
    denoise: bool = True,
    sharpen: bool = True,
) -> list[str]:
    """对图片执行增强处理。

    Args:
        src_path: 源图绝对路径
        dst_path: 输出图绝对路径
        brightness: 亮度增益，1.0=不变
        denoise: 是否降噪
        sharpen: 是否锐化

    Returns:
        执行的操作列表（用于响应记录）
    """
    operations: list[str] = []

    # 用 OpenCV 读图（BGR）
    img = cv2.imread(str(src_path))
    if img is None:
        # OpenCV 读不了，用 Pillow 兜底
        pil_img = Image.open(src_path).convert("RGB")
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    # 1. Gamma 校正（亮度增强）
    # brightness>1 时 gamma<1，图像变亮；暗部提得多、亮部提得少
    if brightness != 1.0:
        gamma = 1.0 / brightness if brightness > 0 else 1.0
        inv_gamma = 1.0 / max(gamma, 0.01)
        table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(256)]).astype("uint8")
        img = cv2.LUT(img, table)
        operations.append(f"gamma_{brightness}")

    # TODO: 后续补充
    # 2. CLAHE 自适应直方图均衡（局部对比度）
    # 3. Unsharp Masking 锐化（文字边缘增强）
    # 4. Non-Local Means 降噪（暗光噪点）

    # 写出
    cv2.imwrite(str(dst_path), img)
    logger.info("图像增强完成: %s -> %s, ops=%s", src_path.name, dst_path.name, operations)
    return operations


def get_image_size(path: Path) -> tuple[int, int] | None:
    """获取图片宽高。失败返回 None。"""
    try:
        with Image.open(path) as img:
            return img.size  # (width, height)
    except Exception:
        return None
