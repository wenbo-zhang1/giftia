"""
预设模型配置库

提供常见模型的预设配置，用户只需选择模型并填写 API Key 即可使用。
"""


# 预设模型配置
PRESET_MODELS = {
    "DeepSeek（推荐）": {
        "model": "deepseek-v4-flash",
        "base_url": "https://api.deepseek.com/v1",
        "support_url": "https://platform.deepseek.com/api_keys",
        "support_text": "前往 DeepSeek 平台获取 API Key",
        "use_thinking": True,
    },
    "OpenAI": {
        "model": "gpt-4o",
        "base_url": "https://api.openai.com/v1",
        "support_url": "https://platform.openai.com/api-keys",
        "support_text": "前往 OpenAI 平台获取 API Key",
        "use_thinking": False,
    },
    "智谱 AI": {
        "model": "glm-5.1",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "support_url": "https://open.bigmodel.cn/usercenter/apikeys",
        "support_text": "前往智谱 AI 平台获取 API Key",
        "use_thinking": False,
    },
    "通义千问": {
        "model": "qwen-3.7plus",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "support_url": "https://bailian.console.aliyun.com/?apiKey=1#/api-key",
        "support_text": "前往阿里云百炼平台获取 API Key",
        "use_thinking": False,
    },
    "SiliconFlow": {
        "model": "Qwen/Qwen2.5-72B-Instruct",
        "base_url": "https://api.siliconflow.cn/v1",
        "support_url": "https://cloud.siliconflow.cn/account/ak",
        "support_text": "前往 SiliconFlow 平台获取 API Key（免费额度高）",
        "use_thinking": False,
    },
    "自定义": {
        "model": "",
        "base_url": "",
        "support_url": "",
        "support_text": "手动填写模型名称和 API Base URL",
        "use_thinking": False,
    },
}
