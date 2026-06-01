"""
模型配置中心
───────────
这个文件定义「用什么模型」和「模型特性」，.env 文件只负责「存 API key」。
系统会自动根据这里配置的 base_url 识别提供商，并从 .env 中找到对应的 API key。

切换模型只需改 CHAT_MODEL 和 CHAT_BASE_URL，
如果模型有特殊参数需求（如 thinking），在 MODEL_PROFILES 中添加配置即可。
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ================================================================
# 对话模型（改这里切换 LLM）
# ================================================================

CHAT_MODEL = "deepseek-v4-flash"
CHAT_BASE_URL = "https://api.deepseek.com/v1"

# ================================================================
# 模型特性配置（按名称匹配，新增模型只需在这里加一行）
# ================================================================

MODEL_PROFILES = {
    # 智谱 GLM 系列（支持 thinking）
    "glm-4.6v": {
        "thinking": {"type": "enabled"},
    },
    "glm-4.6v-flash": {
        "thinking": {"type": "enabled"},
    },
    "glm-4.6": {
        "thinking": {"type": "enabled"},
    },
    "glm-5.1": {
        "thinking": {"type": "enabled"},
    },
    # DeepSeek（支持 thinking，需要 extra_body）
    "deepseek": {
        "extra_body": {"thinking": {"type": "enabled"}},
        "reasoning_effort": "high",
    },
    # OpenAI（无特殊参数）
    "gpt-4o": {},
    "gpt-5.5": {},
    # Qwen（支持 thinking）
    "qwen": {
        "extra_body": {"enable_thinking": True, "return_reasoning": True},
    },
    # 其他模型（默认无特殊参数）
}

def get_model_profile(model_name: str) -> dict:
    """根据模型名称获取特性配置。
    
    精确匹配优先，如果找不到则尝试前缀匹配。
    例如："glm-4.6v-flash" 会先精确匹配，找不到则尝试 "glm-4.6v"、"glm" 等。
    """
    model_lower = model_name.lower()
    
    # 精确匹配
    if model_lower in MODEL_PROFILES:
        return MODEL_PROFILES[model_lower]
    
    # 前缀匹配（从长到短，优先匹配更长的前缀）
    for key in sorted(MODEL_PROFILES.keys(), key=len, reverse=True):
        if model_lower.startswith(key.lower()):
            return MODEL_PROFILES[key]
    
    # 默认无特殊参数
    return {}


# ================================================================
# Mem0 记忆配置
# ================================================================

MEM0_ENABLED = True

# ================================================================
# 嵌入模型（预留，Memo 云端模式下不需要配置）
# ================================================================

EMBED_MODEL = "embedding-3"
EMBED_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/embeddings"
EMBED_PROVIDER = "zhipu"

# ================================================================
# Provider → API Key 环境变量名映射
# ================================================================

PROVIDER_KEY_MAP = {
    "deepseek":    "DEEPSEEK_API_KEY",
    "openai":      "OPENAI_API_KEY",
    "zhipu":       "ZHIPU_API_KEY",
    "qwen":        "DASHSCOPE_API_KEY",
    "siliconflow": "SILICONFLOW_API_KEY",
}

_PROVIDER_KEY_ALIASES = {
    "DEEPSEEK_API_KEY": "Deepseek_API_KEY",
    "ZHIPU_API_KEY": "ZhipuAI_API_KEY",
}

# ================================================================
# Provider → 识别
# ================================================================

def detect_provider(model: str = CHAT_MODEL, base_url: str = CHAT_BASE_URL) -> str:
    model_lower = model.lower()
    url_lower = base_url.lower()

    if "deepseek" in model_lower or "deepseek" in url_lower:
        return "deepseek"
    elif "openai.com" in url_lower or model_lower.startswith(("gpt-", "o1", "o3")):
        return "openai"
    elif "bigmodel.cn" in url_lower or "zhipu" in model_lower or "glm" in model_lower:
        return "zhipu"
    elif "qwen" in model_lower or "dashscope" in url_lower:
        return "qwen"
    elif "siliconflow" in url_lower or "silicon" in model_lower:
        return "siliconflow"
    return "other"


def resolve_api_key(provider: str) -> str:
    if provider not in PROVIDER_KEY_MAP:
        raise ValueError(
            f"未找到 provider '{provider}' 对应的 API key 映射。\n"
            f"请在 model_config.py 的 PROVIDER_KEY_MAP 中添加。"
        )
    key_name = PROVIDER_KEY_MAP[provider]
    api_key = os.environ.get(key_name, "")
    if not api_key and key_name in _PROVIDER_KEY_ALIASES:
        api_key = os.environ.get(_PROVIDER_KEY_ALIASES[key_name], "")
    if not api_key:
        raise ValueError(
            f"未找到 API key '{key_name}'。\n"
            f"请在 .env 文件中设置 {key_name}=your_api_key"
        )
    return api_key


def get_chat_api_key() -> str:
    provider = detect_provider()
    return resolve_api_key(provider)


def get_mem0_api_key() -> str:
    api_key = os.environ.get("MEM0_API_KEY", "") or os.environ.get("mem0_API_KEY", "")
    if not api_key:
        raise ValueError("未找到 MEM0_API_KEY，请在 .env 文件中设置 MEM0_API_KEY=your_key")
    return api_key