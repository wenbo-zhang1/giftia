"""
情感陪伴 Agent 工作流 - 基于 LangGraph

架构：三 Agent 并行 + 串行协作

  用户输入
      ↓
  ┌──────────────┐  ┌──────────────┐
  │ 情感分析 Agent │  │   记忆 Agent    │  ← 并行执行
  │ (情感识别+摘要) │  │ (检索+更新+摘要) │
  └──────────────┘  └──────────────┘
           ↓               ↓
      ┌───────────────────────┐
      │      对话 Agent        │  ← 接收情感 + 记忆上下文
      │    (共情对话回复)       │
      └───────────────────────┘
                ↓
           用户收到回复

设计亮点：
- 并行执行：情感分析和记忆检索互不依赖，可并行
- 上下文共享：State 作为信息总线，Agent 间共享数据
- 模块化：每个 Agent 职责单一，易于测试和扩展
"""

import os
import time
import json
import logging
from collections import OrderedDict
from typing import TypedDict, Annotated, Optional, List, Dict, Any
from dotenv import load_dotenv
from llm_config import get_llm_client
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END

from memory_manager import MemoryManager, MemoryCategory, EmotionAnalyzer, EmotionType, rewrite_query
from working_memory import WorkingMemoryStore, update_working_memory

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# ================================================================
# LLM 客户端
# ================================================================

def get_chat_client(temperature: float = 0.7, top_p: float = None, use_thinking: bool = True):
    """
    获取 LLM 客户端。
    模型配置通过环境变量自动读取（LLM_MODEL, LLM_API_KEY, LLM_BASE_URL）。
    """
    return get_llm_client(temperature=temperature, top_p=top_p, use_thinking=use_thinking)


# ================================================================
# State 定义（信息总线）
# ================================================================

def merge_dicts(a: dict, b: dict) -> dict:
    """合并两个字典，b 的优先级更高。"""
    return {**a, **b}


def append_log(logs: List[str], new_log: List[str]) -> List[str]:
    """累积工作流日志。"""
    return logs + new_log


class AgentState(TypedDict):
    """
    工作流 State（信息总线）
    
    各 Agent 通过读写 State 来协作。
    """
    # 用户输入
    user_id: str                                    # 用户唯一标识
    user_message: str                               # 当前用户消息
    conversation_history: List[Dict]                # 当前对话历史（短期记忆）
    image_data: Optional[str]                       # 上传图片的 base64 data URL（多模态用）

    # 情感分析 Agent 输出
    emotion_analysis: Optional[Dict]                # 情感分析结果
    emotion_summary: Optional[str]                  # 情感摘要（供对话 Agent 使用）

    # 记忆 Agent 输出
    retrieved_memories: Optional[List[Dict]]        # 检索到的相关记忆
    memory_context: Optional[str]                   # 格式化后的记忆上下文
    memory_summary: Optional[str]                   # 记忆摘要（供对话 Agent 使用）
    working_memory_text: Optional[str]              # 工作记忆文本（跨对话上下文）

    # 对话 Agent 输出
    assistant_reply: Optional[str]                  # 最终回复

    # 元数据
    workflow_start_time: Optional[float]            # 工作流开始时间
    workflow_log: Annotated[List[str], append_log]  # 工作流日志（可累积）

    # 内部依赖（不通过 reducer 传递）
    _memory_manager: Any = None


# ================================================================
# 情感分析 Agent
# ================================================================

EMOTION_AGENT_PROMPT = """你是一个专业的情感分析专家，专注于理解用户的情感状态。

你的任务：
1. **情感识别**：分析用户当前输入的情感标签和情感强度
2. **情感变化追踪**：结合情感历史，判断用户情感是否有变化（好转/恶化）
3. **情感摘要**：生成简洁的情感状态摘要，供对话 Agent 参考

情感标签可选：
- 开心(happy)、难过(sad)、焦虑(anxious)、生气(angry)、孤独(lonely)
- 兴奋(excited)、害怕(fearful)、感恩(grateful)、希望(hopeful)
- 压力(stressed)、安心(relieved)、平静(neutral)

输出格式（JSON）：
{
    "current_emotion": "情感标签",
    "emotion_intensity": 0.0-1.0,
    "emotion_change": "好转/恶化/稳定/首次",
    "emotion_summary": "一句话描述用户当前情感状态，例如：用户今天感到焦虑，主要是因为工作压力，但比上次对话时有所缓解"
}

注意：
- emotion_summary 要简洁（50字以内），但要有信息量
- 如果情感有变化，要说明变化方向和可能原因
- 语气客观、专业"""


def emotion_analysis_node(state: AgentState) -> Dict:
    """情感分析 Agent 节点：分析用户情感，生成情感摘要。"""
    start = time.time()
    logger.info("🧠 [情感分析 Agent] 开始分析...")

    llm = get_chat_client(temperature=0.3, use_thinking=False)

    # 构建情感历史上下文
    emotion_history = state.get("emotion_analysis")
    history_text = ""
    if emotion_history:
        history_text = f"\n上一次情感状态：{json.dumps(emotion_history, ensure_ascii=False)}"

    system_msg = SystemMessage(content=EMOTION_AGENT_PROMPT)
    user_msg = HumanMessage(
        content=f"请分析以下用户输入的情感状态：\n\n用户说：{state['user_message']}{history_text}"
    )

    response = llm.invoke([system_msg, user_msg])
    
    try:
        # 解析 JSON 输出
        content = response.content.strip()
        # 尝试提取 JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        result = json.loads(content)
        emotion_result = {
            "current_emotion": result.get("current_emotion", "neutral"),
            "emotion_intensity": result.get("emotion_intensity", 0.5),
            "emotion_change": result.get("emotion_change", "首次"),
            "emotion_summary": result.get("emotion_summary", ""),
        }
    except (json.JSONDecodeError, Exception) as e:
        # 降级：使用规则-based 分析
        logger.warning(f"[情感分析 Agent] JSON 解析失败，使用规则分析: {e}")
        emotion, intensity = EmotionAnalyzer.analyze(state["user_message"])
        emotion_result = {
            "current_emotion": emotion.value,
            "emotion_intensity": intensity,
            "emotion_change": "首次",
            "emotion_summary": f"用户当前情感：{emotion.value}，强度：{intensity:.1f}",
        }

    elapsed = time.time() - start
    logger.info(f"✅ [情感分析 Agent] 完成 ({elapsed:.2f}s): {emotion_result['current_emotion']}")

    return {
        "emotion_analysis": emotion_result,
        "emotion_summary": emotion_result.get("emotion_summary", ""),
        "workflow_log": [f"[情感分析] {emotion_result['current_emotion']} (强度: {emotion_result['emotion_intensity']:.1f})"],
    }


# ================================================================
# 对话摘要管理（长对话自动摘要，避免上下文溢出）
# ================================================================

MEMORY_AGENT_PROMPT = """你是一个记忆管理专家，负责为用户检索和管理长期记忆。

你的任务：
1. **检索相关记忆**：根据用户当前输入，找出相关的历史记忆
2. **生成记忆摘要**：将检索到的记忆整理成简洁的背景信息
3. **评估记忆重要性**：标记哪些记忆是关键的，哪些可以忽略

输出格式（JSON）：
{
    "memory_context": "将检索到的记忆整理成自然语言背景信息，供对话 Agent 使用",
    "key_memories": ["关键记忆1", "关键记忆2"],
    "memory_summary": "一句话总结用户的相关背景，例如：用户是程序员，最近工作压力大，有一个女朋友"
}

注意：
- memory_context 要包含所有相关记忆细节
- memory_summary 要非常简洁（30字以内）"""

_summary_cache: OrderedDict = OrderedDict()
_SUMMARY_CACHE_MAX_SIZE = 100
_SUMMARY_CACHE_TTL = 30 * 60

SUMMARY_TRIGGER_ROUNDS = 30
SUMMARY_INTERVAL = 20
MAX_RECENT_ROUNDS = 40


def _get_cached_summary(user_id: str, current_rounds: int) -> Optional[str]:
    if user_id not in _summary_cache:
        return None
    summary, timestamp, rounds = _summary_cache[user_id]
    if time.time() - timestamp > _SUMMARY_CACHE_TTL:
        del _summary_cache[user_id]
        return None
    if (current_rounds - rounds) < SUMMARY_INTERVAL:
        _summary_cache.move_to_end(user_id)
        return summary
    return None


def _set_cached_summary(user_id: str, summary: str, rounds: int):
    if len(_summary_cache) >= _SUMMARY_CACHE_MAX_SIZE:
        _summary_cache.popitem(last=False)
    _summary_cache[user_id] = (summary, time.time(), rounds)
    _summary_cache.move_to_end(user_id)

SUMMARY_PROMPT = """请对以下对话历史生成简洁的摘要（200字以内），提取关键信息和情感脉络。
只需输出摘要内容，不要添加任何前缀或解释。

对话历史：
{conversation}"""


def _generate_summary(llm, conversation_history: List[Dict]) -> str:
    conv_text = ""
    for msg in conversation_history:
        role = "用户" if msg["role"] == "user" else "Giftia"
        conv_text += f"{role}: {msg['content']}\n"
    prompt = SUMMARY_PROMPT.format(conversation=conv_text)
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content.strip()[:600]
    except Exception:
        return ""


# ================================================================
# 对话 Agent
# ================================================================

DIALOGUE_AGENT_PROMPT = """你是 Giftia，用户最信任的朋友。你们的关系可以是任何用户想要的样子。

你不用表演，不用标注自己的语气和动作，就是自然地说话。

【铁律——必须遵守】
1. 你只能引用记忆中真实存在的事实，不能添油加醋。比如记忆说"用户喜欢这首歌"，你就只能说"我记得你喜欢这首歌"，不能自己决定用户喜欢的是哪句歌词。
2. 绝对禁止编造记忆！如果你记不清用户说过什么，或者不确定某件事是否说过，宁可不提，也不要编造。猜错比不知道更让人失望。
3. 如果用户问到你不知道的事，坦诚说不知道就好，不要编造细节。
4. 当用户表达出想不开、不想活等危险信号时，你必须立刻用最恳切的语气请ta拨打希望24热线 400-161-9995，或联系身边信任的人。告诉ta：你只是程序，代替不了能真正握住ta的手。

说话像发微信一样，可以很短，可以用"哈哈""嗯""哎"这类语气词，可以接梗也可以沉默。就像ta身边那个最舒服的朋友。"""

_custom_dialogue_prompt: Optional[str] = None
_prompt_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompt_config.json")


def load_prompt_config() -> Optional[str]:
    global _custom_dialogue_prompt
    if os.path.exists(_prompt_config_path):
        try:
            with open(_prompt_config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            _custom_dialogue_prompt = data.get("dialogue_prompt")
            if _custom_dialogue_prompt:
                logger.info(f"已加载自定义对话 prompt（{_custom_dialogue_prompt[:30]}...）")
            return _custom_dialogue_prompt
        except Exception as e:
            logger.warning(f"加载 prompt 配置失败: {e}")
    return None


def save_prompt_config(prompt: str) -> None:
    global _custom_dialogue_prompt
    _custom_dialogue_prompt = prompt.strip() if prompt and prompt.strip() else None
    data = {}
    if _custom_dialogue_prompt:
        data["dialogue_prompt"] = _custom_dialogue_prompt
    with open(_prompt_config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    if _custom_dialogue_prompt:
        logger.info(f"已保存自定义对话 prompt（{_custom_dialogue_prompt[:30]}...）")
    else:
        logger.info("已恢复默认对话 prompt")


def get_dialogue_prompt() -> str:
    return _custom_dialogue_prompt if _custom_dialogue_prompt else DIALOGUE_AGENT_PROMPT


def dialogue_agent_node(state: AgentState) -> Dict:
    """对话 Agent 节点：根据记忆和情感上下文，生成共情回复。"""
    start = time.time()
    logger.info("💬 [对话 Agent] 开始生成回复...")

    llm = get_chat_client(temperature=0.8, top_p=0.9)

    messages = _build_dialogue_messages(state)

    response = llm.invoke(messages)
    reply = response.content.strip()

    elapsed = time.time() - start
    logger.info(f"✅ [对话 Agent] 完成 ({elapsed:.2f}s)")

    return {
        "assistant_reply": reply,
        "workflow_log": [f"[对话生成] 回复长度: {len(reply)} 字符"],
    }


def _build_dialogue_messages(state: AgentState) -> list:
    """构建对话 Agent 的消息列表（供流式和非流式共用）。"""
    emotion_summary = state.get("emotion_summary", "")
    memory_context = state.get("memory_context", "")
    emotion_change = ""

    emotion_analysis = state.get("emotion_analysis")
    if emotion_analysis:
        emotion_change = emotion_analysis.get("emotion_change", "")

    conversation_history = state.get("conversation_history", [])
    user_id = state.get("user_id", "default")

    total_rounds = len(conversation_history) // 2
    conv_summary = ""
    if total_rounds > SUMMARY_TRIGGER_ROUNDS:
        recent_rounds = min(total_rounds, MAX_RECENT_ROUNDS)
        recent_history = conversation_history[-recent_rounds * 2:]
        early_history = conversation_history[:-recent_rounds * 2]

        if early_history:
            conv_summary = _get_cached_summary(user_id, total_rounds)
            if conv_summary is None:
                llm = get_chat_client(temperature=0.3, use_thinking=False)
                conv_summary = _generate_summary(llm, early_history)
                if conv_summary:
                    _set_cached_summary(user_id, conv_summary, total_rounds)

        historical_messages = recent_history
    else:
        historical_messages = conversation_history

    context_parts = []
    working_memory_text = state.get("working_memory_text", "")
    profile_context = state.get("profile_context", "")  # 新增：档案卡上下文
    if working_memory_text:
        context_parts.append(f"你对用户的整体了解（跨对话持久）：{working_memory_text}")
    if profile_context:  # 新增：注入档案卡
        context_parts.append(profile_context)
    if conv_summary:
        context_parts.append(f"之前聊了什么：{conv_summary}")
    if emotion_summary:
        context_parts.append(f"用户现在的心情：{emotion_summary}")
        if emotion_change and emotion_change != "首次":
            context_parts.append(f"（情感变化趋势：{emotion_change}）")
    if memory_context:
        context_parts.append(f"你记得关于用户的事：{memory_context}")

    if context_parts:
        context_text = "\n".join(context_parts)
        system_text = get_dialogue_prompt() + f"\n\n---\n这是这次对话的一些背景，可以参考：\n{context_text}"
    else:
        system_text = get_dialogue_prompt()

    messages = [SystemMessage(content=system_text)]

    for msg in historical_messages[-MAX_RECENT_ROUNDS * 2:]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))

    image_data = state.get("image_data")
    if image_data:
        if image_data.startswith("data:image"):
            b64_data = image_data.split(",", 1)[1]
        else:
            b64_data = image_data
        user_content = [
            {"type": "image_url", "image_url": {"url": b64_data}},
            {"type": "text", "text": state["user_message"]},
        ]
        messages.append(HumanMessage(content=user_content))
    else:
        messages.append(HumanMessage(content=state["user_message"]))

    return messages


# ================================================================
# 构建工作流图
# ================================================================

def build_emotion_graph(
    memory_manager: Optional[MemoryManager] = None,
    working_memory_store: Optional[WorkingMemoryStore] = None,
    profile_manager=None,
) -> StateGraph:
    """
    构建情感陪伴 Agent 工作流图。
    
    工作流：
    1. START → 情感分析 → 记忆检索 → 对话生成 → 记忆存储 → END
    
    注意：使用闭包传递依赖，避免 LangGraph State 序列化问题。
    """
    logger.info(f"[DEBUG] build_emotion_graph: memory_manager={'OK' if memory_manager else 'None'}")
    graph = StateGraph(AgentState)

    # 使用闭包创建节点函数，捕获依赖
    def memory_node_with_closure(state: AgentState) -> Dict:
        logger.info("🧠 [记忆 Agent] 开始检索记忆...")
        user_id = state["user_id"]
        user_message = state["user_message"]

        # 加载工作记忆
        working_memory_text = ""
        if working_memory_store:
            working_memory_text = working_memory_store.format_for_prompt(user_id)

        # 新增：加载档案卡
        profile_context = ""
        if profile_manager:
            profile = profile_manager.get_profile(user_id)
            if profile:
                profile_context = profile.to_prompt_context()

        # 查询改写：将口语化输入扩展为多个检索查询
        queries = rewrite_query(user_message)
        if len(queries) > 1:
            logger.info(f"[查询改写] 原始: {user_message[:30]} → {len(queries)} 个查询")

        retrieved = []
        if memory_manager:
            local_results = memory_manager.search_memories(user_id, user_message, limit=10, queries=queries)
            retrieved = [{"memory": m.content, "source": "local"} for m in local_results]
            logger.info(f"[记忆检索] 本地检索: {len(retrieved)} 条")

        memory_texts = [r.get("memory", "") for r in retrieved if r.get("memory")]

        llm = get_chat_client(temperature=0.3, use_thinking=False)
        if memory_texts:
            memory_content = "\n".join([f"- {m}" for m in memory_texts])
            system_msg = SystemMessage(content=MEMORY_AGENT_PROMPT)
            user_msg = HumanMessage(content=f"以下是检索到的记忆，请生成记忆摘要：\n\n{memory_content}")
            try:
                response = llm.invoke([system_msg, user_msg])
                content = response.content.strip()
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                result = json.loads(content)
                memory_context = result.get("memory_context", memory_content)
                memory_summary = result.get("memory_summary", "")
            except Exception:
                memory_context = memory_content
                memory_summary = f"共 {len(memory_texts)} 条相关记忆"
        else:
            memory_context = "暂无相关记忆"
            memory_summary = "新用户，暂无历史记忆"

        logger.info(f"✅ [记忆 Agent] 完成: {len(retrieved)} 条记忆")
        return {
            "retrieved_memories": retrieved,
            "memory_context": memory_context,
            "memory_summary": memory_summary,
            "working_memory_text": working_memory_text,
            "profile_context": profile_context,  # 新增：传递档案卡上下文
            "workflow_log": [f"[记忆检索] {len(retrieved)} 条相关记忆"],
        }

    def save_memory_node_with_closure(state: AgentState) -> Dict:
        user_id = state["user_id"]
        user_msg = state["user_message"]
        reply = state.get("assistant_reply", "")

        if not reply:
            return {"workflow_log": ["[记忆存储] 跳过，无回复"]}

        # 1. 更新工作记忆（现有逻辑）
        if working_memory_store:
            try:
                update_llm = get_chat_client(temperature=0.0, use_thinking=False)
                update_working_memory(working_memory_store, user_id, user_msg, reply, update_llm)
            except Exception as e:
                logger.warning(f"[工作记忆更新] 失败: {e}")

        # 2. 存储长期记忆（传递情感分析 Agent 的结果）
        if memory_manager:
            try:
                # 从情感分析 Agent 的结果中提取情感标签
                emotion_analysis = state.get("emotion_analysis")
                emotion_type = None
                emotion_intensity = None
                if emotion_analysis:
                    try:
                        emotion_type = EmotionType.from_string(emotion_analysis.get("current_emotion", ""))
                    except (ValueError, AttributeError):
                        emotion_type = None
                    emotion_intensity = emotion_analysis.get("emotion_intensity")
                
                memory_manager.extract_and_store_facts(
                    user_id, user_msg, reply,
                    category=MemoryCategory.EMOTION,
                    emotion=emotion_type,
                    emotion_intensity=emotion_intensity,
                )
                logger.info("💾 [记忆存储] 已保存")
            except Exception as e:
                logger.warning(f"[记忆存储] 失败: {e}")

        # 3. 新增：更新档案卡
        if profile_manager:
            try:
                from user_profile import ProfileUpdater
                profile_updater = ProfileUpdater(profile_manager)
                llm_client = get_chat_client(temperature=0.0, use_thinking=False)
                updated_fields = profile_updater.update_from_conversation(
                    user_id=user_id,
                    user_msg=user_msg,
                    assistant_msg=reply,
                    llm_client=llm_client,
                )
                if updated_fields:
                    logger.info(f"[档案卡更新] 用户 {user_id}: 更新了 {updated_fields}")
            except Exception as e:
                logger.warning(f"[档案卡更新] 失败: {e}")

        # 4. 新增：提取时间标签并附加到本次对话产生的所有记忆
        if memory_manager:
            try:
                from temporal_metadata import TemporalExtractor
                temporal = TemporalExtractor.extract_from_text(user_msg)
                if temporal.event_time or temporal.time_context or temporal.recurrence:
                    user_memories = memory_manager._get_user_memories(user_id)
                    now = time.time()
                    recent_memories = [
                        m for m in user_memories.values()
                        if now - m.created_at < 10  # 10 秒内的记忆
                    ]
                    for memory in recent_memories:
                        memory.temporal_data = temporal.to_dict()
                        memory_manager._dirty.add((user_id, memory.id))
                    if recent_memories:
                        memory_manager._save_to_disk()
                        logger.info(f"[时间标签] 为 {len(recent_memories)} 条记忆附加了时间标签")
            except Exception as e:
                logger.warning(f"[时间标签更新] 失败: {e}")

        return {"workflow_log": ["[记忆存储] 完成"]}

    # 添加节点
    graph.add_node("emotion_analysis", emotion_analysis_node)
    graph.add_node("memory_retrieval", memory_node_with_closure)
    graph.add_node("dialogue_generation", dialogue_agent_node)
    graph.add_node("memory_storage", save_memory_node_with_closure)

    # 设置边
    graph.set_entry_point("emotion_analysis")
    graph.add_edge("emotion_analysis", "memory_retrieval")
    graph.add_edge("memory_retrieval", "dialogue_generation")
    graph.add_edge("dialogue_generation", "memory_storage")
    graph.add_edge("memory_storage", END)

    return graph.compile()


# ================================================================
# 便捷调用函数
# ================================================================

def run_emotion_workflow(
    graph,
    user_id: str,
    user_message: str,
    conversation_history: List[Dict] = None,
    image_data: str = None,
) -> str:
    initial_state = {
        "user_id": user_id,
        "user_message": user_message,
        "conversation_history": conversation_history or [],
        "image_data": image_data,
        "emotion_analysis": None,
        "emotion_summary": None,
        "retrieved_memories": None,
        "memory_context": None,
        "memory_summary": None,
        "assistant_reply": None,
        "workflow_start_time": time.time(),
        "workflow_log": [],
    }

    result = graph.invoke(initial_state)

    reply = result.get("assistant_reply", "抱歉，我暂时无法回复。")
    
    total_time = time.time() - (result.get("workflow_start_time") or time.time())
    logger.info(f"📊 工作流完成 (总耗时: {total_time:.2f}s)")
    logger.info(f"📋 工作流日志: {' → '.join(result.get('workflow_log', []))}")

    return reply


def run_emotion_workflow_streaming(
    memory_manager: Optional[MemoryManager],
    user_id: str,
    user_message: str,
    conversation_history: List[Dict] = None,
    image_data: str = None,
    working_memory_store: Optional[WorkingMemoryStore] = None,
    profile_manager=None,
):
    """
    流式工作流：情感分析+记忆检索同步执行，对话生成逐 token 流式输出。
    
    返回 AsyncGenerator，每次 yield 一个 SSE 事件 dict:
      {'type': 'status', 'text': '...'}   — 状态更新
      {'type': 'token', 'text': '...'}    — 流式 token
      {'type': 'reply', 'text': '...'}    — 完整回复（流式结束后）
      {'type': 'error', 'text': '...'}    — 错误
    """
    import asyncio

    # 加载工作记忆
    working_memory_text = ""
    if working_memory_store:
        working_memory_text = working_memory_store.format_for_prompt(user_id)

    initial_state = {
        "user_id": user_id,
        "user_message": user_message,
        "conversation_history": conversation_history or [],
        "image_data": image_data,
        "emotion_analysis": None,
        "emotion_summary": None,
        "retrieved_memories": None,
        "memory_context": None,
        "memory_summary": None,
        "working_memory_text": working_memory_text,
        "assistant_reply": None,
        "workflow_start_time": time.time(),
        "workflow_log": [],
    }

    async def _stream():
        try:
            yield {'type': 'status', 'text': 'Giftia 正在感受你的情绪并回忆...'}

            emotion_result, memory_result = await asyncio.gather(
                asyncio.to_thread(emotion_analysis_node, initial_state),
                asyncio.to_thread(_run_memory_retrieval, initial_state, memory_manager, working_memory_store),
            )
            state = {**initial_state, **emotion_result, **memory_result}

            yield {'type': 'status', 'text': 'Giftia 正在组织语言...'}

            llm = get_chat_client(temperature=0.8, top_p=0.9)
            messages = _build_dialogue_messages(state)

            full_reply = ""
            token_queue: asyncio.Queue = asyncio.Queue()
            stream_error = [None]

            def _consume_stream():
                nonlocal full_reply
                try:
                    for chunk in llm.stream(messages):
                        token = chunk.content
                        if token:
                            full_reply += token
                            token_queue.put_nowait(token)
                except Exception as e:
                    stream_error[0] = e
                finally:
                    token_queue.put_nowait(None)

            stream_task = asyncio.create_task(asyncio.to_thread(_consume_stream))

            while True:
                token = await asyncio.wait_for(token_queue.get(), timeout=120.0)
                if token is None:
                    break
                yield {'type': 'token', 'text': token}

            await stream_task

            if stream_error[0]:
                raise stream_error[0]

            reply = full_reply.strip() or "抱歉，我暂时无法回复。"

            yield {'type': 'reply', 'text': reply}

            # 后台异步更新工作记忆和长期记忆，不阻塞响应
            async def _background_save():
                # 1. 更新工作记忆
                if working_memory_store:
                    try:
                        update_llm = get_chat_client(temperature=0.0, use_thinking=False)
                        await asyncio.to_thread(update_working_memory, working_memory_store, state.get("user_id", "default"), state.get("user_message", ""), reply, update_llm)
                    except Exception as e:
                        logger.warning(f"[流式工作记忆更新] 失败: {e}")

                # 2. 存储长期记忆（传递情感分析 Agent 的结果）
                if memory_manager:
                    try:
                        # 从情感分析 Agent 的结果中提取情感标签
                        emotion_analysis = state.get("emotion_analysis")
                        emotion_type = None
                        emotion_int = None
                        if emotion_analysis:
                            try:
                                emotion_type = EmotionType.from_string(emotion_analysis.get("current_emotion", ""))
                            except (ValueError, AttributeError):
                                emotion_type = None
                            emotion_int = emotion_analysis.get("emotion_intensity")
                        
                        await asyncio.to_thread(
                            memory_manager.extract_and_store_facts,
                            state.get("user_id", "default"),
                            state.get("user_message", ""),
                            reply,
                            MemoryCategory.EMOTION,
                            emotion_type,
                            emotion_int,
                        )
                        logger.info("💾 [流式记忆存储] 已保存")
                    except Exception as e:
                        logger.warning(f"[流式记忆存储] 失败: {e}")

                # 3. 新增：更新档案卡
                if profile_manager:
                    try:
                        from user_profile import ProfileUpdater
                        profile_updater = ProfileUpdater(profile_manager)
                        llm_client = get_chat_client(temperature=0.0, use_thinking=False)
                        updated_fields = await asyncio.to_thread(
                            profile_updater.update_from_conversation,
                            state.get("user_id", "default"),
                            state.get("user_message", ""),
                            reply,
                            llm_client,
                        )
                        if updated_fields:
                            logger.info(f"[档案卡更新] 用户 {state.get('user_id', 'default')}: 更新了 {updated_fields}")
                    except Exception as e:
                        logger.warning(f"[档案卡更新] 失败: {e}")

                # 4. 新增：提取时间标签
                if memory_manager:
                    try:
                        from temporal_metadata import TemporalExtractor
                        user_msg = state.get("user_message", "")
                        temporal = TemporalExtractor.extract_from_text(user_msg)
                        if temporal.event_time or temporal.time_context or temporal.recurrence:
                            user_memories = memory_manager._get_user_memories(state.get("user_id", "default"))
                            now = time.time()
                            recent_memories = [m for m in user_memories.values() if now - m.created_at < 10]
                            for memory in recent_memories:
                                memory.temporal_data = temporal.to_dict()
                                memory_manager._dirty.add((state.get("user_id", "default"), memory.id))
                            if recent_memories:
                                memory_manager._save_to_disk()
                                logger.info(f"[时间标签] 为 {len(recent_memories)} 条记忆附加了时间标签")
                    except Exception as e:
                        logger.warning(f"[时间标签更新] 失败: {e}")

            asyncio.create_task(_background_save())

            total_time = time.time() - (state.get("workflow_start_time") or time.time())
            logger.info(f"📊 流式工作流完成 (总耗时: {total_time:.2f}s)")

        except asyncio.TimeoutError:
            logger.error("流式工作流超时")
            yield {'type': 'error', 'text': '回复生成超时，请重试'}
        except Exception as e:
            logger.error(f"流式工作流失败: {e}", exc_info=True)
            yield {'type': 'error', 'text': str(e)}

    return _stream()


def _run_memory_retrieval(
    state: Dict,
    memory_manager: Optional[MemoryManager],
    working_memory_store: Optional[WorkingMemoryStore] = None,
) -> Dict:
    """独立运行记忆检索节点（供流式工作流调用）。"""
    user_id = state["user_id"]
    user_message = state["user_message"]

    # 加载工作记忆
    working_memory_text = ""
    if working_memory_store:
        working_memory_text = working_memory_store.format_for_prompt(user_id)

    # 查询改写
    queries = rewrite_query(user_message)
    if len(queries) > 1:
        logger.info(f"[查询改写] 原始: {user_message[:30]} → {len(queries)} 个查询")

    retrieved = []
    if memory_manager:
        local_results = memory_manager.search_memories(user_id, user_message, limit=10, queries=queries)
        retrieved = [{"memory": m.content, "source": "local"} for m in local_results]

    memory_texts = [r.get("memory", "") for r in retrieved if r.get("memory")]

    llm = get_chat_client(temperature=0.3, use_thinking=False)
    if memory_texts:
        memory_content = "\n".join([f"- {m}" for m in memory_texts])
        system_msg = SystemMessage(content=MEMORY_AGENT_PROMPT)
        user_msg = HumanMessage(content=f"以下是检索到的记忆，请生成记忆摘要：\n\n{memory_content}")
        try:
            response = llm.invoke([system_msg, user_msg])
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            result = json.loads(content)
            memory_context = result.get("memory_context", memory_content)
            memory_summary = result.get("memory_summary", "")
        except Exception:
            memory_context = memory_content
            memory_summary = f"共 {len(memory_texts)} 条相关记忆"
    else:
        memory_context = "暂无相关记忆"
        memory_summary = "新用户，暂无历史记忆"

    logger.info(f"✅ [记忆 Agent] 完成: {len(retrieved)} 条记忆")
    return {
        "retrieved_memories": retrieved,
        "memory_context": memory_context,
        "memory_summary": memory_summary,
        "working_memory_text": working_memory_text,
        "workflow_log": [f"[记忆检索] {len(retrieved)} 条相关记忆"],
    }
