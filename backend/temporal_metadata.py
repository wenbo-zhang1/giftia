"""
时间标签模块 - 记忆的时间维度

为记忆添加时间上下文，让模型理解"昨天"、"去年夏天"等时间表达。
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime, timedelta
import time


# ================================================================
# 时间标签数据结构
# ================================================================

@dataclass
class TemporalMetadata:
    """记忆的时间标签元数据"""
    
    event_time: Dict[str, any] = field(default_factory=dict)
    time_context: Dict[str, str] = field(default_factory=dict)
    recurrence: Dict[str, any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "event_time": self.event_time,
            "time_context": self.time_context,
            "recurrence": self.recurrence,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "TemporalMetadata":
        return cls(
            event_time=data.get("event_time", {}),
            time_context=data.get("time_context", {}),
            recurrence=data.get("recurrence", {}),
        )
    
    def get_age_in_days(self) -> Optional[float]:
        """获取记忆的年龄（天数）"""
        if not self.event_time.get("timestamp"):
            return None
        
        now = time.time()
        age_seconds = now - self.event_time["timestamp"]
        return age_seconds / 86400
    
    def is_recent(self, days: int = 7) -> bool:
        """判断是否是近期记忆"""
        age = self.get_age_in_days()
        return age is not None and age <= days


# ================================================================
# 时间信息提取器
# ================================================================

class TemporalExtractor:
    """时间信息提取器（修复季节映射）"""
    
    # 复合时间表达（优先匹配）- 修复：统一使用"夏天"
    COMPOUND_TIME_MAP = {
        "去年夏天": (-365, "夏天"),
        "去年冬天": (-365, "冬天"),
        "今年夏天": (0, "夏天"),
        "今年冬天": (0, "冬天"),
        "上个暑假": (-365, "暑假"),
        "这个暑假": (0, "暑假"),
    }
    
    # 简单相对时间
    RELATIVE_TIME_MAP = {
        "今天": 0,
        "昨天": -1,
        "前天": -2,
        "明天": 1,
        "后天": 2,
        "上周": -7,
        "这周": 0,
        "下周": 7,
        "上个月": -30,
        "这个月": 0,
        "下个月": 30,
        "去年": -365,
        "今年": 0,
        "明年": 365,
    }
    
    # 季节映射 - 修复：同时包含"夏天"和"夏季"、"冬天"和"冬季"
    SEASON_MAP = {
        "春天": (3, 5),
        "夏季": (6, 8),
        "夏天": (6, 8),  # 新增
        "秋天": (9, 11),
        "冬季": (12, 2),
        "冬天": (12, 2),  # 新增
        "暑假": (7, 8),
        "寒假": (1, 2),
    }
    
    @classmethod
    def extract_from_text(cls, text: str, reference_time: Optional[float] = None) -> TemporalMetadata:
        """从文本中提取时间信息（修复复合时间表达覆盖问题）"""
        ref_time = reference_time or time.time()
        ref_dt = datetime.fromtimestamp(ref_time)
        
        metadata = TemporalMetadata()
        
        # 1. 优先匹配复合时间表达（如"去年夏天"）
        for compound, (days_offset, season) in cls.COMPOUND_TIME_MAP.items():
            if compound in text:
                target_year = ref_dt.year + (days_offset // 365)
                season_months = cls.SEASON_MAP[season]
                target_dt = datetime(target_year, season_months[0], 1)
                
                metadata.event_time = {
                    "timestamp": target_dt.timestamp(),
                    "description": compound,
                    "precision": "relative",
                }
                metadata.time_context["season"] = season
                return metadata  # 匹配到复合表达后直接返回
        
        # 2. 匹配简单相对时间
        for keyword, days_offset in cls.RELATIVE_TIME_MAP.items():
            if keyword in text:
                target_dt = ref_dt + timedelta(days=days_offset)
                metadata.event_time = {
                    "timestamp": target_dt.timestamp(),
                    "description": keyword,
                    "precision": "relative",
                }
                break
        
        # 3. 匹配季节（如果前面没有匹配到复合表达）
        if not metadata.event_time:
            for season, (start_month, end_month) in cls.SEASON_MAP.items():
                if season in text:
                    metadata.time_context["season"] = season
                    year = ref_dt.year
                    if start_month > ref_dt.month:
                        year -= 1
                    metadata.event_time["timestamp"] = datetime(year, start_month, 1).timestamp()
                    metadata.event_time["precision"] = "approximate"
                    break
        
        # 4. 提取生活阶段
        life_stages = ["小时候", "童年", "学生时代", "大学时期", "工作后"]
        for stage in life_stages:
            if stage in text:
                metadata.time_context["life_stage"] = stage
                break
        
        # 5. 提取重复性
        recurrence_keywords = ["每天", "每周", "每月", "每年", "经常", "总是"]
        for kw in recurrence_keywords:
            if kw in text:
                metadata.recurrence["is_recurring"] = True
                if "每天" in text:
                    metadata.recurrence["frequency"] = "daily"
                elif "每周" in text:
                    metadata.recurrence["frequency"] = "weekly"
                elif "每月" in text:
                    metadata.recurrence["frequency"] = "monthly"
                elif "每年" in text:
                    metadata.recurrence["frequency"] = "yearly"
                else:
                    metadata.recurrence["frequency"] = "irregular"
                break
        
        return metadata
