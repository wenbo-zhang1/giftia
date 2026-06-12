"""
记忆分层模块 - 多层次记忆管理

将记忆分为三个层级：
- CORE（核心）：永不遗忘
- IMPORTANT（重要）：慢速遗忘
- REGULAR（常规）：正常遗忘

工作记忆保持独立模块（WorkingMemoryStore），不参与分层。
"""

from enum import IntEnum


class MemoryLayer(IntEnum):
    """记忆层级枚举（移除 WORKING，工作记忆保持独立模块）"""
    CORE = 1      # 核心记忆：永不遗忘
    IMPORTANT = 2 # 重要记忆：慢速遗忘
    REGULAR = 3   # 常规记忆：正常遗忘
    
    @classmethod
    def from_importance(cls, importance: float, emotion_intensity: float = 0.5) -> "MemoryLayer":
        """根据重要性和情感强度自动分配层级"""
        if importance >= 0.8 or emotion_intensity >= 0.8:
            return cls.CORE
        elif importance >= 0.6 or emotion_intensity >= 0.7:
            return cls.IMPORTANT
        else:
            return cls.REGULAR
    
    def get_forgetting_strength(self) -> float:
        """获取遗忘曲线强度系数"""
        strength_map = {
            MemoryLayer.CORE: 10.0,      # 几乎不遗忘
            MemoryLayer.IMPORTANT: 2.0,  # 慢速遗忘
            MemoryLayer.REGULAR: 1.0,    # 正常遗忘
        }
        return strength_map.get(self, 1.0)
    
    def get_retrieval_weight(self) -> float:
        """获取检索时的权重"""
        weight_map = {
            MemoryLayer.CORE: 1.0,
            MemoryLayer.IMPORTANT: 0.8,
            MemoryLayer.REGULAR: 0.5,
        }
        return weight_map.get(self, 0.5)
