"""语音识别服务：faster-whisper 语音转文本。

模型：Whisper medium（~1.5GB，中文准确率高于 small）
本地存储：./data/whisper_models，首次下载后持久化。
下载镜像：HF_ENDPOINT → hf-mirror.com
"""
import logging
import os
from pathlib import Path

# 国内镜像（必须在导入 faster_whisper 之前设置）
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from faster_whisper import WhisperModel
from app.core.config import settings

logger = logging.getLogger(__name__)

_model: WhisperModel | None = None

MODEL_SIZE = "medium"          # tiny/small/medium/large-v3
DEVICE = "cpu"                 # 老人场景短句，CPU 够用
COMPUTE_TYPE = "int8"          # int8 量化，降内存
MODEL_DIR = settings.whisper_model_dir


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        os.makedirs(MODEL_DIR, exist_ok=True)
        logger.info("加载 faster-whisper %s (dir=%s)...", MODEL_SIZE, MODEL_DIR)
        _model = WhisperModel(
            MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE,
            download_root=MODEL_DIR,
        )
        logger.info("faster-whisper 就绪")
    return _model


def transcribe(audio_path: str | Path) -> str:
    audio_path = Path(audio_path)
    if not audio_path.exists():
        logger.error("语音文件不存在: %s", audio_path)
        return ""

    try:
        model = _get_model()
        segments, _ = model.transcribe(
            str(audio_path),
            language="zh",
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
        )
        result = "".join(seg.text.strip() for seg in segments)
        logger.info("语音转写完成: %d 字符", len(result))
        return result
    except Exception as e:
        logger.error("语音转写失败: %s", e, exc_info=True)
        return ""
