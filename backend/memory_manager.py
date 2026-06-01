"""
情感记忆管理器 - 高级记忆系统

功能：
1. 情感标签系统：自动识别和标记记忆的情感属性
2. 记忆重要性评分：基于多维度评估记忆的重要性
3. 遗忘曲线机制：基于艾宾浩斯遗忘曲线的记忆衰减与巩固
4. 记忆合并与清理：自动合并相似记忆，清理低价值记忆

设计目标：
- 展示功能：展示完整的记忆系统设计能力
- 模块化设计：可与 Mem0 配合使用，也可独立运行
"""

import os
import json
import time
import math
import hashlib
import datetime
import logging
import sqlite3
import threading
import numpy as np
from typing import List, Dict, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field, asdict
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logger.addHandler(handler)


# ================================================================
# 枚举定义
# ================================================================

class EmotionType(Enum):
    """情感标签枚举。"""
    HAPPY = "happy"
    SAD = "sad"
    ANXIOUS = "anxious"
    ANGRY = "angry"
    NEUTRAL = "neutral"
    EXCITED = "excited"
    FEARFUL = "fearful"
    GRATEFUL = "grateful"
    LONELY = "lonely"
    HOPEFUL = "hopeful"
    STRESSED = "stressed"
    RELIEVED = "relieved"

    @classmethod
    def from_string(cls, emotion: str) -> "EmotionType":
        mapping = {
            "开心": cls.HAPPY, "快乐": cls.HAPPY, "高兴": cls.HAPPY, "愉快": cls.HAPPY, "兴奋": cls.EXCITED, "激动": cls.EXCITED,
            "难过": cls.SAD, "悲伤": cls.SAD, "伤心": cls.SAD, "失落": cls.SAD, "沮丧": cls.SAD, "孤独": cls.LONELY,
            "焦虑": cls.ANXIOUS, "紧张": cls.ANXIOUS, "压力": cls.STRESSED, "担忧": cls.ANXIOUS, "害怕": cls.FEARFUL,
            "生气": cls.ANGRY, "愤怒": cls.ANGRY, "烦躁": cls.ANGRY,
            "感恩": cls.GRATEFUL, "感谢": cls.GRATEFUL, "谢谢": cls.GRATEFUL,
            "希望": cls.HOPEFUL, "期待": cls.HOPEFUL, "放心": cls.RELIEVED,
            "平静": cls.NEUTRAL, "一般": cls.NEUTRAL, "没事": cls.NEUTRAL,
        }
        return mapping.get(emotion, cls.NEUTRAL)

    def to_emoji(self) -> str:
        emoji_map = {
            EmotionType.HAPPY: "😊", EmotionType.SAD: "😢", EmotionType.ANXIOUS: "😰",
            EmotionType.ANGRY: "😠", EmotionType.NEUTRAL: "😐", EmotionType.EXCITED: "🤩",
            EmotionType.FEARFUL: "😨", EmotionType.GRATEFUL: "🙏", EmotionType.LONELY: "😔",
            EmotionType.HOPEFUL: "🌟", EmotionType.STRESSED: "😫", EmotionType.RELIEVED: "😌",
        }
        return emoji_map.get(self, "😐")


class MemoryCategory(Enum):
    """记忆分类。"""
    EMOTION = "emotion"       # 情感状态/事件
    FACT = "fact"             # 事实信息（职业、喜好等）
    RELATIONSHIP = "relationship"  # 人际关系
    EVENT = "event"           # 重要事件
    PREFERENCE = "preference"     # 个人偏好
    GOAL = "goal"             # 目标/愿望
    CONCERN = "concern"       # 担忧/困扰


# ================================================================
# 数据模型
# ================================================================

@dataclass
class MemoryItem:
    """单条记忆数据结构。"""
    id: str                           # 记忆唯一 ID
    content: str                      # 记忆内容
    emotion: EmotionType = EmotionType.NEUTRAL   # 情感标签
    category: MemoryCategory = MemoryCategory.FACT  # 记忆分类
    importance: float = 0.5           # 重要性评分 (0-1)
    access_count: int = 0             # 被检索次数
    created_at: float = field(default_factory=time.time)  # 创建时间
    last_accessed: float = 0.0        # 最后访问时间
    emotion_intensity: float = 0.5    # 情感强度 (0-1)
    tags: List[str] = field(default_factory=list)  # 关键词标签
    is_consolidated: bool = False     # 是否已巩固
    embedding: Optional[List[float]] = None  # 语义向量

    def to_dict(self) -> Dict:
        d = {
            "id": self.id,
            "content": self.content,
            "emotion": self.emotion.value,
            "category": self.category.value,
            "importance": self.importance,
            "access_count": self.access_count,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "emotion_intensity": self.emotion_intensity,
            "tags": self.tags,
            "is_consolidated": self.is_consolidated,
        }
        if self.embedding is not None:
            d["embedding"] = self.embedding
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> "MemoryItem":
        data = dict(data)
        data["emotion"] = EmotionType(data["emotion"])
        data["category"] = MemoryCategory(data["category"])
        if "embedding" not in data:
            data["embedding"] = None
        return cls(**data)


# ================================================================
# 遗忘曲线
# ================================================================

class EbbinghausCurve:
    """
    艾宾浩斯遗忘曲线实现。
    
    遗忘率公式: R = e^(-t/S)
    R: 记忆保留率
    t: 经过时间（小时）
    S: 记忆强度系数（与重要性和复习次数相关）
    """

    @staticmethod
    def retention_rate(created_at: float, last_accessed: float, importance: float, access_count: int) -> float:
        """
        计算当前记忆保留率。
        
        参数：
        - created_at: 记忆创建时间戳
        - last_accessed: 最后访问时间戳
        - importance: 重要性评分
        - access_count: 访问次数
        
        返回：
        - 记忆保留率 (0-1)
        """
        now = time.time()
        elapsed_hours = (now - (last_accessed or created_at)) / 3600

        # 记忆强度系数：基础强度 + 重要性加成 + 复习次数加成
        # 复习次数越多，遗忘越慢（间隔重复效应）
        base_strength = 0.3
        importance_factor = importance * 0.5
        review_factor = min(access_count * 0.15, 1.0)
        strength = base_strength + importance_factor + review_factor

        # 艾宾浩斯遗忘曲线
        retention = math.exp(-elapsed_hours / (strength * 24 + 1))
        return max(0.0, min(1.0, retention))

    @staticmethod
    def should_consolidate(memory: MemoryItem, threshold: float = 0.3) -> bool:
        """
        判断是否需要巩固（重新复习）该记忆。
        
        当记忆保留率低于阈值且不是已巩固状态时，需要巩固。
        """
        if memory.is_consolidated:
            return False
        retention = EbbinghausCurve.retention_rate(
            memory.created_at, memory.last_accessed,
            memory.importance, memory.access_count
        )
        return retention < threshold

    @staticmethod
    def decay_importance(memory: MemoryItem) -> float:
        """
        根据遗忘曲线衰减记忆的重要性。
        
        被频繁访问的记忆重要性会提升，长期未被访问的记忆重要性会下降。
        """
        retention = EbbinghausCurve.retention_rate(
            memory.created_at, memory.last_accessed,
            memory.importance, memory.access_count
        )
        # 新的重要性 = 原重要性 * 保留率 + 基础值
        new_importance = memory.importance * retention * 0.8 + 0.1
        return max(0.0, min(1.0, new_importance))


# ================================================================
# 语义向量服务
# ================================================================

class EmbeddingService:
    """
    语义向量服务：调用智谱 Embedding API 生成文本向量。
    
    用于记忆的语义检索，替代纯关键词匹配。
    API 不可用时自动降级到关键词匹配。
    """

    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is not None:
            return
        try:
            from model_config import EMBED_MODEL, EMBED_BASE_URL, EMBED_PROVIDER, resolve_api_key
            api_key = resolve_api_key(EMBED_PROVIDER)
            from openai import OpenAI
            self._client = OpenAI(api_key=api_key, base_url=EMBED_BASE_URL.rsplit("/", 1)[0])
            self._model = EMBED_MODEL
            logger.info(f"[EmbeddingService] 初始化成功, model={EMBED_MODEL}")
        except Exception as e:
            logger.warning(f"[EmbeddingService] 初始化失败: {e}, 将降级到关键词匹配")
            self._client = None

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """获取文本的语义向量。"""
        if self._client is None:
            return None
        try:
            resp = self._client.embeddings.create(
                model=self._model,
                input=text,
            )
            return resp.data[0].embedding
        except Exception as e:
            logger.warning(f"[EmbeddingService] 获取向量失败: {e}")
            return None

    def get_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """批量获取文本的语义向量。"""
        if self._client is None:
            return [None] * len(texts)
        try:
            resp = self._client.embeddings.create(
                model=self._model,
                input=texts,
            )
            sorted_data = sorted(resp.data, key=lambda x: x.index)
            return [d.embedding for d in sorted_data]
        except Exception as e:
            logger.warning(f"[EmbeddingService] 批量获取向量失败: {e}")
            return [None] * len(texts)

    @staticmethod
    def cosine_similarity(a: List[float], b: List[float]) -> float:
        """计算两个向量的余弦相似度。"""
        va = np.array(a)
        vb = np.array(b)
        norm_a = np.linalg.norm(va)
        norm_b = np.linalg.norm(vb)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(va, vb) / (norm_a * norm_b))


# ================================================================
# 情感分析器（基于规则的轻量级实现）
# ================================================================

class EmotionAnalyzer:
    """
    基于关键词的情感分析器。
    
    用于从对话文本中识别情感标签和情感强度。
    生产环境可以替换为 LLM 调用或专门的 NLP 模型。
    """

    EMOTION_KEYWORDS = {
        EmotionType.HAPPY: [
            "开心", "快乐", "高兴", "愉快", "幸福", "满足", "太好了", "棒", "爽",
            "笑", "好玩", "有趣", "喜欢", "爱", "期待", "惊喜", "顺利", "成功",
        ],
        EmotionType.SAD: [
            "难过", "悲伤", "伤心", "失落", "沮丧", "哭", "痛苦", "绝望",
            "无奈", "失望", "心碎", "眼泪", "不开心", "郁闷", "低落",
        ],
        EmotionType.ANXIOUS: [
            "焦虑", "紧张", "担心", "害怕", "不安", "惶恐", "压力", "喘不过气",
            "忐忑", "不安", "忧虑", "发愁", "纠结",
        ],
        EmotionType.ANGRY: [
            "生气", "愤怒", "恼火", "烦躁", "烦", "讨厌", "恨", "不爽",
            " rage", "发火", "暴躁",
        ],
        EmotionType.EXCITED: [
            "兴奋", "激动", "期待", "迫不及待", "振奋", "狂热",
        ],
        EmotionType.FEARFUL: [
            "害怕", "恐惧", "恐慌", "吓死", "不敢", "畏惧", "胆怯",
        ],
        EmotionType.GRATEFUL: [
            "感谢", "谢谢", "感恩", "感激", "多亏", "幸好",
        ],
        EmotionType.LONELY: [
            "孤独", "寂寞", "孤单", "一个人", "没人陪", "冷落",
        ],
        EmotionType.HOPEFUL: [
            "希望", "期待", "相信", "一定", "会好的", "努力", "未来",
        ],
        EmotionType.STRESSED: [
            "压力", "累", "疲惫", "受不了", "崩溃", "撑不住", "喘不过气",
            "加班", "考试", " deadline",
        ],
        EmotionType.RELIEVED: [
            "放心", "安心", "松了一口气", "还好", "总算", "解脱",
        ],
    }

    INTENSIFIERS = ["非常", "特别", "超级", "极其", "万分", "太", "真的很", "特别", "格外", "十分"]
    NEGATORS = ["不", "没", "别", "别", "别要", "没有", "并非", "并不"]

    @classmethod
    def analyze(cls, text: str) -> Tuple[EmotionType, float]:
        """
        分析文本情感，返回情感标签和强度。
        
        参数：
        - text: 待分析的文本
        
        返回：
        - (情感标签, 情感强度 0-1)
        """
        scores = {}
        for emotion, keywords in cls.EMOTION_KEYWORDS.items():
            score = 0.0
            for kw in keywords:
                if kw in text:
                    # 基础分
                    score += 0.3
                    # 检查是否有程度副词
                    for intensifier in cls.INTENSIFIERS:
                        if intensifier + kw in text or intensifier in text:
                            score += 0.2
                    # 检查是否有否定词（简单处理）
                    for negator in cls.NEGATORS:
                        if negator + kw in text:
                            score -= 0.2
            scores[emotion] = max(0.0, score)

        # 找到最高分的情感
        if not scores or max(scores.values()) == 0:
            return EmotionType.NEUTRAL, 0.0

        dominant_emotion = max(scores, key=scores.get)
        intensity = min(1.0, scores[dominant_emotion])
        return dominant_emotion, intensity


# ================================================================
# 记忆重要性评估器
# ================================================================

class ImportanceScorer:
    """
    记忆重要性评分器。
    
    评分维度：
    1. 情感强度：情感越强烈，记忆越重要
    2. 信息密度：包含的事实信息越多，越重要
    3. 用户关注度：被检索次数越多，越重要
    4. 时间衰减：新记忆初始分高，老记忆需要维持
    """

    INFO_INDICATORS = [
        "叫", "是", "喜欢", "讨厌", "工作", "住", "在", "有", "毕业于",
        "来自", "年龄", "岁", "职业", "专业", " hobby", "兴趣",
        "家人", "朋友", "同事", "同学",
    ]

    @classmethod
    def calculate(cls, content: str, emotion: EmotionType, emotion_intensity: float, access_count: int = 0) -> float:
        """
        计算记忆重要性评分。
        
        参数：
        - content: 记忆内容
        - emotion: 情感标签
        - emotion_intensity: 情感强度
        - access_count: 被访问次数
        
        返回：
        - 重要性评分 (0-1)
        """
        # 1. 情感强度分（0-0.4）
        emotion_score = emotion_intensity * 0.4

        # 2. 信息密度分（0-0.3）
        info_score = 0.0
        for indicator in cls.INFO_INDICATORS:
            if indicator in content:
                info_score += 0.05
        info_score = min(0.3, info_score)

        # 3. 用户关注度分（0-0.2）
        access_score = min(0.2, access_count * 0.04)

        # 4. 内容长度分（0-0.1）
        length_score = min(0.1, len(content) / 200)

        total = emotion_score + info_score + access_score + length_score
        return max(0.0, min(1.0, round(total, 3)))


# ================================================================
# 记忆管理器（核心）
# ================================================================

class MemoryManager:
    """
    高级记忆管理器。
    
    功能：
    - 记忆的创建、检索、更新、删除
    - 情感标签自动标注
    - 重要性评分
    - 遗忘曲线管理
    - 记忆合并与清理
    - 持久化存储
    """

    def __init__(self, storage_path: str = "./memory_store"):
        self.storage_path = storage_path
        self.db_path = os.path.join(
            os.path.abspath(os.path.dirname(__file__)), "giftia.db"
        )
        self._local = threading.local()
        self._conn_lock = threading.Lock()
        self.emotion_analyzer = EmotionAnalyzer()
        self.importance_scorer = ImportanceScorer()
        self.embedding_service = EmbeddingService()
        self.memories: Dict[str, Dict[str, MemoryItem]] = {}
        self._dirty: set = set()
        self._init_db()
        self._load_from_disk()

    def _get_user_memories(self, user_id: str) -> Dict[str, MemoryItem]:
        if user_id not in self.memories:
            self.memories[user_id] = {}
        return self.memories[user_id]

    def _generate_id(self, content: str, user_id: str) -> str:
        """生成记忆唯一 ID。"""
        raw = f"{user_id}:{content}:{time.time()}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    def add_memory(
        self,
        user_id: str,
        content: str,
        category: MemoryCategory = MemoryCategory.FACT,
        emotion: Optional[EmotionType] = None,
        emotion_intensity: Optional[float] = None,
    ) -> MemoryItem:
        """
        添加新记忆。
        
        参数：
        - user_id: 用户 ID
        - content: 记忆内容
        - category: 记忆分类
        - emotion: 情感标签（不传则自动分析）
        - emotion_intensity: 情感强度（不传则自动分析）
        """
        # 自动情感分析
        if emotion is None or emotion_intensity is None:
            auto_emotion, auto_intensity = self.emotion_analyzer.analyze(content)
            emotion = emotion or auto_emotion
            emotion_intensity = emotion_intensity if emotion_intensity is not None else auto_intensity

        # 计算重要性
        importance = self.importance_scorer.calculate(content, emotion, emotion_intensity)

        tags = []
        for kw in self.importance_scorer.INFO_INDICATORS:
            if kw in content:
                tags.append(kw)
        for etype, keywords in self.emotion_analyzer.EMOTION_KEYWORDS.items():
            for kw in keywords:
                if kw in content and kw not in tags:
                    tags.append(kw)
                    break
        tags = tags[:5]

        memory_id = self._generate_id(content, user_id)
        memory = MemoryItem(
            id=memory_id,
            content=content,
            emotion=emotion,
            category=category,
            importance=importance,
            emotion_intensity=emotion_intensity,
            last_accessed=time.time(),
            tags=tags,
        )

        # 生成语义向量
        embedding = self.embedding_service.get_embedding(content)
        if embedding is not None:
            memory.embedding = embedding

        user_memories = self._get_user_memories(user_id)
        user_memories[memory_id] = memory
        self._dirty.add((user_id, memory_id))

        user_mem_count = len(user_memories)
        if user_mem_count > 50 and user_mem_count % 10 == 0:
            pruned = self.prune_memories(user_id)
            if pruned:
                logger.info(f"[遗忘曲线] 清理了 {len(pruned)} 条低价值记忆 (用户: {user_id})")

        self._save_to_disk()
        return memory

    def search_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 5,
        emotion_filter: Optional[EmotionType] = None,
        min_importance: float = 0.0,
    ) -> List[MemoryItem]:
        """
        检索记忆。
        
        优先使用语义匹配（Embedding 余弦相似度），
        API 不可用或无向量数据时降级到关键词匹配。
        """
        user_memories = self._get_user_memories(user_id)
        if not user_memories:
            return []

        # 尝试语义匹配
        query_embedding = self.embedding_service.get_embedding(query)
        has_embeddings = any(m.embedding is not None for m in user_memories.values())

        if query_embedding is not None and has_embeddings:
            results = self._semantic_search(user_memories, query_embedding, emotion_filter, min_importance)
            if results:
                for m in results:
                    self._dirty.add((user_id, m.id))
                self._save_to_disk()
                return results[:limit]

        results = self._keyword_search(user_memories, query, emotion_filter, min_importance)
        results.sort(key=lambda x: x[0], reverse=True)
        selected = results[:limit]

        for _, m in selected:
            self._dirty.add((user_id, m.id))
        self._save_to_disk()
        return [m for _, m in selected]

    def _semantic_search(
        self,
        user_memories: Dict[str, MemoryItem],
        query_embedding: List[float],
        emotion_filter: Optional[EmotionType],
        min_importance: float,
    ) -> List[MemoryItem]:
        """语义匹配检索：基于 Embedding 余弦相似度。"""
        # 对无 embedding 的记忆按需补算
        memories_without_embedding = [
            m for m in user_memories.values()
            if m.embedding is None and m.importance >= min_importance
        ]
        if memories_without_embedding:
            texts = [m.content for m in memories_without_embedding]
            embeddings = self.embedding_service.get_embeddings_batch(texts)
            for m, emb in zip(memories_without_embedding, embeddings):
                if emb is not None:
                    m.embedding = emb

        results = []
        for memory in user_memories.values():
            if memory.importance < min_importance:
                continue
            if emotion_filter and memory.emotion != emotion_filter:
                continue
            if memory.embedding is None:
                continue

            similarity = EmbeddingService.cosine_similarity(query_embedding, memory.embedding)
            # 综合评分：语义相似度 * 0.7 + 重要性 * 0.3
            score = similarity * 0.7 + memory.importance * 0.3
            if score > 0.1:
                memory.access_count += 1
                memory.last_accessed = time.time()
                results.append((score, memory))

        results.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in results]

    def _keyword_search(
        self,
        user_memories: Dict[str, MemoryItem],
        query: str,
        emotion_filter: Optional[EmotionType],
        min_importance: float,
    ) -> List[Tuple[float, MemoryItem]]:
        """关键词匹配检索（原有逻辑，作为 fallback）。"""
        results = []
        for memory in user_memories.values():
            if memory.importance < min_importance:
                continue
            if emotion_filter and memory.emotion != emotion_filter:
                continue
            score = self._match_score(memory, query)
            if score > 0:
                memory.access_count += 1
                memory.last_accessed = time.time()
                results.append((score, memory))
        return results

    def _match_score(self, memory: MemoryItem, query: str) -> float:
        """计算记忆与查询的匹配度。"""
        query_lower = query.lower()
        content_lower = memory.content.lower()

        # 中文字符级子串匹配（优先级最高）
        # 移除空格和标点，逐字符匹配
        clean_query = "".join(c for c in query_lower if c.isalnum())
        clean_content = "".join(c for c in content_lower if c.isalnum())

        # 1. 查询中的连续关键词在内容中出现
        if len(clean_query) >= 2 and clean_query in clean_content:
            return 0.8
        if len(clean_content) >= 2 and clean_content in clean_query:
            return 0.8

        # 2. 提取查询中的中文词（2-4字组合）进行匹配
        common_count = 0
        for word_len in range(2, min(5, len(clean_query) + 1)):
            for i in range(len(clean_query) - word_len + 1):
                sub = clean_query[i:i+word_len]
                if sub in clean_content:
                    common_count += 1

        if common_count > 0:
            ratio = common_count / max(len(clean_query), 1)
            return ratio * (0.6 + memory.importance * 0.4)

        # 3. 英文词匹配（回退）
        query_words = set(query_lower.replace("，", " ").replace("。", " ").replace("！", " ").replace("？", " ").split())
        content_words = set(content_lower.replace("，", " ").replace("。", " ").replace("！", " ").replace("？", " ").split())
        common = query_words & content_words
        if common:
            union = query_words | content_words
            jaccard = len(common) / len(union)
            return jaccard * (0.6 + memory.importance * 0.4)

        return 0.0

    def update_emotion(self, user_id: str, memory_id: str, emotion: EmotionType, intensity: float):
        user_memories = self._get_user_memories(user_id)
        if memory_id in user_memories:
            user_memories[memory_id].emotion = emotion
            user_memories[memory_id].emotion_intensity = intensity
            self._dirty.add((user_id, memory_id))
            self._save_to_disk()

    def consolidate_memory(self, user_id: str, memory_id: str) -> bool:
        user_memories = self._get_user_memories(user_id)
        if memory_id in user_memories:
            memory = user_memories[memory_id]
            memory.is_consolidated = True
            memory.access_count += 1
            memory.last_accessed = time.time()
            memory.importance = min(1.0, memory.importance + 0.05)
            self._dirty.add((user_id, memory_id))
            self._save_to_disk()
            return True
        return False

    def prune_memories(self, user_id: str, threshold: float = 0.1) -> List[str]:
        user_memories = self._get_user_memories(user_id)
        to_remove = []

        for mid, memory in user_memories.items():
            new_importance = EbbinghausCurve.decay_importance(memory)
            memory.importance = new_importance

            if new_importance < threshold and not memory.is_consolidated:
                to_remove.append(mid)

        for mid in to_remove:
            del user_memories[mid]
            self._dirty.discard((user_id, mid))

        if to_remove:
            self._save_to_disk()
        return to_remove

    def get_memory_stats(self, user_id: str) -> Dict:
        """获取用户记忆统计信息。"""
        user_memories = self._get_user_memories(user_id)
        if not user_memories:
            return {"total": 0}

        emotion_dist = {}
        category_dist = {}
        importance_avg = 0.0

        for m in user_memories.values():
            emotion_dist[m.emotion.value] = emotion_dist.get(m.emotion.value, 0) + 1
            category_dist[m.category.value] = category_dist.get(m.category.value, 0) + 1
            importance_avg += m.importance

        importance_avg /= len(user_memories)

        return {
            "total": len(user_memories),
            "emotion_distribution": emotion_dist,
            "category_distribution": category_dist,
            "avg_importance": round(importance_avg, 3),
            "consolidated_count": sum(1 for m in user_memories.values() if m.is_consolidated),
        }

    # ================================================================
    # 持久化（SQLite）
    # ================================================================

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            last_error = None
            for attempt in range(3):
                try:
                    with self._conn_lock:
                        conn = sqlite3.connect(self.db_path, timeout=5)
                        conn.execute("PRAGMA journal_mode=WAL")
                        self._local.conn = conn
                    return self._local.conn
                except sqlite3.Error as e:
                    last_error = e
                    logger.warning(f"数据库连接失败 (尝试 {attempt + 1}/3): {e}")
                    if attempt < 2:
                        time.sleep(0.5)
            raise last_error
        return self._local.conn

    def _init_db(self):
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                user_id TEXT NOT NULL,
                memory_id TEXT NOT NULL,
                data TEXT NOT NULL,
                PRIMARY KEY (user_id, memory_id)
            )
        """)
        conn.commit()

    def _save_to_disk(self):
        if not self._dirty:
            return
        conn = self._get_conn()
        for user_id, mid in list(self._dirty):
            if user_id in self.memories and mid in self.memories[user_id]:
                m = self.memories[user_id][mid]
                data = json.dumps(m.to_dict(), ensure_ascii=False)
                conn.execute(
                    "INSERT OR REPLACE INTO memories (user_id, memory_id, data) VALUES (?, ?, ?)",
                    (user_id, mid, data),
                )
        conn.commit()
        self._dirty.clear()

    def _load_from_disk(self):
        conn = self._get_conn()
        try:
            rows = conn.execute("SELECT user_id, memory_id, data FROM memories").fetchall()
            for user_id, mid, data_str in rows:
                if user_id not in self.memories:
                    self.memories[user_id] = {}
                try:
                    self.memories[user_id][mid] = MemoryItem.from_dict(json.loads(data_str))
                except Exception:
                    pass
        except sqlite3.OperationalError:
            pass

    def get_all_user_ids(self) -> List[str]:
        conn = self._get_conn()
        try:
            rows = conn.execute("SELECT DISTINCT user_id FROM memories").fetchall()
            return sorted([r[0] for r in rows])
        except sqlite3.OperationalError:
            return []

    def delete_user_memories(self, user_id: str):
        if user_id in self.memories:
            del self.memories[user_id]
        self._dirty = {(uid, mid) for uid, mid in self._dirty if uid != user_id}
        conn = self._get_conn()
        conn.execute("DELETE FROM memories WHERE user_id = ?", (user_id,))
        conn.commit()


# ================================================================
# 与 Mem0 的桥接适配器
# ================================================================

class Mem0Bridge:
    """
    Mem0 与本地记忆管理器的桥接适配器。
    
    作用：
    - 将 Mem0 的搜索结果转换为本地 MemoryItem 格式
    - 将本地记忆同步到 Mem0（用于向量检索）
    """

    def __init__(self, memory_manager: MemoryManager, mem0_client=None):
        self.memory_manager = memory_manager
        self.mem0_client = mem0_client

    def add_to_both(
        self,
        user_id: str,
        user_msg: str,
        assistant_msg: str,
        category: MemoryCategory = MemoryCategory.FACT,
    ):
        """
        同时添加到 Mem0 和本地记忆管理器。
        
        1. Mem0 负责自动提取和向量化
        2. 本地管理器负责情感标注、重要性评分、遗忘管理
        """
        extracted_facts = self._extract_facts(user_msg, assistant_msg)

        # 添加到 Mem0（向量化检索）
        if self.mem0_client:
            try:
                self.mem0_client.add(
                    messages=[
                        {"role": "user", "content": user_msg},
                        {"role": "assistant", "content": assistant_msg},
                    ],
                    user_id=user_id,
                )
            except Exception:
                pass

        # 添加到本地记忆管理器（存储提取后的事实）
        if extracted_facts:
            for fact in extracted_facts:
                self.memory_manager.add_memory(
                    user_id=user_id,
                    content=fact,
                    category=category,
                )
        else:
            user_summary = user_msg.strip()[:60]
            ai_summary = assistant_msg.strip()[:80]
            if len(user_summary) >= 2:
                self.memory_manager.add_memory(
                    user_id=user_id,
                    content=f"[对话摘要] 用户说：{user_summary}",
                    category=category,
                )
            if len(ai_summary) >= 4:
                self.memory_manager.add_memory(
                    user_id=user_id,
                    content=f"[对话摘要] AI回复要点：{ai_summary}",
                    category=category,
                )

    def _extract_facts(self, user_msg: str, assistant_msg: str) -> List[str]:
        """从对话中提取关于用户的关键事实。使用规则 + LLM 混合提取。"""
        facts = []
        logger.info(f"[DEBUG] _extract_facts called, user_msg={user_msg[:80]}")

        info_keywords = ["我叫", "我是", "我喜欢", "我不喜欢", "我的职业", "我的工作",
                         "我养了", "我有", "我在", "我从事", "我来自", "我结婚", "我单身",
                         "我希望", "我害怕", "我担心", "我讨厌"]
        ai_subject_patterns = ["你会", "你可以", "你能", "你总是", "你应该", "你说的", "你回", "你跟"]
        for kw in info_keywords:
            if kw in user_msg:
                sentences = user_msg.replace("。", "。SPLIT").replace("！", "！SPLIT").replace("？", "？SPLIT").replace("，", "，SPLIT").split("SPLIT")
                for s in sentences:
                    s = s.strip().rstrip("，。！？,.")
                    if kw in s and 4 <= len(s) <= 100:
                        if any(s.startswith(p) or f" {p}" in s or f"，{p}" in s for p in ai_subject_patterns):
                            continue
                        facts.append(f"[关于用户] {s}")
                break

        emotion_keywords = ["焦虑", "孤独", "悲伤", "痛苦", "迷茫",
                           "压力大", "崩溃", "失望", "愤怒", "抑郁"]
        for kw in emotion_keywords:
            if kw in user_msg:
                facts.append(f"[用户情感状态] 用户正在经历{kw}")
                break

        try:
            llm_facts = self._llm_extract_facts(user_msg, assistant_msg)
            existing = set(facts)
            for f in llm_facts:
                if f not in existing:
                    facts.append(f)
        except Exception as e:
            logger.warning(f"[DEBUG] _llm_extract_facts failed: {e}")

        facts = self._filter_low_quality_facts(facts)

        logger.info(f"[DEBUG] _extract_facts result: {facts}")
        return facts[:5]

    def _filter_low_quality_facts(self, facts: List[str]) -> List[str]:
        """过滤低质量事实。"""
        filtered = []
        seen_prefixes = set()
        for f in facts:
            # 移除空事实
            if not f or len(f) < 5:
                continue
            # 移除不完整句子（以逗号、句号等结尾）
            if f.rstrip().endswith("，") or f.rstrip().endswith(","):
                continue
            # 去重（基于前缀）
            prefix = f[:20]
            if prefix in seen_prefixes:
                continue
            seen_prefixes.add(prefix)
            filtered.append(f)
        return filtered

    def _llm_extract_facts(self, user_msg: str, assistant_msg: str) -> List[str]:
        """调用 LLM 从对话中提取关键事实。"""
        try:
            from llm_config import get_llm_client
            from langchain_core.messages import HumanMessage
            import json as _json

            llm = get_llm_client(temperature=0.1, use_thinking=True)

            prompt = f"""你是一个情感陪伴助手的记忆提取模块。请从以下对话中提取值得长期记住的信息。

对话：
用户：{user_msg}
AI：{assistant_msg}

你需要提取的内容（按优先级）：
1. 情感状态：用户当前的情绪、心情（如"用户今天很难过"）
2. 具体事件：用户经历的具体事情，包括有情感关联的细节
3. 人际关系：用户提到的重要关系（家人、朋友、恋人）
4. 偏好与习惯：用户的喜好、习惯、兴趣
5. 身份与生活状况：职业、居住地、生活状态
6. 担忧与困扰：用户担心的事情、面临的困难
7. 互动记忆：AI 给用户的推荐、建议、分享的内容（如推荐的歌曲、书籍、电影、菜谱等），格式为"AI曾向用户推荐了XXX"

重要：第7类"互动记忆"非常关键！如果AI在回复中推荐了具体的歌曲、书籍、电影、美食等，必须提取出来，因为用户后续可能会问起。

不需要提取的：
- 纯粹的客套话或寒暄
- 与用户无关的通用知识

以 JSON 数组格式返回，每条事实是完整的陈述句：
["用户今天买了个不好吃的西瓜，感到很失落", "AI曾向用户推荐了歌曲《晴天》"]
如果没有值得提取的信息，返回 []。"""

            response = llm.invoke([HumanMessage(content=prompt)])
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            facts = _json.loads(content)
            if isinstance(facts, list):
                tagged = []
                for f in facts:
                    if not f or len(f) <= 5:
                        continue
                    if f.startswith("AI") or f.startswith("ai") or "AI曾" in f or "AI向" in f or "AI建议" in f or "AI推荐" in f:
                        tagged.append(f"[AI互动] {f}")
                    else:
                        tagged.append(f"[关于用户] {f}")
                return tagged
        except Exception as e:
            logger.warning(f"[DEBUG] LLM extraction error: {e}")
            pass

        return []

    def search_with_enrichment(
        self,
        user_id: str,
        query: str,
        mem0_limit: int = 5,
        local_limit: int = 3,
    ) -> List[Dict]:
        """
        从 Mem0 和本地记忆管理器联合检索。
        
        返回 enriched 结果，包含情感标签和重要性信息。
        """
        results = []

        # 1. 从 Mem0 检索（向量相似度）
        if self.mem0_client:
            try:
                mem0_results = self.mem0_client.search(query=query, user_id=user_id, limit=mem0_limit)
                if mem0_results and "results" in mem0_results:
                    for r in mem0_results["results"]:
                        results.append({
                            "source": "mem0",
                            "memory": r.get("memory", ""),
                            "score": r.get("score", 0),
                            "emotion": EmotionType.NEUTRAL.value,
                            "importance": 0.5,
                        })
            except Exception:
                pass

        # 2. 从本地记忆检索（情感/重要性增强）
        local_results = self.memory_manager.search_memories(user_id, query, limit=local_limit)
        for m in local_results:
            results.append({
                "source": "local",
                "memory": m.content,
                "score": m.importance,
                "emotion": m.emotion.value,
                "importance": m.importance,
                "category": m.category.value,
                "emotion_emoji": m.emotion.to_emoji(),
            })

        # 去重（基于内容相似度）
        results = self._deduplicate(results)

        # 回退：当 Mem0（异步索引延迟）和本地关键词搜索都无结果时，
        # 返回最近 N 条记忆作为兜底，确保记忆系统始终可用
        if not results:
            user_memories = self.memory_manager._get_user_memories(user_id)
            sorted_by_time = sorted(
                user_memories.values(),
                key=lambda m: m.created_at,
                reverse=True,
            )
            for m in sorted_by_time[:local_limit]:
                results.append({
                    "source": "local_recent",
                    "memory": m.content,
                    "score": 0.1,
                    "emotion": m.emotion.value,
                    "importance": m.importance,
                    "category": m.category.value,
                    "emotion_emoji": m.emotion.to_emoji(),
                })

        return results[:mem0_limit + local_limit]

    def _deduplicate(self, results: List[Dict]) -> List[Dict]:
        """简单去重：移除内容高度相似的记忆。"""
        seen = set()
        unique = []
        for r in results:
            # 使用内容的前 20 个字符作为简单哈希
            key = r["memory"][:30]
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return unique
