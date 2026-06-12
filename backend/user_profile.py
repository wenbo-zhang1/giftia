"""
用户档案卡模块 - 结构化的用户画像

职责：存储结构化的用户事实信息（字段级）
与 WorkingMemory 的关系：档案卡是工作记忆的结构化子集
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import time
import json
import threading
import sqlite3
import logging

logger = logging.getLogger(__name__)


# ================================================================
# 档案卡数据结构
# ================================================================

@dataclass
class UserProfile:
    """用户结构化档案卡
    
    职责：存储结构化的用户事实信息（字段级）
    与 WorkingMemory 的关系：档案卡是工作记忆的结构化子集
    """
    
    user_id: str
    identity: Dict[str, Optional[str]] = field(default_factory=dict)
    preferences: Dict[str, List[str]] = field(default_factory=dict)
    relationships: Dict[str, Any] = field(default_factory=dict)
    emotional_profile: Dict[str, Any] = field(default_factory=dict)
    
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    version: int = 1
    
    def to_dict(self) -> Dict:
        """转换为字典（用于 JSON 序列化）"""
        return {
            "identity": self.identity,
            "preferences": self.preferences,
            "relationships": self.relationships,
            "emotional_profile": self.emotional_profile,
        }
    
    @classmethod
    def from_dict(cls, user_id: str, data: Dict) -> "UserProfile":
        """从字典创建档案卡"""
        return cls(
            user_id=user_id,
            identity=data.get("identity", {}),
            preferences=data.get("preferences", {}),
            relationships=data.get("relationships", {}),
            emotional_profile=data.get("emotional_profile", {}),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            version=data.get("version", 1),
        )
    
    def to_prompt_context(self) -> str:
        """生成用于 System Prompt 的档案卡摘要"""
        parts = []
        
        # 基本信息
        if self.identity.get("name"):
            parts.append(f"用户名叫{self.identity['name']}")
        if self.identity.get("age"):
            parts.append(f"{self.identity['age']}岁")
        if self.identity.get("occupation"):
            parts.append(f"从事{self.identity['occupation']}工作")
        
        # 喜好
        if self.preferences.get("hobbies"):
            hobbies = "、".join(self.preferences["hobbies"][:3])
            parts.append(f"喜欢{hobbies}")
        
        # 情感模式
        if self.emotional_profile.get("recent_mood_trend"):
            parts.append(f"最近心情{self.emotional_profile['recent_mood_trend']}")
        
        if not parts:
            return ""
        
        return "你认识的用户：" + "，".join(parts) + "。"


# ================================================================
# 档案卡管理器
# ================================================================

class ProfileManager:
    """档案卡管理器（线程安全，带连接关闭机制）"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._cache = {}  # user_id -> UserProfile
        self._cache_lock = threading.Lock()
        self._cache_ttl = 300  # 5分钟 TTL
        self._cache_timestamps = {}  # user_id -> timestamp
        self._connections = []  # 所有连接的列表（用于 close）
        self._connections_lock = threading.Lock()
        self._local = threading.local()
        self._init_db()  # 初始化数据库表
    
    def _init_db(self):
        """创建 user_profiles 表（如果不存在）"""
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                profile_data TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                version INTEGER DEFAULT 1
            )
        """)
        conn.commit()
    
    def _get_conn(self) -> sqlite3.Connection:
        """获取当前线程的数据库连接"""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            # 记录连接（用于 close）
            with self._connections_lock:
                self._connections.append(self._local.conn)
        return self._local.conn
    
    def close(self):
        """关闭所有数据库连接（在 FastAPI shutdown 时调用）
        
        修复：遍历关闭所有线程的连接，而不仅是当前线程
        """
        with self._connections_lock:
            for conn in self._connections:
                try:
                    conn.close()
                except Exception:
                    pass
            self._connections.clear()
        
        # 清理当前线程的连接
        if hasattr(self._local, "conn") and self._local.conn:
            try:
                self._local.conn.close()
            except Exception:
                pass
            self._local.conn = None
        
        # 清理缓存
        with self._cache_lock:
            self._cache.clear()
            self._cache_timestamps.clear()
    
    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """获取用户档案卡（带缓存和 TTL）"""
        with self._cache_lock:
            if user_id in self._cache:
                # 检查 TTL
                cached_time = self._cache_timestamps.get(user_id, 0)
                if time.time() - cached_time < self._cache_ttl:
                    return self._cache[user_id]
        
        # 从数据库加载
        profile = self._load_from_db(user_id)
        
        if profile:
            with self._cache_lock:
                self._cache[user_id] = profile
                self._cache_timestamps[user_id] = time.time()
        
        return profile
    
    def _load_from_db(self, user_id: str) -> Optional[UserProfile]:
        """从数据库加载档案卡"""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT profile_data, created_at, updated_at, version FROM user_profiles WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        
        if not row:
            return None
        
        data = json.loads(row[0])
        data["created_at"] = row[1]
        data["updated_at"] = row[2]
        data["version"] = row[3]
        
        return UserProfile.from_dict(user_id, data)
    
    def save_profile(self, profile: UserProfile):
        """保存档案卡到数据库（同时更新缓存）"""
        profile.updated_at = time.time()
        
        conn = self._get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO user_profiles 
               (user_id, profile_data, created_at, updated_at, version)
               VALUES (?, ?, ?, ?, ?)""",
            (profile.user_id, json.dumps(profile.to_dict(), ensure_ascii=False),
             profile.created_at, profile.updated_at, profile.version)
        )
        conn.commit()
        
        with self._cache_lock:
            self._cache[profile.user_id] = profile
            self._cache_timestamps[profile.user_id] = time.time()


# ================================================================
# 档案卡自动更新器
# ================================================================

PROFILE_EXTRACTION_PROMPT = """你是一个用户档案提取专家。请从以下对话中提取适合填入用户档案卡的信息。

对话：
用户：{user_msg}
AI：{assistant_msg}

档案卡字段：
1. identity（基本信息）：name（姓名）、age（年龄）、gender（性别）、occupation（职业）、location（地点）
2. preferences（喜好）：hobbies（爱好）、music（音乐）、movies（电影）、books（书籍）、food（食物）、other（其他）
3. relationships（人际关系）：family（家人，数组，每项包含 relation/name/description）、friends（朋友，数组，每项包含 name/description）、romantic（恋爱状态，对象，包含 status/partner_name）
4. emotional_profile（情感模式）：common_triggers（触发因素）、coping_strategies（应对策略）、recent_mood_trend（最近心情趋势）、support_preferences（支持偏好）

严格规则：
1. 只提取用户**明确说出**的信息，禁止推测
2. 如果某个字段没有新信息，返回空
3. 使用 JSON 格式返回，键为字段路径（如 "identity.name"），值为提取的内容
4. 对于数组字段（如 hobbies），返回完整数组，不是追加
5. 对于嵌套对象（如 romantic），返回完整对象（如 "relationships.romantic": {{"status": "单身"}}）

示例输出：
{{
  "identity.name": "小明",
  "identity.age": 25,
  "preferences.hobbies": ["编程", "旅行"],
  "relationships.family": [{{"relation": "母亲", "name": "张妈妈", "description": "关系很好"}}],
  "relationships.romantic": {{"status": "单身"}}
}}

请提取信息（如果没有新信息，返回 {{}}）：
"""


class ProfileUpdater:
    """档案卡自动更新器"""
    
    def __init__(self, profile_manager: ProfileManager):
        self.profile_manager = profile_manager
    
    def update_from_conversation(
        self,
        user_id: str,
        user_msg: str,
        assistant_msg: str,
        llm_client=None,
    ) -> List[str]:
        """从对话中自动更新档案卡
        
        Args:
            user_id: 用户 ID
            user_msg: 用户消息
            assistant_msg: AI 回复
            llm_client: LLM 客户端（可选，不可用时降级到规则提取）
        
        Returns:
            更新的字段路径列表
        """
        if llm_client is None:
            return self._rule_based_update(user_id, user_msg, assistant_msg)
        
        try:
            # 1. 使用 LLM 提取档案信息
            extracted_data = self._extract_profile_facts(user_msg, assistant_msg, llm_client)
            
            if not extracted_data:
                return []
            
            # 2. 获取当前档案卡
            profile = self.profile_manager.get_profile(user_id)
            if not profile:
                profile = UserProfile(user_id=user_id)
            
            # 3. 更新档案卡
            updated_fields = self._apply_extractions(profile, extracted_data)
            
            # 4. 保存
            if updated_fields:
                profile.version += 1
                self.profile_manager.save_profile(profile)
                logger.info(f"[档案卡更新] 用户 {user_id}: 更新了 {updated_fields}")
            
            return updated_fields
            
        except Exception as e:
            logger.warning(f"[档案卡更新] LLM 提取失败，降级到规则提取: {e}")
            return self._rule_based_update(user_id, user_msg, assistant_msg)
    
    def _extract_profile_facts(self, user_msg: str, assistant_msg: str, llm_client) -> Dict:
        """使用 LLM 提取档案相关事实"""
        from langchain_core.messages import HumanMessage
        
        prompt = PROFILE_EXTRACTION_PROMPT.format(
            user_msg=user_msg[:1000],
            assistant_msg=assistant_msg[:1000],
        )
        
        response = llm_client.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        
        # 解析 JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.warning(f"[档案卡提取] JSON 解析失败: {content[:100]}")
            return {}
    
    def _apply_extractions(self, profile: UserProfile, extracted_data: Dict) -> List[str]:
        """将提取的数据应用到档案卡
        
        修复：支持两层和三层路径
        """
        updated_fields = []
        
        for field_path, value in extracted_data.items():
            parts = field_path.split(".")
            
            if len(parts) == 2:
                # 两层路径：section.field
                section, field = parts
                
                if section == "identity" and hasattr(profile, "identity"):
                    if profile.identity.get(field) != value:
                        profile.identity[field] = value
                        updated_fields.append(field_path)
                
                elif section == "preferences" and hasattr(profile, "preferences"):
                    if profile.preferences.get(field) != value:
                        profile.preferences[field] = value
                        updated_fields.append(field_path)
                
                elif section == "relationships" and hasattr(profile, "relationships"):
                    if profile.relationships.get(field) != value:
                        profile.relationships[field] = value
                        updated_fields.append(field_path)
                
                elif section == "emotional_profile" and hasattr(profile, "emotional_profile"):
                    if profile.emotional_profile.get(field) != value:
                        profile.emotional_profile[field] = value
                        updated_fields.append(field_path)
            
            elif len(parts) == 3:
                # 三层路径：section.subsection.field（如 relationships.romantic.status）
                section, subsection, field = parts
                
                if section == "relationships" and hasattr(profile, "relationships"):
                    if subsection not in profile.relationships:
                        profile.relationships[subsection] = {}
                    
                    if isinstance(profile.relationships[subsection], dict):
                        if profile.relationships[subsection].get(field) != value:
                            profile.relationships[subsection][field] = value
                            updated_fields.append(field_path)
                
                elif section == "emotional_profile" and hasattr(profile, "emotional_profile"):
                    if subsection not in profile.emotional_profile:
                        profile.emotional_profile[subsection] = {}
                    
                    if isinstance(profile.emotional_profile[subsection], dict):
                        if profile.emotional_profile[subsection].get(field) != value:
                            profile.emotional_profile[subsection][field] = value
                            updated_fields.append(field_path)
        
        return updated_fields
    
    def _rule_based_update(self, user_id: str, user_msg: str, assistant_msg: str) -> List[str]:
        """基于规则的简单更新（LLM 不可用时的降级方案）"""
        profile = self.profile_manager.get_profile(user_id)
        if not profile:
            profile = UserProfile(user_id=user_id)
        
        updated_fields = []
        
        # 简单的规则提取（示例）
        if "我叫" in user_msg:
            name = user_msg.split("我叫")[1].split()[0].strip()
            if profile.identity.get("name") != name:
                profile.identity["name"] = name
                updated_fields.append("identity.name")
        
        if "我今年" in user_msg and "岁" in user_msg:
            try:
                age = int(user_msg.split("我今年")[1].split("岁")[0].strip())
                if profile.identity.get("age") != age:
                    profile.identity["age"] = age
                    updated_fields.append("identity.age")
            except (ValueError, IndexError):
                pass
        
        if updated_fields:
            profile.version += 1
            self.profile_manager.save_profile(profile)
        
        return updated_fields
