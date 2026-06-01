import base64
import io
from typing import Optional, Tuple

try:
    from PIL import Image
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

ALLOWED_IMAGE_TYPES = ["jpg", "jpeg", "png", "gif", "webp"]

_MULTIMODAL_KEYWORDS = [
    "gpt-4o",
    "gpt-4v",
    "gpt-4-turbo",
    "gpt-4.1",
    "gpt-4.5",
    "gpt-5",
    "vision",
    "claude",
    "gemini",
    "gemma",
    "llava",
    "qwen-vl",
    "qwen2.5-vl",
    "qwen2-vl",
    "qwen3-plus",
    "qwen3-max",
    "qwen3-omni",
    "qwen3.5-plus",
    "qwen3.6-plus",
    "qwen3.7-plus",
    "qwen3.5-max",
    "qwen3.6-max",
    "qwen3.7-max",
    "qwen3.5-omni",
    "qwen-3plus",
    "qwen-3max",
    "qwen-3omni",
    "qwen-3.5plus",
    "qwen-3.6plus",
    "qwen-3.7plus",
    "qwen-3.5max",
    "qwen-3.6max",
    "qwen-3.7max",
    "qwen-3.5omni",
    "glm-4.6v",
    "glm-5v-Turbo",
    "cogvlm",
    "cogview",
    "yi-vision",
    "pixtral",
    "llama-3.2-vision",
    "llama-4",
    "internvl",
    "internlm-xcomposer",
    "minicpm-v",
    "deepseek-vl",
    "deepseek-chat",
    "o1",
    "o3",
    "o4",
    "KIMI-2.5",
    "KIMI-2.6"
]


def is_multimodal_model(model_name: str = "") -> bool:
    from model_config import CHAT_MODEL

    if not model_name:
        model_name = CHAT_MODEL

    if not model_name:
        return False

    model_lower = model_name.lower()

    for keyword in _MULTIMODAL_KEYWORDS:
        if keyword in model_lower:
            return True

    return False


def _process_image(image_bytes: bytes, filename: str = "") -> Tuple[Optional[bytes], Optional[str], Optional[str]]:
    """
    图片预处理：验证格式、校验完整性、缩放大图。

    返回:
        (processed_bytes, mime_type, error)
    """
    if not _PIL_AVAILABLE:
        return None, None, "Pillow 库未安装，无法处理图片"

    ext = ""
    if filename:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ALLOWED_IMAGE_TYPES:
        return None, None, f"不支持的图片格式：.{ext}，支持：{', '.join(ALLOWED_IMAGE_TYPES)}"

    mime_map = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
    }
    mime_type = mime_map.get(ext, "image/png")

    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.verify()
    except Exception:
        return None, None, "图片文件损坏或格式无效，请重新选择"

    try:
        img = Image.open(io.BytesIO(image_bytes))
        max_size = 4096
        w, h = img.size
        if w > max_size or h > max_size:
            ratio = min(max_size / w, max_size / h)
            new_w, new_h = int(w * ratio), int(h * ratio)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            buffer = io.BytesIO()
            img_format = ext.upper() if ext != "jpg" else "JPEG"
            img.save(buffer, format=img_format)
            image_bytes = buffer.getvalue()

        if len(image_bytes) > 20 * 1024 * 1024:
            return None, None, "图片文件过大（超过 20MB），请压缩后重试"
    except Exception as e:
        return None, None, f"图片处理失败：{e}"

    return image_bytes, mime_type, None


def image_to_base64_data_url(image_bytes: bytes, filename: str = "") -> Tuple[Optional[str], Optional[str]]:
    processed, mime_type, error = _process_image(image_bytes, filename)
    if error:
        return None, error

    b64 = base64.b64encode(processed).decode("utf-8")
    data_url = f"data:{mime_type};base64,{b64}"
    return data_url, None


def image_to_base64_raw(image_bytes: bytes, filename: str = "") -> Tuple[Optional[str], Optional[str]]:
    processed, _, error = _process_image(image_bytes, filename)
    if error:
        return None, error

    b64 = base64.b64encode(processed).decode("utf-8")
    return b64, None


def get_image_support_message(model_name: str = "") -> str:
    if is_multimodal_model(model_name):
        return ""
    return "当前模型不支持图片上传"
