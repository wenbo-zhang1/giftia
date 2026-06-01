"""
LLM 客户端工厂模块

职责：
- 从 model_config.py 读取模型配置和特性
- 创建统一接口的 LLM 客户端

使用方式：
    from llm_config import get_llm_client
    client = get_llm_client(temperature=0.7)

切换模型：
    编辑 model_config.py 中的 CHAT_MODEL 和 CHAT_BASE_URL，
    如果模型有特殊参数需求（如 thinking），在 MODEL_PROFILES 中添加配置。
    系统自动从 .env 中找到匹配的 API key。
"""

from typing import Optional
from model_config import (
    CHAT_MODEL,
    CHAT_BASE_URL,
    get_chat_api_key,
    get_model_profile,
)


def _build_extra_body(profile: dict, use_thinking: bool) -> Optional[dict]:
    """根据模型特性配置构建 extra_body。
    
    extra_body 中的参数会被 openai SDK 展开到请求体顶层。
    """
    if not profile or not use_thinking:
        return None

    extra_body = {}
    
    # thinking 参数
    if "thinking" in profile:
        extra_body["thinking"] = profile["thinking"]
    
    # reasoning_effort（直接放在 extra_body 里）
    if "reasoning_effort" in profile:
        extra_body["reasoning_effort"] = profile["reasoning_effort"]
    
    # 其他需要放在 extra_body 的参数
    if "extra_body" in profile:
        extra_body.update(profile["extra_body"])
    
    return extra_body or None


def get_llm_client(
    temperature: float = 0.7,
    top_p: Optional[float] = None,
    use_thinking: bool = True,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    max_retries: int = 1,
):
    """创建 LLM 客户端。
    
    模型特性（如 thinking 参数）自动从 model_config.py 的 MODEL_PROFILES 中读取，
    无需修改此文件的代码。
    """
    from langchain_openai import ChatOpenAI

    target_model = model or CHAT_MODEL
    target_base_url = base_url or CHAT_BASE_URL
    target_api_key = api_key or get_chat_api_key()

    kwargs = {
        "model": target_model,
        "base_url": target_base_url,
        "api_key": target_api_key,
        "temperature": temperature,
        "max_retries": max_retries,
    }

    if top_p is not None:
        kwargs["top_p"] = top_p

    # 自动应用模型特性配置
    profile = get_model_profile(target_model)
    extra_body = _build_extra_body(profile, use_thinking)
    if extra_body:
        kwargs["extra_body"] = extra_body
        if "thinking" in extra_body or "enable_thinking" in extra_body:
            kwargs["temperature"] = 1.0
            kwargs.pop("top_p", None)

    return ChatOpenAI(**kwargs)