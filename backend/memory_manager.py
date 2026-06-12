"""
情感记忆管理器 - 高级记忆系统

功能：
1. 情感标签系统：自动识别和标记记忆的情感属性
2. 记忆重要性评分：基于多维度评估记忆的重要性
3. 遗忘曲线机制：基于艾宾浩斯遗忘曲线的记忆衰减与巩固
4. 记忆合并与清理：自动合并相似记忆，清理低价值记忆
5. 事实提取与存储：从对话中提取关键事实并存储为记忆

设计目标：
- 完整的本地记忆系统，无需外部依赖
- 模块化设计，各组件可独立使用
"""

import os
import json
import time
import math
import hashlib
import logging
import sqlite3
import threading
import numpy as np
from typing import List, Dict, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
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
            # 中文映射
            "开心": cls.HAPPY, "快乐": cls.HAPPY, "高兴": cls.HAPPY, "愉快": cls.HAPPY, "兴奋": cls.EXCITED, "激动": cls.EXCITED,
            "难过": cls.SAD, "悲伤": cls.SAD, "伤心": cls.SAD, "失落": cls.SAD, "沮丧": cls.SAD, "孤独": cls.LONELY,
            "焦虑": cls.ANXIOUS, "紧张": cls.ANXIOUS, "压力": cls.STRESSED, "担忧": cls.ANXIOUS, "害怕": cls.FEARFUL,
            "生气": cls.ANGRY, "愤怒": cls.ANGRY, "烦躁": cls.ANGRY,
            "感恩": cls.GRATEFUL, "感谢": cls.GRATEFUL, "谢谢": cls.GRATEFUL,
            "希望": cls.HOPEFUL, "期待": cls.HOPEFUL, "放心": cls.RELIEVED,
            "平静": cls.NEUTRAL, "一般": cls.NEUTRAL, "没事": cls.NEUTRAL,
            # 英文映射（情感分析 Agent 返回英文标签）
            "happy": cls.HAPPY, "sad": cls.SAD, "anxious": cls.ANXIOUS, "angry": cls.ANGRY,
            "neutral": cls.NEUTRAL, "excited": cls.EXCITED, "fearful": cls.FEARFUL,
            "grateful": cls.GRATEFUL, "lonely": cls.LONELY, "hopeful": cls.HOPEFUL,
            "stressed": cls.STRESSED, "relieved": cls.RELIEVED,
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
    """单条记忆数据结构（扩展版）。"""
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
    
    # ========== 新增字段（v2） ==========
    layer: int = 3                    # 记忆层级：1=核心, 2=重要, 3=常规
    temporal_data: Dict = field(default_factory=dict)  # 时间标签数据

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
            # 新增字段
            "layer": self.layer,
            "temporal_data": self.temporal_data,
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
        # 兼容旧数据：如果没有新字段，使用默认值
        if "layer" not in data:
            data["layer"] = 3
        if "temporal_data" not in data:
            data["temporal_data"] = {}
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
            "笑", "好玩", "有趣", "惊喜", "顺利", "成功",
        ],
        EmotionType.SAD: [
            "难过", "悲伤", "伤心", "失落", "沮丧", "哭", "痛苦", "绝望",
            "无奈", "失望", "心碎", "眼泪", "不开心", "郁闷", "低落",
            "失败", "挫败", "遗憾", "错过", "被拒", "碰壁", "落空",
            "没戏", "泡汤", "完了", "凉了",
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
            "兴奋", "激动", "迫不及待", "振奋", "狂热",
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
            "希望", "相信", "会好的", "未来",
        ],
        EmotionType.STRESSED: [
            "压力", "累", "疲惫", "受不了", "崩溃", "撑不住", "喘不过气",
            "加班", "考试", " deadline",
        ],
        EmotionType.RELIEVED: [
            "放心", "安心", "松了一口气", "还好", "总算", "解脱",
        ],
    }

    # 语境翻转规则：当正向词与负面语境共现时，翻转为 SAD
    # 格式：(正向关键词, 负面语境词列表, 翻转目标情感)
    CONTEXT_FLIPS = [
        ("喜欢", ["没牵", "没拉", "没在一起", "不喜欢我", "拒绝", "没结果", "没回应", "单相思", "暗恋", "手都没牵"], EmotionType.SAD),
        ("爱", ["不爱", "分手", "离开", "拒绝", "单相思", "没结果"], EmotionType.SAD),
        ("努力", ["失败", "没用", "白费", "不行", "被拒", "碰壁", "落空", "没结果", "找不到", "还是没"], EmotionType.SAD),
        ("期待", ["落空", "失望", "没实现", "泡汤", "没了"], EmotionType.SAD),
        ("希望", ["破灭", "没了", "失望", "落空"], EmotionType.SAD),
        ("成功", ["没成功", "不成功", "失败"], EmotionType.SAD),
    ]

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
        # 第一步：检查语境翻转规则（优先级最高）
        for positive_kw, negative_contexts, flip_emotion in cls.CONTEXT_FLIPS:
            if positive_kw in text:
                for ctx in negative_contexts:
                    if ctx in text:
                        # 正向词 + 负面语境 → 翻转
                        return flip_emotion, 0.6

        # 第二步：常规关键词匹配
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
# 查询改写（Query Rewriting）
# ================================================================

QUERY_REWRITE_PROMPT = """你是一个搜索查询改写专家。请将用户的口语化输入改写为2-3个更适合检索记忆的查询。

规则：
1. 保留原始查询的核心意图
2. 将口语化表达转为更正式的描述性语句
3. 从不同角度扩展查询（情感状态、具体事实、相关事件）
4. 每个查询不超过30字
5. 如果原始查询已经很清晰，只需微调

用户输入：{query}

以 JSON 数组格式返回改写后的查询（包含原始意图的改写版本）：
["查询1", "查询2"]"""


def rewrite_query(query: str) -> List[str]:
    """
    使用 LLM 将用户口语化输入改写为多个检索查询。

    LLM 不可用或超时时降级返回原始查询。
    """
    if not query or len(query.strip()) < 2:
        return [query]

    try:
        from llm_config import get_llm_client
        from langchain_core.messages import HumanMessage

        llm = get_llm_client(temperature=0.0, use_thinking=False)
        prompt = QUERY_REWRITE_PROMPT.format(query=query)

        # 5 秒超时，避免 LLM 慢响应阻塞检索
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(llm.invoke, [HumanMessage(content=prompt)])
            response = future.result(timeout=5)

        content = response.content.strip()

        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        queries = json.loads(content)
        if isinstance(queries, list) and len(queries) > 0:
            # 确保原始查询也在列表中
            result = [query] + [q for q in queries if q != query]
            return result[:4]  # 最多 4 个查询（原始 + 3 个改写）
    except concurrent.futures.TimeoutError:
        logger.warning("[查询改写] LLM 超时(5s)，使用原始查询")
    except Exception as e:
        logger.warning(f"[查询改写] 失败，使用原始查询: {e}")

    return [query]


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
        queries: Optional[List[str]] = None,
    ) -> List[MemoryItem]:
        """
        混合检索：语义 + 关键词多路召回 → RRF 融合 → Reranking。

        参数：
        - queries: 可选的改写查询列表，用于多查询检索
        """
        user_memories = self._get_user_memories(user_id)
        if not user_memories:
            return []

        search_queries = queries or [query]

        # 多路召回 + RRF 融合
        rrf_scores: Dict[str, float] = {}  # memory_id -> rrf_score
        rrf_k = 60

        for q in search_queries:
            # 语义检索
            semantic_results = self._semantic_search_raw(user_memories, q, emotion_filter, min_importance)
            # 关键词检索
            keyword_results = self._keyword_search_raw(user_memories, q, emotion_filter, min_importance)

            # RRF: score = 1 / (k + rank + 1)
            for rank, (score, memory) in enumerate(semantic_results):
                rrf_scores[memory.id] = rrf_scores.get(memory.id, 0) + 1.0 / (rrf_k + rank + 1)
            for rank, (score, memory) in enumerate(keyword_results):
                rrf_scores[memory.id] = rrf_scores.get(memory.id, 0) + 1.0 / (rrf_k + rank + 1)

        # 构建候选列表
        candidates = []
        for mid, rrf_score in rrf_scores.items():
            if mid in user_memories:
                candidates.append((rrf_score, user_memories[mid]))

        if not candidates:
            return []

        # Reranking
        ranked = self._rerank(candidates, query, emotion_filter)

        # 更新访问统计
        selected = ranked[:limit]
        for m in selected:
            m.access_count += 1
            m.last_accessed = time.time()
            self._dirty.add((user_id, m.id))
        self._save_to_disk()

        return selected

    def _semantic_search_raw(
        self,
        user_memories: Dict[str, MemoryItem],
        query: str,
        emotion_filter: Optional[EmotionType],
        min_importance: float,
    ) -> List[Tuple[float, MemoryItem]]:
        """语义匹配检索（无副作用），返回 (相似度, MemoryItem) 列表。"""
        query_embedding = self.embedding_service.get_embedding(query)
        if query_embedding is None:
            return []

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
            if similarity > 0.1:
                results.append((similarity, memory))

        results.sort(key=lambda x: x[0], reverse=True)
        return results

    def _keyword_search_raw(
        self,
        user_memories: Dict[str, MemoryItem],
        query: str,
        emotion_filter: Optional[EmotionType],
        min_importance: float,
    ) -> List[Tuple[float, MemoryItem]]:
        """关键词匹配检索（无副作用），返回 (匹配分, MemoryItem) 列表。"""
        results = []
        for memory in user_memories.values():
            if memory.importance < min_importance:
                continue
            if emotion_filter and memory.emotion != emotion_filter:
                continue
            score = self._match_score(memory, query)
            if score > 0:
                results.append((score, memory))
        results.sort(key=lambda x: x[0], reverse=True)
        return results

    def _rerank(
        self,
        candidates: List[Tuple[float, MemoryItem]],
        query: str,
        emotion_filter: Optional[EmotionType] = None,
    ) -> List[MemoryItem]:
        """
        多特征 Reranking：RRF 分数 + 时间衰减 + 情感匹配 + 重要性 + layer 权重。

        权重（v2.0 修复版）：
        - RRF 分数: 0.50（检索质量，保持不变）
        - 时间衰减: 0.20（近期记忆更相关，保持不变）
        - 情感匹配: 0.15（情感状态一致的记忆更相关，保持不变）
        - 重要性:   0.10（重要记忆更相关，从 0.15 降到 0.10）
        - layer 权重: 0.05（新增，从重要性中分出）
        """
        from memory_layer import MemoryLayer  # 延迟导入，避免循环依赖
        
        now = time.time()
        query_emotion, _ = self.emotion_analyzer.analyze(query)

        # 归一化 RRF 分数
        max_rrf = max(c[0] for c in candidates) if candidates else 1.0
        if max_rrf == 0:
            max_rrf = 1.0

        scored = []
        for rrf_score, memory in candidates:
            # 归一化 RRF (0-1)
            norm_rrf = rrf_score / max_rrf

            # 时间衰减（使用 layer 的遗忘强度）
            layer = memory.layer if hasattr(memory, "layer") else 3
            strength = MemoryLayer(layer).get_forgetting_strength()
            elapsed_hours = (now - (memory.last_accessed or memory.created_at)) / 3600
            time_score = math.exp(-elapsed_hours / (strength * 24 + 1))

            # 情感匹配
            emotion_score = 0.0
            if query_emotion != EmotionType.NEUTRAL and memory.emotion == query_emotion:
                emotion_score = 1.0
            elif query_emotion != EmotionType.NEUTRAL and memory.emotion != EmotionType.NEUTRAL:
                emotion_score = 0.3  # 非中性情感有部分匹配

            # layer 权重
            layer_weight = MemoryLayer(layer).get_retrieval_weight()

            # 综合评分（修复版：保持 RRF 权重不变）
            final_score = (
                norm_rrf * 0.50          # 检索质量（保持不变）
                + time_score * 0.20      # 时间衰减（保持不变）
                + emotion_score * 0.15   # 情感匹配（保持不变）
                + memory.importance * 0.10  # 重要性（从 0.15 降到 0.10）
                + layer_weight * 0.05    # layer 权重（新增，从重要性中分出）
            )
            scored.append((final_score, memory))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored]

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
    # 事实提取与存储
    # ================================================================

    def extract_and_store_facts(
        self,
        user_id: str,
        user_msg: str,
        assistant_msg: str,
        category: MemoryCategory = MemoryCategory.FACT,
        emotion: Optional[EmotionType] = None,
        emotion_intensity: Optional[float] = None,
    ) -> List[str]:
        """从对话中提取关键事实并存储为记忆。
        
        返回提取到的事实列表。
        """
        extracted_facts = self._extract_facts(user_msg, assistant_msg)

        if extracted_facts:
            for fact in extracted_facts:
                self.add_memory(
                    user_id=user_id,
                    content=fact,
                    category=category,
                    emotion=emotion,
                    emotion_intensity=emotion_intensity,
                )
        else:
            user_summary = user_msg.strip()[:60]
            ai_summary = assistant_msg.strip()[:80]
            if len(user_summary) >= 2:
                self.add_memory(
                    user_id=user_id,
                    content=f"[对话摘要] 用户说：{user_summary}",
                    category=category,
                    emotion=emotion,
                    emotion_intensity=emotion_intensity,
                )
            if len(ai_summary) >= 4:
                self.add_memory(
                    user_id=user_id,
                    content=f"[对话摘要] AI回复要点：{ai_summary}",
                    category=category,
                    emotion=emotion,
                    emotion_intensity=emotion_intensity,
                )

        return extracted_facts

    def _extract_facts(self, user_msg: str, assistant_msg: str) -> List[str]:
        """从对话中提取关于用户的关键事实。使用规则 + LLM 混合提取。"""
        facts = []
        logger.info(f"[事实提取] user_msg={user_msg[:80]}")

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
            logger.warning(f"[事实提取] LLM 提取失败: {e}")

        facts = self._filter_low_quality_facts(facts)

        logger.info(f"[事实提取] 提取了 {len(facts)} 条事实")
        return facts[:5]

    def _filter_low_quality_facts(self, facts: List[str]) -> List[str]:
        """过滤低质量事实。"""
        filtered = []
        seen_prefixes = set()
        for f in facts:
            if not f or len(f) < 5:
                continue
            if f.rstrip().endswith("，") or f.rstrip().endswith(","):
                continue
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

            llm = get_llm_client(temperature=0.0, use_thinking=False)

            prompt = f"""你是一个情感陪伴助手的记忆提取模块。请从以下对话中提取值得长期记住的信息。

对话：
用户：{user_msg}
AI：{assistant_msg}

严格规则：
1. 只能提取用户**明确说出**的事实，禁止任何推测或引申
2. 如果用户没有表达任何值得记住的信息，返回 []
3. 禁止提取 AI 对用户的建议（除非用户明确表示采纳）
4. 禁止提取用户"可能想做"的事情，只提取用户明确说的
5. 情感状态类事实仅在用户明确表达情绪时提取

需要提取的（按优先级）：
1. 用户明确表达的当前情感状态（如"我感到孤独"）
2. 用户明确提到的具体事件
3. 用户明确提到的人际关系
4. 用户明确表达的偏好（如"我喜欢xxx"）
5. 用户明确提到的担忧或困扰
6. AI 向用户推荐的具体内容（歌曲、书籍等），格式为"AI曾向用户推荐了XXX"

不需要提取的：
- 纯粹的客套话或寒暄
- 与用户无关的通用知识
- AI 的建议（除非用户明确采纳）
- 任何推测性内容

以 JSON 数组格式返回，每条事实是完整的陈述句：
["用户今天很难过", "AI曾向用户推荐了歌曲《晴天》"]
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
            logger.warning(f"[事实提取] LLM 提取错误: {e}")
            pass

        return []
