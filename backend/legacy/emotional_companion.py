"""
AI 情感陪伴助手 - 基于 Mem0 长期记忆 + DeepSeek 大模型

功能：
- 长期记忆：使用 Mem0 + Qdrant 本地向量存储，自动提取关键事实
- 短期记忆：保留最近 10 轮对话上下文
- 情感陪伴：温暖、共情的对话风格，能自然引用记忆

运行前请确保已安装依赖：
    pip install mem0ai openai python-dotenv
"""

import os
import sys
from typing import List, Dict
from dotenv import load_dotenv
from llm_config import get_llm_client
from mem0 import MemoryClient

load_dotenv()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 【第一部分】配置项（集中管理，从环境变量读取）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Mem0 配置（用于长期记忆，MemoryClient 需要 MEM0_API_KEY）
MEM0_API_KEY = os.environ.get("mem0_API_KEY", "")

# Embedder 配置（智谱嵌入模型）
MEM0_EMBEDDER_MODEL = os.environ.get("MEM0_EMBEDDER_MODEL", "embedding-3")
MEM0_EMBEDDER_API_KEY = os.environ.get("ZhipuAI_API_KEY", "")
MEM0_EMBEDDER_BASE_URL = os.environ.get("MEM0_EMBEDDER_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/embeddings")

# 对话模型配置（用于主对话）
CHAT_MODEL = os.environ.get("LLM_MODEL", "deepseek-v4-flash")
CHAT_API_KEY = os.environ.get("LLM_API_KEY", "") or os.environ.get("Deepseek_API_KEY", "")
CHAT_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1")

# 用户与记忆配置
USER_ID = os.environ.get("MEM0_USER_ID", "demo_user_001")
MAX_HISTORY_ROUNDS = int(os.environ.get("MAX_HISTORY_ROUNDS", "10"))
MEM0_LOCAL_DB_PATH = os.environ.get("MEM0_LOCAL_DB_PATH", "./mem0_local_db")

# 系统提示词
SYSTEM_PROMPT = """你是一个温暖、善解人意的情感陪伴助手。
你的特点是：
1. 善于倾听和共情，回应用户的情感需求
2. 自然地记住和引用用户之前提到的事情，但不要太生硬
3. 提供情感支持和建设性建议，但不替代专业心理咨询
4. 语言温暖、自然、真诚，像朋友一样交流
5. 如果用户提到之前说过的事情，你可以自然地跟进（"上次你说...最近怎么样？"）
6. 保持适度的幽默感，但不要过度

记住：你是一个陪伴者，不是医生或治疗师。如果用户表现出严重的心理困扰，
请温柔地建议寻求专业帮助。"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 【第二部分】初始化组件
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def init_mem0() -> MemoryClient:
    """
    初始化 Mem0 客户端，使用官方 API Key 方式。
    
    Mem0 会自动：
    1. 从对话中提取关键事实
    2. 向量化存储
    3. 根据查询检索相关记忆
    """
    api_key = os.environ.get("mem0_API_KEY", "")
    if not api_key:
        raise ValueError("请设置 mem0_API_KEY 环境变量")
    
    client = MemoryClient(api_key=api_key)
    return client


def init_chat_client():
    """
    初始化 LLM 客户端，用于与大模型对话。
    模型配置通过环境变量自动读取（LLM_MODEL, LLM_API_KEY, LLM_BASE_URL）。
    """
    return get_llm_client(temperature=0.7)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 【第三部分】记忆操作函数
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def search_memories(memory: MemoryClient, query: str, user_id: str, limit: int = 5) -> List[Dict]:
    """
    根据用户输入从 Mem0 检索相关历史记忆。
    
    参数：
    - query: 当前用户输入（用于向量检索）
    - user_id: 用户 ID，用于过滤该用户的记忆
    - limit: 最多返回的记忆数量
    
    返回：
    - 相关记忆列表，每项包含记忆内容和元数据
    """
    try:
        results = memory.search(query=query, user_id=user_id, limit=limit)
        if results and "results" in results:
            return results["results"]
        return []
    except Exception as e:
        print(f"\n⚠️ 记忆检索失败: {e}")
        return []


def add_memories(memory: MemoryClient, user_msg: str, assistant_msg: str, user_id: str):
    """
    将本轮对话存入 Mem0，由 Mem0 自动提取关键事实。
    
    Mem0 会自动：
    1. 从对话中提取事实（如用户喜欢猫、用户是程序员等）
    2. 向量化存储，关联到 user_id
    3. 去重和更新已有记忆
    
    参数：
    - user_msg: 用户消息
    - assistant_msg: 助手回复
    - user_id: 用户 ID
    """
    try:
        memory.add(
            messages=[
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": assistant_msg},
            ],
            user_id=user_id,
        )
    except Exception as e:
        print(f"\n⚠️ 记忆存储失败: {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 【第四部分】上下文构建函数
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def build_context(
    user_msg: str,
    user_id: str,
    memory: MemoryClient,
    short_history: List[Dict],
    max_memories: int = 5
) -> List[Dict]:
    """
    构建完整的 messages 列表，包含：
    1. 系统提示词
    2. 相关历史记忆（从 Mem0 检索）
    3. 短期对话历史（最近 N 轮）
    4. 当前用户消息
    
    参数：
    - user_msg: 当前用户输入
    - user_id: 用户 ID
    - memory: Mem0 实例
    - short_history: 短期对话历史列表
    - max_memories: 最多引用的记忆数量
    
    返回：
    - 完整的 messages 列表，可直接传给 LLM
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    
    # 1. 检索相关记忆
    memories = search_memories(memory, user_msg, user_id, limit=max_memories)
    
    if memories:
        # 将记忆格式化为自然语言，添加到系统提示中
        memory_texts = []
        for i, mem in enumerate(memories):
            mem_text = mem.get("memory", "")
            if mem_text:
                memory_texts.append(f"- {mem_text}")
        
        if memory_texts:
            memory_context = (
                "以下是关于这位用户的一些背景信息（从之前的对话中提取），"
                "你可以在回复中自然地引用：\n" + "\n".join(memory_texts)
            )
            messages.append({"role": "system", "content": memory_context})
            
            # 可视化提示
            print(f"\n🧠 回忆中: {len(memories)} 条相关记忆")
            for mem in memories:
                print(f"   • {mem.get('memory', '')[:80]}")
    
    # 2. 添加短期对话历史（最近 N 轮）
    for msg in short_history:
        messages.append(msg)
    
    # 3. 添加当前用户消息
    messages.append({"role": "user", "content": user_msg})
    
    return messages


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 【第五部分】LLM 调用函数
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def call_lllm(client, messages: List[Dict], model: str = None) -> str:
    """
    调用大模型获取回复，包含异常处理。
    
    参数：
    - client: LLM 客户端
    - messages: 完整的消息列表
    - model: 模型名称（可选）
    
    返回：
    - 助手回复文本
    """
    try:
        response = client.invoke(messages)
        return response.content.strip()
    except Exception as e:
        error_msg = f"LLM 调用失败: {e}"
        print(f"\n❌ {error_msg}")
        return f"抱歉，我暂时遇到了一些技术问题，请稍后再试。({error_msg})"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 【第六部分】主对话循环
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def chat_loop():
    """
    主对话循环：
    1. 接收用户输入
    2. 检索长期记忆
    3. 构建完整上下文
    4. 调用 LLM 获取回复
    5. 更新短期历史
    6. 存储长期记忆
    """
    print("=" * 70)
    print("🤗 AI 情感陪伴助手")
    print("   我会随时陪着你。")
    print("   输入 'quit' 退出，'history' 查看所有记忆，'clear' 清空记忆。")
    print("=" * 70)
    
    # 初始化组件
    print("\n🔧 正在初始化组件...")
    
    try:
        memory = init_mem0()
        print("  ✅ Mem0 记忆库初始化成功")
    except Exception as e:
        print(f"  ❌ Mem0 初始化失败: {e}")
        print("  请检查配置项是否正确，以及依赖是否已安装。")
        sys.exit(1)
    
    try:
        client = init_chat_client()
        print("  ✅ 对话模型初始化成功")
    except Exception as e:
        print(f"  ❌ 对话模型初始化失败: {e}")
        print("  请检查 CHAT_API_KEY 和 CHAT_BASE_URL 是否正确。")
        sys.exit(1)
    
    print(f"\n👤 用户 ID: {USER_ID}")
    print("=" * 70)
    
    # 短期记忆（保留最近 N 轮对话）
    short_history: List[Dict] = []
    
    while True:
        print()
        user_msg = input("💬 你说: ").strip()
        
        # 退出命令
        if user_msg.lower() in ("quit", "exit", "q"):
            print("\n拜拜！下次再见。")
            break
        
        # 查看所有记忆命令
        if user_msg.lower() in ("history", "memories"):
            try:
                results = memory.get_all(user_id=USER_ID)
                if results and "results" in results and results["results"]:
                    print(f"\n📚 关于你的记忆（共 {len(results['results'])} 条）:")
                    for i, mem in enumerate(results["results"], 1):
                        print(f"   {i}. {mem.get('memory', '')}")
                else:
                    print("\n📚 还没有关于你的记忆。多聊聊天，我就会记住你啦！")
            except Exception as e:
                print(f"\n⚠️ 获取记忆失败: {e}")
            continue
        
        # 清空记忆命令
        if user_msg.lower() in ("clear", "reset"):
            try:
                memory.delete_all(user_id=USER_ID)
                short_history.clear()
                print("\n🗑️ 已清空所有记忆和历史记录。")
            except Exception as e:
                print(f"\n⚠️ 清空记忆失败: {e}")
            continue
        
        # 跳过空输入
        if not user_msg:
            continue
        
        print()
        
        # 1. 构建完整上下文（检索记忆 + 短期历史）
        messages = build_context(user_msg, USER_ID, memory, short_history)
        
        # 2. 调用 LLM 获取回复
        print("  💭 思考中...", end="", flush=True)
        assistant_reply = call_lllm(client, messages)
        print(" ✅")
        
        # 3. 打印助手回复
        print(f"\n🤗 我说: {assistant_reply}")
        
        # 4. 更新短期历史
        short_history.append({"role": "user", "content": user_msg})
        short_history.append({"role": "assistant", "content": assistant_reply})
        
        # 保持短期历史在最大轮数以内（每轮 = 1 用户 + 1 助手）
        max_history_messages = MAX_HISTORY_ROUNDS * 2
        if len(short_history) > max_history_messages:
            short_history = short_history[-max_history_messages:]
        
        # 5. 存储长期记忆（异步提取关键事实）
        add_memories(memory, user_msg, assistant_reply, USER_ID)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 【主程序】
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    # 确保控制台输出为 UTF-8（Windows 兼容）
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    
    # 检查必要的 API Key 是否已配置
    if not MEM0_API_KEY or not CHAT_API_KEY:
        print("⚠️ 请先在 .env 文件中配置以下 API Key:")
        print("   - mem0_API_KEY")
        print("   - LLM_API_KEY")
        sys.exit(1)
    
    chat_loop()
