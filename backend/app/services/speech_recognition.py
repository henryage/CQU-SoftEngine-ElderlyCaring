"""语音识别服务：基于 faster-whisper 将语音文件转写为文本。

模型：Whisper small（~500MB），中文识别准确率高，CPU 可用。
首次调用自动下载模型到本地缓存，后续调用直接加载。

调用方式：
    from app.services.speech_recognition import transcribe
    text = transcribe("/path/to/audio.wav")
"""
import logging
from pathlib import Path
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

# 模型单例
_model: WhisperModel | None = None

# 模型大小：tiny(150MB) / small(500MB) / medium(1.5GB) / large(3GB)
# small 在中文老人场景（短句提问）足够，CPU 可行
MODEL_SIZE = "small"
# 计算设备：cuda / cpu / auto
DEVICE = "cpu"
# 推理精度：int8 降低内存占用，CPU 推荐
COMPUTE_TYPE = "int8"


def _get_model() -> WhisperModel:
    """获取模型单例，首次调用时下载。"""
    global _model
    if _model is None:
        logger.info("正在加载 faster-whisper 模型（%s/%s），首次下载需几十秒...", MODEL_SIZE, DEVICE)
        _model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
        logger.info("faster-whisper 模型加载完成")
    return _model


def transcribe(audio_path: str | Path) -> str:
    """将语音文件转写为文本。

    Args:
        audio_path: 语音文件绝对路径，支持 wav/mp3/m4a/aac 等格式

    Returns:
        转写后的文本字符串，失败返回空字符串
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        logger.error("语音文件不存在: %s", audio_path)
        return ""

    try:
        model = _get_model()
        segments, _ = model.transcribe(
            str(audio_path),
            language="zh",           # 指定中文，提升准确率
            beam_size=5,             # beam search 宽度
            vad_filter=True,         # 过滤静音段
            vad_parameters={"min_silence_duration_ms": 500},
        )
        text_parts = [seg.text.strip() for seg in segments]
        result = "".join(text_parts)
        logger.info("语音转写完成: %d 字符 → %s", len(result), audio_path.name)
        return result
    except Exception as e:
        logger.error("语音转写失败: %s", e, exc_info=True)
        return ""
