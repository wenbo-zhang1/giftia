"""
小忆 - AI 情感陪伴助手（Streamlit 原生 UI 版）

运行方式：
    streamlit run app.py
"""

import os
import sys
import uuid
import json
import re
import datetime
from typing import List, Dict
from dotenv import load_dotenv
from llm_config import get_llm_client
from mem0 import MemoryClient
import streamlit as st
from memory_manager import MemoryManager, Mem0Bridge, EmotionType, MemoryCategory
from emotion_graph import build_emotion_graph, run_emotion_workflow
from file_processor import is_multimodal_model, image_to_base64_data_url, get_image_support_message
from conversation_store import ConversationStore

load_dotenv()

# ================================================================
# 配置项
# ================================================================

MEM0_API_KEY = os.environ.get("mem0_API_KEY", "")
CHAT_API_KEY = os.environ.get("LLM_API_KEY", "") or os.environ.get("Deepseek_API_KEY", "")
DEFAULT_USER_ID = "web_user_001"
MEMORY_SEARCH_LIMIT = 5

# ================================================================
# 初始化
# ================================================================

@st.cache_resource
def get_mem0_client():
    api_key = os.environ.get("mem0_API_KEY", "")
    if not api_key:
        return None
    try:
        return MemoryClient(api_key=api_key)
    except Exception as e:
        print(f"[警告] Mem0 初始化失败: {e}")
        return None

@st.cache_resource
def get_chat_client():
    return get_llm_client(temperature=0.7)

@st.cache_resource
def get_memory_manager():
    return MemoryManager(storage_path="./memory_store")

@st.cache_resource
def get_mem0_bridge(_memory_manager: MemoryManager):
    api_key = os.environ.get("mem0_API_KEY", "")
    if not api_key:
        return Mem0Bridge(memory_manager=_memory_manager)
    try:
        mem0_client = MemoryClient(api_key=api_key)
        return Mem0Bridge(memory_manager=_memory_manager, mem0_client=mem0_client)
    except Exception as e:
        print(f"[警告] Mem0 Bridge 初始化失败: {e}")
        return Mem0Bridge(memory_manager=_memory_manager)

def get_emotion_graph(_mm: MemoryManager, _bridge: Mem0Bridge):
    """初始化 LangGraph 情感陪伴工作流。"""
    return build_emotion_graph(memory_manager=_mm, mem0_bridge=_bridge)

mem0_client_for_chat = get_mem0_client()
chat_client = get_chat_client()
memory_manager = get_memory_manager()
mem0_bridge = get_mem0_bridge(memory_manager)
emotion_graph = get_emotion_graph(memory_manager, mem0_bridge)

_multimodal_supported = is_multimodal_model()
_image_not_supported_msg = get_image_support_message()

# ================================================================
# 记忆操作
# ================================================================

def delete_all_memories(user_id: str) -> bool:
    try:
        if mem0_bridge.mem0_client:
            mem0_bridge.mem0_client.delete_all(user_id=user_id)
    except Exception:
        pass
    memory_manager.delete_user_memories(user_id)
    return True

# ================================================================
# 对话逻辑（LangGraph 工作流）
# ================================================================

# image_data parameter added for multimodal support
def generate_reply(user_msg: str, user_id: str, conv_history: List[Dict], image_data: str = None) -> str:
    return run_emotion_workflow(
        graph=emotion_graph,
        user_id=user_id,
        user_message=user_msg,
        conversation_history=conv_history,
        image_data=image_data,
    )

# ================================================================
# 会话管理（含持久化）
# ================================================================

def init_session_state():
    if "_conv_store" not in st.session_state:
        st.session_state["_conv_store"] = ConversationStore()
    
    defaults = {
        "user_id": DEFAULT_USER_ID,
        "conversations": {},
        "current_conv_id": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    
    # 尝试从持久化存储加载
    if not st.session_state["conversations"]:
        store = st.session_state["_conv_store"]
        convs, current_id = store.load(st.session_state["user_id"])
        if convs and current_id and current_id in convs:
            st.session_state["conversations"] = convs
            st.session_state["current_conv_id"] = current_id
        else:
            _new_conv()

def _save_conversations():
    """保存当前会话到持久化存储。"""
    store = st.session_state.get("_conv_store")
    if store:
        store.save(
            st.session_state["user_id"],
            st.session_state["conversations"],
            st.session_state["current_conv_id"],
        )

@st.dialog("切换模型", width="large")
def _show_model_dialog():
    st.markdown("只需修改 `.env` 文件中的配置，然后重启程序即可生效")
    
    st.info("**1. 打开项目根目录下的 `.env` 文件**")
    st.info("**2. 修改以下三行配置**")
    st.info("**3. 保存文件，关闭并重新运行程序**")
    
    st.subheader("需要修改的配置")
    st.code("LLM_MODEL=模型名称\nLLM_API_KEY=你的API密钥\nLLM_BASE_URL=API地址")
    
    st.subheader("常用模型配置示例")
    
    with st.expander("DeepSeek（默认）"):
        st.code("LLM_MODEL=deepseek-v4-flash\nLLM_BASE_URL=https://api.deepseek.com/v1")
    
    with st.expander("OpenAI"):
        st.code("LLM_MODEL=gpt-4o\nLLM_BASE_URL=https://api.openai.com/v1")
    
    with st.expander("智谱AI"):
        st.code("LLM_MODEL=glm-4-flash\nLLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4")
    
    with st.expander("通义千问"):
        st.code("LLM_MODEL=qwen-plus\nLLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1")
    
    with st.expander("SiliconFlow"):
        st.code("LLM_MODEL=Qwen/Qwen2.5-72B-Instruct\nLLM_BASE_URL=https://api.siliconflow.cn/v1")
    
    if st.button("关闭", type="primary", use_container_width=True):
        st.rerun()

def _new_conv():
    cid = str(uuid.uuid4())
    st.session_state["conversations"][cid] = {
        "title": "新对话",
        "messages": [],
        "created": datetime.datetime.now().strftime("%m/%d %H:%M"),
    }
    st.session_state["current_conv_id"] = cid
    _save_conversations()

def _get_conv():
    cid = st.session_state["current_conv_id"]
    if cid not in st.session_state["conversations"]:
        _new_conv()
    return st.session_state["conversations"][st.session_state["current_conv_id"]]


# ================================================================
# 用户管理
# ================================================================

def get_all_users() -> List[str]:
    """从 memory_store 目录读取所有用户 ID。"""
    mem_store = os.path.join(os.path.dirname(__file__), "memory_store")
    if not os.path.exists(mem_store):
        return [DEFAULT_USER_ID]
    users = []
    for filename in os.listdir(mem_store):
        if filename.endswith(".json"):
            users.append(filename[:-5])
    return sorted(users) if users else [DEFAULT_USER_ID]


def switch_user(new_uid: str):
    """切换到指定用户。"""
    st.session_state["user_id"] = new_uid.strip()
    st.session_state["conversations"] = {}
    _new_conv()
    st.rerun()


def _switch_to_user(new_uid: str):
    """内部用户切换逻辑（不 rerun）。"""
    st.session_state["user_id"] = new_uid.strip()
    st.session_state["conversations"] = {}
    _new_conv()

# ================================================================
# 聊天气泡渲染
# ================================================================

def _md_to_html(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"```(\w*)\n(.*?)```", r"<pre><code>\2</code></pre>", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"<em>\1</em>", text)
    lines = text.split("\n")
    result = []
    in_list = False
    for line in lines:
        stripped = line.strip()
        if re.match(r"^[-*]\s+", stripped):
            if not in_list:
                result.append("<ul>")
                in_list = True
            item = re.sub(r"^[-*]\s+", "", stripped)
            result.append(f"<li>{item}</li>")
        else:
            if in_list:
                result.append("</ul>")
                in_list = False
            result.append(stripped if stripped else "<br>")
    if in_list:
        result.append("</ul>")
    return "\n".join(result)

def _render_bubble(content: str, role: str):
    bubble_class = "bubble-user" if role == "user" else "bubble-assistant"
    html_content = _md_to_html(content)
    st.markdown(
        f'<div class="chat-row"><div class="chat-bubble {bubble_class}">{html_content}</div></div>',
        unsafe_allow_html=True,
    )

# ================================================================
# 主程序
# ================================================================

def main():
    st.set_page_config(page_title="小忆", page_icon="❤️", layout="wide")

    st.markdown("""
<style>
    /* ================================================================
       DeepSeek Design System
    ================================================================ */
    :root {
        --accent: #4d6bfe;
        --accent-glow: rgba(77, 107, 254, 0.20);
        --accent-subtle: rgba(77, 107, 254, 0.08);
        --sidebar-bg: #f9fafb;
        --sidebar-surface: #fff;
        --sidebar-surface-raised: #f3f4f6;
        --sidebar-text: #1f2937;
        --sidebar-text-dim: #6b7280;
        --sidebar-text-muted: #9ca3af;
        --sidebar-border: #e5e7eb;
    }

    /* ---------- Global overrides ---------- */
    .main .block-container { padding-top: 1rem; padding-bottom: 2rem; }

    /* ---------- Primary buttons (global) ---------- */
    .stButton button[kind="primary"] {
        background: var(--accent) !important;
        border: none !important;
        color: #fff !important;
        font-weight: 600 !important;
        letter-spacing: 0.01em !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 2px 8px rgba(77,107,254,0.25) !important;
    }
    .stButton button[kind="primary"]:hover {
        background: #5b78ff !important;
        box-shadow: 0 4px 14px rgba(77,107,254,0.35) !important;
        transform: translateY(-1px) !important;
    }

    /* ---------- Sidebar base ---------- */
    section[data-testid="stSidebar"] {
        background: var(--sidebar-bg) !important;
        border-right: 1px solid var(--sidebar-border) !important;
    }
    section[data-testid="stSidebar"] .block-container {
        padding: 1.25rem 1rem !important;
    }

    /* ---------- Sidebar text ---------- */
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] .stMarkdown {
        color: var(--sidebar-text) !important;
    }
    section[data-testid="stSidebar"] caption,
    section[data-testid="stSidebar"] .st-caption {
        color: var(--sidebar-text-dim) !important;
    }
    section[data-testid="stSidebar"] .st-emotion-cache-1v0mbn {
        color: var(--sidebar-text-dim) !important;
    }

    /* ---------- Dividers ---------- */
    section[data-testid="stSidebar"] hr {
        border-color: var(--sidebar-border) !important;
        margin: 0.625rem 0 !important;
    }

    /* ---------- Main sidebar buttons ---------- */
    section[data-testid="stSidebar"] .stButton > button {
        height: 38px !important;
        min-height: 38px !important;
        font-size: 13.5px !important;
        font-weight: 500 !important;
        line-height: 1 !important;
        border-radius: 10px !important;
        padding: 0 14px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        gap: 6px !important;
        transition: all 0.18s ease !important;
        border: 1px solid transparent !important;
    }

    /* Default (secondary) sidebar buttons */
    section[data-testid="stSidebar"] .stButton > button[kind="secondary"] {
        background: var(--sidebar-surface) !important;
        color: var(--sidebar-text) !important;
        border-color: var(--sidebar-border) !important;
    }
    section[data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {
        background: var(--sidebar-surface-raised) !important;
        border-color: var(--accent) !important;
        color: var(--accent) !important;
    }

    /* Primary sidebar buttons */
    section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
        justify-content: center !important;
        font-size: 13.5px !important;
        font-weight: 600 !important;
        height: 40px !important;
        border-radius: 10px !important;
    }

    /* ---------- Conversation item: active state ---------- */
    section[data-testid="stSidebar"] .stButton > button[kind="primary"].conv-item {
        background: rgba(77,107,254,0.08) !important;
        border-color: rgba(77,107,254,0.25) !important;
        color: #4d6bfe !important;
        box-shadow: inset 0 0 0 1px rgba(77,107,254,0.06) !important;
    }

    /* ---------- Selectbox ---------- */
    section[data-testid="stSidebar"] .stSelectbox > div > div {
        background: var(--sidebar-surface) !important;
        border: 1px solid var(--sidebar-border) !important;
        border-radius: 10px !important;
        color: var(--sidebar-text) !important;
        font-size: 13.5px !important;
    }
    section[data-testid="stSidebar"] .stSelectbox label {
        font-size: 12px !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
        color: var(--sidebar-text-dim) !important;
        margin-bottom: 4px !important;
    }

    /* ---------- Text inputs ---------- */
    section[data-testid="stSidebar"] .stTextInput input {
        height: 36px !important;
        font-size: 13.5px !important;
        border-radius: 10px !important;
        background: var(--sidebar-surface) !important;
        border: 1px solid var(--sidebar-border) !important;
        color: var(--sidebar-text) !important;
    }
    section[data-testid="stSidebar"] .stTextInput input:focus {
        border-color: var(--accent) !important;
        box-shadow: none !important;
        outline: none !important;
    }
    section[data-testid="stSidebar"] .stTextInput [data-baseweb="input"]:focus {
        border-color: var(--accent) !important;
    }
    section[data-testid="stSidebar"] .stTextInput input::placeholder {
        color: var(--sidebar-text-muted) !important;
    }

    /* ---------- Expander ---------- */
    section[data-testid="stSidebar"] .streamlit-expanderHeader {
        font-size: 13px !important;
        background: transparent !important;
        border-radius: 10px !important;
        border: 1px solid var(--sidebar-border) !important;
        color: var(--sidebar-text-dim) !important;
        font-weight: 500 !important;
    }

    /* ---------- Warning box ---------- */
    section[data-testid="stSidebar"] .stAlert {
        background: rgba(255,159,67,0.12) !important;
        border: 1px solid rgba(255,159,67,0.25) !important;
        border-radius: 10px !important;
        color: #e8a840 !important;
    }

    /* ---------- Chat messages: WeChat-style bubbles ---------- */
    .chat-bubble {
        position: relative;
        max-width: 75%;
        padding: 10px 14px;
        border-radius: 8px;
        font-size: 15px;
        line-height: 1.55;
        word-wrap: break-word;
        word-break: break-word;
        white-space: pre-wrap;
    }
    .bubble-user {
        background: #95EC69;
        color: #000;
        float: right;
        margin-right: 0;
    }
    .bubble-assistant {
        background: #FFFFFF;
        color: #1F2937;
        float: left;
        margin-left: 0;
        border: 1px solid #E5E7EB;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .chat-row {
        overflow: hidden;
        margin: 6px 0;
    }

    /* ---------- Chat input ---------- */
    .stChatInput textarea,
    .stChatInput {
        border-color: #e2e2e5 !important;
        border-radius: 14px !important;
    }
    .stChatInput textarea:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px rgba(77,107,254,0.15) !important;
    }
    [data-testid="stChatInput"] span[class*="decoration"],
    [data-testid="stChatInput"] span[class*="Decor"],
    [data-testid="stChatInput"] span[class*="bracket"] {
        display: none !important;
    }

    /* ---------- DeepSeek-style chat input ---------- */
    [data-testid="stChatInput"] {
        position: relative !important;
        margin-top: 8px !important;
        margin-bottom: 20px !important;
    }
    /* The inner container — border + shadow + padding + radius */
    [data-testid="stChatInput"] > div:first-child {
        border: 1px solid #e2e8f0 !important;
        border-radius: 24px !important;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06), 0 0 1px rgba(0,0,0,0.04) !important;
        background: #fff !important;
        padding: 10px 16px 10px 20px !important;
        transition: box-shadow 0.2s ease !important;
    }
    [data-testid="stChatInput"] > div:first-child:hover {
        box-shadow: 0 2px 16px rgba(0,0,0,0.09), 0 0 1px rgba(0,0,0,0.06) !important;
    }
    [data-testid="stChatInput"] textarea {
        min-height: 56px !important;
        max-height: 200px !important;
        border: none !important;
        background: transparent !important;
        font-size: 15px !important;
        line-height: 1.6 !important;
        color: #1f2937 !important;
        padding: 4px 0 !important;
        box-shadow: none !important;
        resize: none !important;
    }
    [data-testid="stChatInput"] textarea::placeholder {
        color: #9ca3af !important;
    }
    /* Submit button — purple circle */
    [data-testid="stChatInputSubmitButton"] {
        width: 36px !important;
        height: 36px !important;
        min-width: 36px !important;
        min-height: 36px !important;
        border-radius: 50% !important;
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        background: #4d6bfe !important;
        border: none !important;
        box-shadow: 0 1px 4px rgba(77,107,254,0.3) !important;
        transition: all 0.15s ease !important;
        flex-shrink: 0 !important;
    }
    [data-testid="stChatInputSubmitButton"]:hover {
        background: #3b5de7 !important;
        box-shadow: 0 2px 8px rgba(77,107,254,0.4) !important;
        transform: scale(1.05) !important;
    }
    [data-testid="stChatInputSubmitButton"] svg {
        fill: #fff !important;
    }

    /* Injected paperclip button */
    .ds-attach-btn {
        width: 36px !important;
        height: 36px !important;
        min-width: 36px !important;
        min-height: 36px !important;
        border-radius: 50% !important;
        border: none !important;
        background: transparent !important;
        cursor: pointer !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        transition: background 0.15s ease !important;
        flex-shrink: 0 !important;
        padding: 0 !important;
    }
    .ds-attach-btn:hover {
        background: rgba(0,0,0,0.06) !important;
    }
    .ds-attach-btn svg {
        width: 18px !important;
        height: 18px !important;
        stroke: #6b7280 !important;
    }

    /* Action row — make the submit button's parent flex, right-aligned */
    #ds-actions-row {
        display: flex !important;
        align-items: center !important;
        justify-content: flex-end !important;
        margin-top: 4px !important;
        padding-top: 2px !important;
        gap: 6px !important;
    }

    /* ---------- Stats card ---------- */
    .sidebar-stats {
        background: var(--sidebar-surface);
        border: 1px solid var(--sidebar-border);
        border-radius: 12px;
        padding: 14px 16px;
        margin-top: 10px;
    }
    .sidebar-stats .stat-divider {
        height: 1px;
        background: var(--sidebar-border);
        margin: 6px 0 2px 0;
    }
    .stat-metrics-grid {
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 4px;
        padding: 4px 0 0 0;
    }
    .stat-metrics-grid .metric-item {
        text-align: center;
        padding: 4px 2px;
    }
    .stat-metrics-grid .metric-value {
        font-size: 22px;
        font-weight: 700;
        color: var(--sidebar-text);
        line-height: 1.2;
    }
    .stat-metrics-grid .metric-label {
        font-size: 10.5px;
        color: var(--sidebar-text-dim);
        font-weight: 500;
        margin-top: 1px;
    }

    /* ---------- User avatar circle ---------- */
    .user-avatar {
        width: 28px; height: 28px;
        border-radius: 50%;
        background: linear-gradient(135deg, #4d6bfe, #3b5de7);
        display: inline-flex; align-items: center; justify-content: center;
        font-size: 13px; color: #fff; font-weight: 700;
        margin-right: 8px;
    }
</style>
<script>
document.querySelectorAll('input').forEach(function(el) {
    if (!el.getAttribute('autocomplete')) el.setAttribute('autocomplete', 'off');
});
/* ---------- Inject paperclip button into chat input ---------- */
(function injectAttachBtn() {
    var submitBtn = document.querySelector('[data-testid="stChatInputSubmitButton"]');
    if (!submitBtn) { setTimeout(injectAttachBtn, 200); return; }
    if (document.querySelector('.ds-attach-btn')) return;

    var actionsRow = submitBtn.parentElement;
    actionsRow.id = 'ds-actions-row';

    var btn = document.createElement('button');
    btn.className = 'ds-attach-btn';
    btn.type = 'button';
    btn.setAttribute('title', '上传图片');
    btn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>';
    actionsRow.insertBefore(btn, submitBtn);

    btn.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        var hiddenInput = document.getElementById('ds-hidden-file-input');
        if (hiddenInput) hiddenInput.click();
    });
})();
</script>
""", unsafe_allow_html=True)

    init_session_state()

    _current_model_env = os.environ.get("LLM_MODEL", os.environ.get("CHAT_MODEL", "deepseek-v4-flash"))
    _current_base_url_env = os.environ.get("LLM_BASE_URL", os.environ.get("CHAT_BASE_URL", "https://api.deepseek.com/v1"))

    with st.sidebar:
        st.markdown("""
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">
            <div style="width:38px;height:38px;border-radius:12px;background:linear-gradient(135deg,#6b8aff,#4d6bfe 50%,#3b5de7);display:flex;align-items:center;justify-content:center;box-shadow:0 2px 8px rgba(77,107,254,0.30)"><svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="white" stroke="none"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg></div>
            <div>
                <div style="font-size:17px;font-weight:700;color:#1f2937;line-height:1.2">小忆</div>
                <div style="font-size:11.5px;color:#6b7280;font-weight:500;letter-spacing:0.04em">AI 情感陪伴</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 当前模型显示
        st.markdown(f"""
        <div style="background:var(--sidebar-surface);border:1px solid var(--sidebar-border);border-radius:10px;padding:10px 12px;margin:10px 0 0 0">
            <div style="font-size:11px;color:var(--sidebar-text-dim);font-weight:600;text-transform:uppercase;letter-spacing:0.04em;margin-bottom:4px">当前模型</div>
            <div style="font-size:14px;font-weight:600;color:var(--sidebar-text)">{_current_model_env}</div>
            <div style="font-size:11px;color:var(--sidebar-text-muted);margin-top:2px">{_current_base_url_env}</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🔄 切换模型", use_container_width=True, key="open_model_dialog_btn"):
            st.session_state["show_model_dialog"] = True

        if st.button("＋ 开启新对话", use_container_width=True, key="_new_chat_btn"):
            _new_conv()
            st.rerun()

        st.markdown('<div style="margin:14px 0 8px 0;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:var(--sidebar-text-muted)">对话</div>', unsafe_allow_html=True)

        search_query = st.text_input(
            "搜索对话",
            key="search_convs",
            placeholder="搜索历史对话…",
            label_visibility="collapsed"
        ).strip().lower()

        convs = st.session_state["conversations"]
        current_id = st.session_state["current_conv_id"]

        sorted_convs = sorted(convs.items(), key=lambda x: x[1].get("created", ""), reverse=True)

        if search_query:
            sorted_convs = [
                (cid, cd) for cid, cd in sorted_convs
                if search_query in cd.get("title", "").lower()
            ]

        for cid, cd in sorted_convs:
            title = cd.get("title", "新对话")
            is_active = cid == current_id
            is_editing = st.session_state.get(f"_editing_{cid}", False)

            if is_editing:
                col1, col2, col3 = st.columns([5, 1, 1])
                new_title = col1.text_input(
                    "重命名",
                    value=title,
                    key=f"_rename_input_{cid}",
                    label_visibility="collapsed"
                )
                if col2.button("✓", key=f"_save_rename_{cid}"):
                    if new_title.strip():
                        st.session_state["conversations"][cid]["title"] = new_title.strip()
                    st.session_state.pop(f"_editing_{cid}", None)
                    _save_conversations()
                    st.rerun()
                if col3.button("✕", key=f"_cancel_rename_{cid}"):
                    st.session_state.pop(f"_editing_{cid}", None)
                    st.rerun()
            else:
                display_title = title[:14] + "…" if len(title) > 14 else title
                label_safe = ("● " + display_title) if is_active else display_title

                c1, c2, c3 = st.columns([6, 1, 1])
                btn_type = "primary" if is_active else "secondary"
                if c1.button(label_safe, key=f"_sel_{cid}", use_container_width=True, type=btn_type):
                    st.session_state["current_conv_id"] = cid
                    _save_conversations()
                    st.rerun()
                if c2.button("✎", key=f"_ed_{cid}"):
                    st.session_state[f"_editing_{cid}"] = True
                    st.rerun()
                if c3.button("✕", key=f"_del_{cid}"):
                    del convs[cid]
                    if not convs:
                        _new_conv()
                    elif current_id == cid:
                        st.session_state["current_conv_id"] = list(convs.keys())[-1]
                    _save_conversations()
                    st.rerun()

        st.divider()

        # ================================================================
        # 用户配置
        # ================================================================

        st.markdown('<div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:var(--sidebar-text-muted);margin-bottom:4px">用户</div>', unsafe_allow_html=True)

        all_users = get_all_users()
        current_user = st.session_state["user_id"]

        if current_user not in all_users:
            all_users.insert(0, current_user)

        user_labels = {}
        for u in all_users:
            stats = memory_manager.get_memory_stats(u)
            count = stats.get("total", 0)
            user_labels[u] = f"👤 {u}  ·  {count} 记忆"

        selected_user = st.selectbox(
            "选择用户",
            options=all_users,
            index=all_users.index(current_user) if current_user in all_users else 0,
            format_func=lambda u: user_labels.get(u, u),
            label_visibility="collapsed",
        )

        if selected_user != current_user:
            _switch_to_user(selected_user)
            st.rerun()

        with st.expander("＋ 添加用户"):
            col_a, col_b = st.columns([3, 1])
            new_uid_input = col_a.text_input(
                "新用户 ID",
                key="new_user_input",
                placeholder="输入 ID…",
                label_visibility="collapsed"
            )
            if col_b.button("创建", use_container_width=True, key="create_user_btn", type="primary"):
                if new_uid_input.strip():
                    _switch_to_user(new_uid_input.strip())
                    st.rerun()

        st.markdown('<div style="margin-top:8px"></div>', unsafe_allow_html=True)
        if st.button("清除记忆", use_container_width=True, type="secondary"):
            st.session_state["_confirm_clear_memories"] = True
            st.rerun()

        if st.session_state.get("_confirm_clear_memories", False):
            st.warning("确定清除此用户的所有记忆？不可撤销。", icon="⚠️")
            col_yes, col_no = st.columns(2)
            if col_yes.button("确认", use_container_width=True, type="primary"):
                uid = st.session_state["user_id"]
                try:
                    if mem0_bridge.mem0_client:
                        mem0_bridge.mem0_client.delete_all(user_id=uid)
                except Exception:
                    pass
                memory_manager.delete_user_memories(uid)
                mem_store = os.path.join(os.path.dirname(__file__), "memory_store")
                mem_file = os.path.join(mem_store, f"{uid}.json")
                if os.path.exists(mem_file):
                    os.remove(mem_file)
                st.session_state.pop("_confirm_clear_memories", None)
                st.toast("已清除所有记忆", icon="✅")
                st.rerun()
            if col_no.button("取消", use_container_width=True):
                st.session_state.pop("_confirm_clear_memories", None)
                st.rerun()

        st.divider()

        current_stats = memory_manager.get_memory_stats(current_user)
        st.markdown(f"""
        <div class="sidebar-stats">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
                <div class="user-avatar">{current_user[0].upper() if current_user else 'U'}</div>
                <div>
                    <div style="font-size:13px;font-weight:600;color:var(--sidebar-text)">{current_user[:14]}</div>
                    <div style="font-size:11px;color:var(--sidebar-text-dim)">当前用户</div>
                </div>
            </div>
            <div class="stat-divider"></div>
        """, unsafe_allow_html=True)
        if current_stats.get("total", 0) > 0:
            importance = current_stats.get("avg_importance", 0)
            consolidated = current_stats.get("consolidated_count", 0)
            st.markdown(f"""
                <div class="stat-metrics-grid">
                    <div class="metric-item">
                        <div class="metric-value">{current_stats['total']}</div>
                        <div class="metric-label">记忆总数</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-value">{consolidated}</div>
                        <div class="metric-label">巩固记忆</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-value">{importance:.1f}</div>
                        <div class="metric-label">重要性</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
                <div style="font-size:12px;color:var(--sidebar-text-muted);text-align:center;padding:10px 0">暂无记忆数据</div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.pop("show_model_dialog", False):
        _show_model_dialog()

    conv = _get_conv()
    msgs = conv["messages"]

    st.title(conv["title"])

    for m in msgs:
        _render_bubble(m["content"], m["role"])

    # Hidden file input — triggered by the injected paperclip button
    if _multimodal_supported:
        uploaded_file = st.file_uploader(
            "",
            type=["jpg", "jpeg", "png", "gif", "webp"],
            key="uploaded_image",
            label_visibility="collapsed",
            accept_multiple_files=False,
        )
        if uploaded_file:
            st.session_state["_uploaded_file_name"] = uploaded_file.name
        # Hide Streamlit's file uploader UI (keep functional input)
        st.markdown("""
        <style>
        div[data-testid="stFileUploader"] {
            position: absolute !important;
            left: -9999px !important;
            top: -9999px !important;
            visibility: hidden !important;
            pointer-events: none !important;
        }
        </style>
        """, unsafe_allow_html=True)
        # Hidden HTML file input that the JS paperclip clicks
        st.markdown("""
        <input type="file" id="ds-hidden-file-input" accept="image/jpeg,image/png,image/gif,image/webp" style="display:none" />
        <script>
        (function wireHiddenInput() {
            var hidden = document.getElementById('ds-hidden-file-input');
            var realUploaders = document.querySelectorAll('input[type="file"][data-testid="stFileUploaderUploadInput"]');
            if (!hidden || !realUploaders.length) { setTimeout(wireHiddenInput, 200); return; }
            var realInput = realUploaders[0];
            hidden.addEventListener('change', function() {
                if (this.files.length) {
                    realInput.files = this.files;
                    var ev = new Event('change', { bubbles: true });
                    realInput.dispatchEvent(ev);
                }
            });
        })();
        </script>
        """, unsafe_allow_html=True)
        if st.session_state.get("_uploaded_file_name"):
            st.image(uploaded_file, width=180, caption=st.session_state["_uploaded_file_name"])

    if prompt := st.chat_input("和我说说你的心事吧..."):
        image_data = None
        uf = st.session_state.get("uploaded_image")
        if uf and _multimodal_supported:
            image_bytes = uf.getvalue()
            image_data, img_error = image_to_base64_data_url(image_bytes, uf.name)
            if img_error:
                st.error(img_error)
                st.stop()

        msgs.append({"role": "user", "content": prompt})

        with st.spinner("小忆正在思考..."):
            reply = generate_reply(prompt, st.session_state["user_id"], msgs[:-1], image_data=image_data)

        msgs.append({"role": "assistant", "content": reply})
        conv["messages"] = msgs
        _save_conversations()

        st.session_state.pop("uploaded_image", None)
        st.session_state.pop("_uploaded_file_name", None)

        if len(msgs) == 2:
            conv["title"] = prompt[:20] or "新对话"
            _save_conversations()

        st.rerun()


if __name__ == "__main__":
    if not MEM0_API_KEY or not CHAT_API_KEY:
        st.error("请在 .env 中配置 mem0_API_KEY 和 LLM_API_KEY")
        st.stop()
    if sys.stdout.encoding != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    main()
