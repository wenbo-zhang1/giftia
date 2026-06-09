"""
工作记忆模块 - 跨对话的动态上下文

解决：用户切换对话后 AI 丢失上下文的问题。

工作记忆 vs 长期记忆：
- 工作记忆：当前状态摘要，始终注入 system prompt，跨对话持久
- 长期记忆：具体事实/事件，按相关性检索，按遗忘曲线衰减
"""

import json
import time
import sqlite3
import threading
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class WorkingMemoryStore:
    """跨对话工作记忆存储（SQLite 持久化）。"""

    def __init__(self, db_path: str = ""):
        if not db_path:
            import os
            db_path = os.path.join(
                os.path.abspath(os.path.dirname(__file__)), "giftia.db"
            )
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.execute("PRAGMA journal_mode=WAL")
        return self._local.conn

    def _init_db(self):
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS working_memory (
                user_id TEXT PRIMARY KEY,
                summary TEXT NOT NULL DEFAULT '',
                open_topics TEXT NOT NULL DEFAULT '[]',
                current_emotion TEXT NOT NULL DEFAULT 'neutral',
                updated_at REAL NOT NULL DEFAULT 0
            )
        """)
        conn.commit()

    def load(self, user_id: str) -> Dict:
        """加载用户的工作记忆。"""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT summary, open_topics, current_emotion, updated_at FROM working_memory WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            return {"summary": "", "open_topics": [], "current_emotion": "neutral", "updated_at": 0}
        try:
            topics = json.loads(row[1])
        except (json.JSONDecodeError, TypeError):
            topics = []
        return {
            "summary": row[0],
            "open_topics": topics,
            "current_emotion": row[2],
            "updated_at": row[3],
        }

    def save(self, user_id: str, summary: str, open_topics: List[str], current_emotion: str):
        """保存用户的工作记忆。"""
        conn = self._get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO working_memory (user_id, summary, open_topics, current_emotion, updated_at)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, summary, json.dumps(open_topics, ensure_ascii=False), current_emotion, time.time()),
        )
        conn.commit()

    def format_for_prompt(self, user_id: str) -> str:
        """格式化工作记忆为可注入 prompt 的文本。"""
        data = self.load(user_id)
        if not data["summary"] and not data["open_topics"]:
            return ""

        parts = []
        if data["summary"]:
            parts.append(data["summary"])
        if data["open_topics"]:
            topics_text = "、".join(data["open_topics"][:5])
            parts.append(f"待跟进的话题：{topics_text}")
        if data["current_emotion"] and data["current_emotion"] != "neutral":
            parts.append(f"用户最近的情绪：{data['current_emotion']}")

        return "\n".join(parts)


WORKING_MEMORY_UPDATE_PROMPT = """你是一个记忆更新模块。请根据最新对话更新工作记忆。

工作记忆是跨对话持久保存的，用于让 AI 在不同对话间保持对用户的了解。

当前工作记忆：
{current_memory}

最新对话：
用户：{user_message}
AI：{assistant_reply}

请更新工作记忆，规则：
1. 保留仍然有效的信息
2. 添加新的重要信息（用户明确说出的）
3. 移除已过时或矛盾的信息
4. summary 控制在 200 字以内，只保留最重要的信息
5. open_topics 只保留尚未解决的话题（最多 5 个）
6. 禁止编造或推测任何信息

输出 JSON：
{{"summary": "更新后的整体了解", "open_topics": ["话题1"], "current_emotion": "情感标签"}}"""


def update_working_memory(
    store: WorkingMemoryStore,
    user_id: str,
    user_message: str,
    assistant_reply: str,
    llm_client=None,
):
    """使用 LLM 更新工作记忆，LLM 不可用时降级到规则更新。"""
    current = store.load(user_id)

    if llm_client is None:
        _rule_based_update(store, user_id, current, user_message, assistant_reply)
        return

    current_memory_text = current["summary"]
    if current["open_topics"]:
        current_memory_text += f"\n待跟进：{'、'.join(current['open_topics'])}"
    if not current_memory_text.strip():
        current_memory_text = "（空，这是第一次对话）"

    from langchain_core.messages import HumanMessage

    prompt = WORKING_MEMORY_UPDATE_PROMPT.format(
        current_memory=current_memory_text,
        user_message=user_message[:500],
        assistant_reply=assistant_reply[:500],
    )

    try:
        response = llm_client.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()

        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        result = json.loads(content)
        store.save(
            user_id=user_id,
            summary=result.get("summary", current["summary"]),
            open_topics=result.get("open_topics", current["open_topics"]),
            current_emotion=result.get("current_emotion", current["current_emotion"]),
        )
        logger.info(f"[工作记忆] 已更新 (用户: {user_id})")
    except Exception as e:
        logger.warning(f"[工作记忆] LLM 更新失败，使用规则更新: {e}")
        _rule_based_update(store, user_id, current, user_message, assistant_reply)


def _rule_based_update(
    store: WorkingMemoryStore,
    user_id: str,
    current: Dict,
    user_message: str,
    assistant_reply: str,
):
    """基于规则的简单工作记忆更新（LLM 不可用时的降级方案）。"""
    from memory_manager import EmotionAnalyzer

    summary = current["summary"]
    open_topics = list(current["open_topics"])

    # 情感更新
    emotion, _ = EmotionAnalyzer.analyze(user_message)
    current_emotion = emotion.value if emotion.value != "neutral" else current["current_emotion"]

    # 简单追加到摘要（限制长度）
    if len(user_message.strip()) >= 4:
        new_info = user_message.strip()[:80]
        if new_info not in summary:
            if summary:
                summary = summary + f"；最近提到：{new_info}"
            else:
                summary = f"最近提到：{new_info}"
            if len(summary) > 300:
                summary = summary[-300:]

    store.save(user_id, summary, open_topics, current_emotion)
