"""
Giftia - 核心模块单元测试

运行: cd backend && python -m pytest tests/ -v
"""

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# ================================================================
# 遗忘曲线测试
# ================================================================

class TestEbbinghausCurve:
    from memory_manager import EbbinghausCurve, MemoryItem, EmotionType, MemoryCategory

    def test_retention_rate_fresh_memory(self):
        """刚创建的记忆保留率应接近 1.0"""
        now = time.time()
        rate = self.EbbinghausCurve.retention_rate(
            created_at=now,
            last_accessed=now,
            importance=0.5,
            access_count=0,
        )
        assert rate > 0.9, f"Fresh memory retention should be > 0.9, got {rate}"

    def test_retention_rate_decays_over_time(self):
        """记忆保留率应随时间衰减"""
        now = time.time()
        rate_fresh = self.EbbinghausCurve.retention_rate(
            created_at=now, last_accessed=now, importance=0.5, access_count=0
        )
        rate_old = self.EbbinghausCurve.retention_rate(
            created_at=now - 7200, last_accessed=now - 7200, importance=0.5, access_count=0
        )
        assert rate_fresh > rate_old, "Retention should decay over time"

    def test_retention_rate_importance_effect(self):
        """高重要性记忆应衰减更慢"""
        now = time.time()
        old_time = now - 7200
        rate_low = self.EbbinghausCurve.retention_rate(
            created_at=old_time, last_accessed=old_time, importance=0.1, access_count=0
        )
        rate_high = self.EbbinghausCurve.retention_rate(
            created_at=old_time, last_accessed=old_time, importance=0.9, access_count=0
        )
        assert rate_high > rate_low, "High importance memory should retain better"

    def test_retention_rate_review_effect(self):
        """多次复习的记忆应衰减更慢"""
        now = time.time()
        old_time = now - 7200
        rate_no_review = self.EbbinghausCurve.retention_rate(
            created_at=old_time, last_accessed=old_time, importance=0.5, access_count=0
        )
        rate_reviewed = self.EbbinghausCurve.retention_rate(
            created_at=old_time, last_accessed=old_time, importance=0.5, access_count=5
        )
        assert rate_reviewed > rate_no_review, "Reviewed memory should retain better"

    def test_retention_rate_bounded(self):
        """保留率应在 [0, 1] 范围内"""
        now = time.time()
        for importance in [0.0, 0.5, 1.0]:
            for access_count in [0, 1, 10, 100]:
                for elapsed_hours in [0, 1, 24, 168, 8760]:
                    rate = self.EbbinghausCurve.retention_rate(
                        created_at=now - elapsed_hours * 3600,
                        last_accessed=now - elapsed_hours * 3600,
                        importance=importance,
                        access_count=access_count,
                    )
                    assert 0.0 <= rate <= 1.0, f"Rate {rate} out of bounds for imp={importance}, access={access_count}, hours={elapsed_hours}"

    def test_should_consolidate(self):
        """低保留率且未巩固的记忆应需要巩固"""
        now = time.time()
        memory = self.MemoryItem(
            id="test",
            content="test",
            importance=0.1,
            access_count=0,
            created_at=now - 8760 * 3600,
            last_accessed=now - 8760 * 3600,
            is_consolidated=False,
        )
        assert self.EbbinghausCurve.should_consolidate(memory), "Old unconsolidated memory should need consolidation"

    def test_should_not_consolidate_already_consolidated(self):
        """已巩固的记忆不需要再次巩固"""
        now = time.time()
        memory = self.MemoryItem(
            id="test",
            content="test",
            importance=0.1,
            access_count=0,
            created_at=now - 8760 * 3600,
            last_accessed=now - 8760 * 3600,
            is_consolidated=True,
        )
        assert not self.EbbinghausCurve.should_consolidate(memory), "Consolidated memory should not need re-consolidation"

    def test_decay_importance(self):
        """重要性衰减后应在 [0, 1] 范围内"""
        now = time.time()
        memory = self.MemoryItem(
            id="test",
            content="test",
            importance=0.8,
            access_count=2,
            created_at=now - 48 * 3600,
            last_accessed=now - 24 * 3600,
        )
        decayed = self.EbbinghausCurve.decay_importance(memory)
        assert 0.0 <= decayed <= 1.0, f"Decayed importance {decayed} out of bounds"


# ================================================================
# Provider 检测测试
# ================================================================

class TestProviderDetection:

    def test_deepseek_by_model(self):
        from model_config import detect_provider
        assert detect_provider(model="deepseek-chat") == "deepseek"

    def test_deepseek_by_url(self):
        from model_config import detect_provider
        assert detect_provider(model="x", base_url="https://api.deepseek.com/v1") == "deepseek"

    def test_openai_by_url(self):
        from model_config import detect_provider
        assert detect_provider(model="x", base_url="https://api.openai.com/v1") == "openai"

    def test_openai_by_model(self):
        from model_config import detect_provider
        assert detect_provider(model="gpt-4o", base_url="https://api.openai.com/v1") == "openai"

    def test_zhipu_by_url(self):
        from model_config import detect_provider
        assert detect_provider(model="x", base_url="https://open.bigmodel.cn/api/paas/v4") == "zhipu"

    def test_zhipu_by_model(self):
        from model_config import detect_provider
        assert detect_provider(model="glm-4-flash", base_url="https://open.bigmodel.cn/api/paas/v4") == "zhipu"

    def test_qwen_by_model(self):
        from model_config import detect_provider
        assert detect_provider(model="qwen-plus", base_url="https://dashscope.aliyuncs.com/compatible-mode/v1") == "qwen"

    def test_qwen_by_url(self):
        from model_config import detect_provider
        assert detect_provider(model="x", base_url="https://dashscope.aliyuncs.com/compatible-mode/v1") == "qwen"

    def test_siliconflow_by_url(self):
        from model_config import detect_provider
        assert detect_provider(model="x", base_url="https://api.siliconflow.cn/v1") == "siliconflow"

    def test_unknown_provider(self):
        from model_config import detect_provider
        assert detect_provider(model="unknown-model", base_url="https://unknown.api.com/v1") == "other"


class TestModelProfile:

    def test_exact_match(self):
        from model_config import get_model_profile, MODEL_PROFILES
        for key in MODEL_PROFILES:
            profile = get_model_profile(key)
            assert profile == MODEL_PROFILES[key], f"Exact match failed for {key}"

    def test_prefix_match(self):
        from model_config import get_model_profile
        profile = get_model_profile("deepseek-v4-flash")
        assert "extra_body" in profile or "reasoning_effort" in profile, "Prefix match should work for deepseek-v4-flash"

    def test_unknown_model_returns_empty(self):
        from model_config import get_model_profile
        profile = get_model_profile("totally-unknown-model-xyz")
        assert profile == {}, "Unknown model should return empty dict"


# ================================================================
# EmotionType 测试
# ================================================================

class TestEmotionType:
    from memory_manager import EmotionType

    def test_from_string_happy(self):
        assert self.EmotionType.from_string("开心") == self.EmotionType.HAPPY

    def test_from_string_sad(self):
        assert self.EmotionType.from_string("难过") == self.EmotionType.SAD

    def test_from_string_unknown(self):
        assert self.EmotionType.from_string("未知情感") == self.EmotionType.NEUTRAL

    def test_to_emoji(self):
        assert self.EmotionType.HAPPY.to_emoji() == "😊"
        assert self.EmotionType.SAD.to_emoji() == "😢"


# ================================================================
# MemoryItem 序列化测试
# ================================================================

class TestMemoryItem:
    from memory_manager import MemoryItem, EmotionType, MemoryCategory

    def test_to_dict_and_back(self):
        item = self.MemoryItem(
            id="test-123",
            content="用户今天很开心",
            emotion=self.EmotionType.HAPPY,
            category=self.MemoryCategory.EMOTION,
            importance=0.8,
            access_count=3,
            emotion_intensity=0.9,
            tags=["开心", "工作"],
        )
        d = item.to_dict()
        restored = self.MemoryItem.from_dict(d)
        assert restored.id == item.id
        assert restored.content == item.content
        assert restored.emotion == item.emotion
        assert restored.category == item.category
        assert restored.importance == item.importance
        assert restored.access_count == item.access_count

    def test_default_values(self):
        item = self.MemoryItem(id="test", content="test")
        assert item.emotion == self.EmotionType.NEUTRAL
        assert item.category == self.MemoryCategory.FACT
        assert item.importance == 0.5
        assert item.access_count == 0
        assert item.is_consolidated is False
