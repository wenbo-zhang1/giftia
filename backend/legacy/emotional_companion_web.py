"""
小忆 - AI 情感陪伴助手（Gradio 网页版）

功能：
- 长期记忆：使用 Mem0 记忆平台，自动提取关键事实
- 短期记忆：保留最近 10 轮对话上下文
- 情感陪伴：温暖、共情的对话风格，能自然引用记忆
- 多用户隔离：不同 user_id 的记忆互相独立

运行前请确保已安装依赖：
    pip install mem0ai langchain-openai python-dotenv gradio
"""

import os
import sys
import threading
import webbrowser
from typing import List, Dict, Tuple
from dotenv import load_dotenv
from llm_config import get_llm_client
from mem0 import MemoryClient
import gradio as gr

load_dotenv()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 【第一部分】配置项（集中管理，从环境变量读取）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Mem0 配置（用于长期记忆）
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
DEFAULT_USER_ID = "web_user_001"
MAX_HISTORY_ROUNDS = 10

# 系统提示词
SYSTEM_PROMPT = """你是一个温暖、善解人意的情感陪伴助手，名叫"小忆"。
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
# 【第二部分】初始化全局组件
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def init_mem0() -> MemoryClient:
    """初始化 Mem0 客户端。"""
    api_key = os.environ.get("mem0_API_KEY", "")
    if not api_key:
        raise ValueError("请设置 mem0_API_KEY 环境变量")
    return MemoryClient(api_key=api_key)


def init_chat_client():
    """初始化 LLM 客户端。"""
    return get_llm_client(temperature=0.7)


# 全局初始化（避免每次请求重复创建）
mem0_client = init_mem0()
chat_client = init_chat_client()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 【第三部分】记忆操作函数
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def search_memories(query: str, user_id: str, limit: int = 5) -> List[Dict]:
    """根据用户输入从 Mem0 检索相关历史记忆。"""
    try:
        results = mem0_client.search(
            query=query,
            user_id=user_id,
            limit=limit
        )
        if results:
            return results if isinstance(results, list) else results.get("results", [])
        return []
    except Exception as e:
        print(f"⚠️ 记忆检索失败: {e}")
        return []


def add_memories(user_msg: str, assistant_msg: str, user_id: str):
    """将本轮对话存入 Mem0，由 Mem0 自动提取关键事实。"""
    try:
        mem0_client.add(
            messages=[
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": assistant_msg},
            ],
            user_id=user_id,
        )
    except Exception as e:
        print(f"⚠️ 记忆存储失败: {e}")


def clear_user_memories(user_id: str) -> str:
    """清空指定用户的所有记忆。"""
    try:
        mem0_client.delete_all(user_id=user_id)
        return f"✅ 已清除用户「{user_id}」的所有记忆"
    except Exception as e:
        return f"❌ 清除记忆失败: {e}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 【第四部分】对话核心逻辑
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def build_messages(user_msg: str, user_id: str, history: List[Dict], max_memories: int = 5) -> List[Dict]:
    """
    构建完整的 messages 列表，包含：
    1. 系统提示词
    2. 相关历史记忆（从 Mem0 检索）
    3. 短期对话历史（最近 N 轮）
    4. 当前用户消息
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    # 1. 检索相关记忆
    memories = search_memories(user_msg, user_id, limit=max_memories)

    if memories:
        memory_texts = []
        for mem in memories:
            mem_text = mem.get("memory", "")
            if mem_text:
                memory_texts.append(f"- {mem_text}")

        if memory_texts:
            memory_context = (
                "以下是关于这位用户的一些背景信息（从之前的对话中提取），"
                "你可以在回复中自然地引用：\n" + "\n".join(memory_texts)
            )
            messages.append({"role": "system", "content": memory_context})

    # 2. 添加短期对话历史（最近 N 轮）
    max_history_messages = MAX_HISTORY_ROUNDS * 2
    recent_history = history[-max_history_messages:] if len(history) > max_history_messages else history
    messages.extend(recent_history)

    # 3. 添加当前用户消息
    messages.append({"role": "user", "content": user_msg})

    return messages


def call_llm(messages: List[Dict]) -> str:
    """调用大模型获取回复，包含异常处理。"""
    try:
        response = chat_client.invoke(messages)
        return response.content.strip()
    except Exception as e:
        error_msg = f"LLM 调用失败: {e}"
        print(f"❌ {error_msg}")
        return f"抱歉，我暂时遇到了一些技术问题，请稍后再试。（{error_msg}）"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 【第五部分】Gradio 对话处理函数
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def respond(
    message: str,
    history: List[Dict],
    user_id: str,
) -> Tuple[str, List[Dict]]:
    """
    Gradio 对话处理函数（Gradio 6.0 消息格式）。
    
    参数：
    - message: 用户当前输入
    - history: 历史消息列表，格式 [{"role": "user", "content": "..."}, ...]
    - user_id: 用于隔离不同用户的记忆
    
    返回：
    - ("", 新的历史列表)：清空输入框，保留完整聊天历史
    """
    user_id = (user_id or "").strip() or DEFAULT_USER_ID

    # 构建 messages（系统提示词 + 记忆 + 历史 + 当前消息）
    messages = build_messages(message, user_id, history)

    # 调用 LLM
    assistant_reply = call_llm(messages)

    # 将对话存入 Mem0（后台线程，不阻塞对话）
    threading.Thread(
        target=add_memories,
        args=(message, assistant_reply, user_id),
        daemon=True
    ).start()

    # 返回 ("", 新历史) 格式：清空输入框，保留完整聊天历史
    new_history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": assistant_reply},
    ]
    return ("", new_history)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 【第六部分】Gradio 界面
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def create_interface() -> gr.Blocks:
    """创建 Gradio 聊天界面。"""

    def on_clear_click(user_id):
        """清除记忆按钮的回调函数。"""
        user_id = (user_id or "").strip() or DEFAULT_USER_ID
        return clear_user_memories(user_id)

    with gr.Blocks(title="小忆 - AI 情感陪伴助手") as demo:
        # 标题
        gr.Markdown(
            """
            # 🌸 小忆 - AI 情感陪伴助手
            我会一直陪着你。你的故事，我都记得 💕
            """,
        )

        with gr.Row():
            # ── 侧边栏 ──
            with gr.Column(scale=1, min_width=280):
                gr.Markdown("### ⚙️ 用户设置")

                user_id_input = gr.Textbox(
                    label="用户 ID",
                    value=DEFAULT_USER_ID,
                    placeholder="输入你的用户 ID",
                    info="不同用户 ID 的记忆互相隔离",
                )

                clear_btn = gr.Button("🗑️ 清除我的记忆", variant="stop")
                clear_status = gr.Textbox(label="操作结果", interactive=False, lines=2)

                clear_btn.click(
                    fn=on_clear_click,
                    inputs=[user_id_input],
                    outputs=[clear_status],
                )

                gr.Markdown(
                    """
                    ---
                    ### 💡 小贴士
                    - 每次对话我都会记住重要信息
                    - 切换用户 ID 可体验多用户隔离
                    - 清除记忆后无法恢复哦
                    """,
                )

            # ── 主聊天区 ──
            with gr.Column(scale=4):
                chatbot = gr.Chatbot(
                    label="和小忆聊天",
                    placeholder="说点什么吧，我在听 💬",
                    height=500,
                )

                with gr.Row():
                    msg_input = gr.Textbox(
                        placeholder="输入你的消息...",
                        show_label=False,
                        scale=4,
                    )
                    submit_btn = gr.Button("发送", variant="primary", scale=1)

                # 提交按钮绑定
                submit_btn.click(
                    fn=respond,
                    inputs=[msg_input, chatbot, user_id_input],
                    outputs=[msg_input, chatbot],
                )

                # 回车键提交
                msg_input.submit(
                    fn=respond,
                    inputs=[msg_input, chatbot, user_id_input],
                    outputs=[msg_input, chatbot],
                )

    return demo


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 【主程序】
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    # 确保控制台输出为 UTF-8（Windows 兼容）
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

    # 检查必要的 API Key
    if not MEM0_API_KEY or not CHAT_API_KEY:
        print("⚠️ 请先在 .env 文件中配置以下 API Key:")
        print("   - mem0_API_KEY")
        print("   - LLM_API_KEY")
        sys.exit(1)

    print("🌸 小忆 - AI 情感陪伴助手（网页版）")
    print("=" * 50)
    print("正在启动 Web 服务...")

    # 创建界面
    app = create_interface()

    # 自动打开浏览器（延迟 1.5 秒等待服务启动）
    def open_browser():
        import time
        time.sleep(1.5)
        webbrowser.open("http://127.0.0.1:7860")

    threading.Thread(target=open_browser, daemon=True).start()

    # 启动服务
    app.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        inbrowser=False,
        theme=gr.themes.Soft(
            primary_hue="rose",
            secondary_hue="pink",
        ),
    )
