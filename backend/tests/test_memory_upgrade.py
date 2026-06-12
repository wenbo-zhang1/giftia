"""
记忆系统升级 v2 单元测试

测试覆盖：
1. UserProfile 和 ProfileManager
2. TemporalMetadata 和 TemporalExtractor
3. MemoryLayer
4. 数据库迁移脚本
"""

import os
import sys
import json
import time
import tempfile
import sqlite3
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from user_profile import UserProfile, ProfileManager, ProfileUpdater
from temporal_metadata import TemporalMetadata, TemporalExtractor
from memory_layer import MemoryLayer


class TestUserProfile:
    """测试 UserProfile 数据结构"""

    def test_profile_creation(self):
        profile = UserProfile(user_id="test_user")
        assert profile.user_id == "test_user"
        assert profile.version == 1
        assert profile.identity == {}
        assert profile.preferences == {}

    def test_profile_to_dict(self):
        profile = UserProfile(
            user_id="test_user",
            identity={"name": "小明", "age": 25},
            preferences={"hobbies": ["编程", "旅行"]},
        )
        d = profile.to_dict()
        assert d["identity"]["name"] == "小明"
        assert d["preferences"]["hobbies"] == ["编程", "旅行"]

    def test_profile_from_dict(self):
        data = {
            "identity": {"name": "小明"},
            "preferences": {"hobbies": ["编程"]},
        }
        profile = UserProfile.from_dict("test_user", data)
        assert profile.user_id == "test_user"
        assert profile.identity["name"] == "小明"

    def test_profile_to_prompt_context(self):
        profile = UserProfile(
            user_id="test_user",
            identity={"name": "小明", "age": 25, "occupation": "程序员"},
            preferences={"hobbies": ["编程", "旅行"]},
            emotional_profile={"recent_mood_trend": "比较好"},
        )
        context = profile.to_prompt_context()
        assert "小明" in context
        assert "25岁" in context
        assert "程序员" in context
        assert "编程" in context
        assert "比较好" in context

    def test_profile_to_prompt_context_empty(self):
        profile = UserProfile(user_id="test_user")
        context = profile.to_prompt_context()
        assert context == ""


class TestProfileManager:
    """测试 ProfileManager"""

    def test_save_and_load(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
            db_path = f.name

        try:
            manager = ProfileManager(db_path)
            
            # 创建并保存档案卡
            profile = UserProfile(
                user_id="test_user",
                identity={"name": "小明"},
            )
            manager.save_profile(profile)

            # 加载档案卡
            loaded = manager.get_profile("test_user")
            assert loaded is not None
            assert loaded.identity["name"] == "小明"

            manager.close()
        finally:
            try:
                os.unlink(db_path)
            except PermissionError:
                pass  # Windows 文件锁

    def test_cache_hit(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
            db_path = f.name

        try:
            manager = ProfileManager(db_path)
            
            profile = UserProfile(user_id="test_user", identity={"name": "小明"})
            manager.save_profile(profile)

            # 第一次加载（缓存未命中）
            loaded1 = manager.get_profile("test_user")
            assert loaded1.identity["name"] == "小明"

            # 修改数据库中的值
            conn = sqlite3.connect(db_path)
            conn.execute(
                "UPDATE user_profiles SET profile_data = ? WHERE user_id = ?",
                (json.dumps({"identity": {"name": "小红"}}), "test_user")
            )
            conn.commit()
            conn.close()

            # 第二次加载（缓存命中，应该还是旧值）
            loaded2 = manager.get_profile("test_user")
            assert loaded2.identity["name"] == "小明"

            manager.close()
        finally:
            try:
                os.unlink(db_path)
            except PermissionError:
                pass

    def test_nonexistent_profile(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
            db_path = f.name

        try:
            manager = ProfileManager(db_path)
            profile = manager.get_profile("nonexistent")
            assert profile is None
            manager.close()
        finally:
            try:
                os.unlink(db_path)
            except PermissionError:
                pass


class TestTemporalExtractor:
    """测试时间提取器"""

    def test_relative_time_yesterday(self):
        text = "昨天我去公园散步"
        metadata = TemporalExtractor.extract_from_text(text)
        
        assert metadata.event_time["description"] == "昨天"
        assert metadata.event_time["precision"] == "relative"
        
        expected_date = datetime.now() - timedelta(days=1)
        actual_date = datetime.fromtimestamp(metadata.event_time["timestamp"])
        assert actual_date.date() == expected_date.date()

    def test_compound_time_last_summer(self):
        text = "去年夏天我去海边玩"
        metadata = TemporalExtractor.extract_from_text(text)
        
        assert metadata.event_time["description"] == "去年夏天"
        assert metadata.time_context["season"] == "夏天"
        
        expected_year = datetime.now().year - 1
        actual_year = datetime.fromtimestamp(metadata.event_time["timestamp"]).year
        assert actual_year == expected_year

    def test_season_mapping(self):
        # 测试"夏天"
        metadata1 = TemporalExtractor.extract_from_text("夏天我去海边")
        assert metadata1.time_context["season"] == "夏天"
        
        # 测试"夏季"
        metadata2 = TemporalExtractor.extract_from_text("夏季天气很热")
        assert metadata2.time_context["season"] == "夏季"
        
        # 测试"冬天"
        metadata3 = TemporalExtractor.extract_from_text("冬天很冷")
        assert metadata3.time_context["season"] == "冬天"
        
        # 测试"冬季"
        metadata4 = TemporalExtractor.extract_from_text("冬季下雪")
        assert metadata4.time_context["season"] == "冬季"

    def test_life_stage(self):
        text = "大学时期我经常去图书馆"
        metadata = TemporalExtractor.extract_from_text(text)
        assert metadata.time_context["life_stage"] == "大学时期"

    def test_recurrence(self):
        text = "我每天都会看书"
        metadata = TemporalExtractor.extract_from_text(text)
        assert metadata.recurrence["is_recurring"] == True
        assert metadata.recurrence["frequency"] == "daily"

    def test_no_temporal_info(self):
        text = "我喜欢编程"
        metadata = TemporalExtractor.extract_from_text(text)
        assert metadata.event_time == {}
        assert metadata.time_context == {}
        assert metadata.recurrence == {}


class TestTemporalMetadata:
    """测试 TemporalMetadata"""

    def test_to_dict_and_from_dict(self):
        metadata = TemporalMetadata(
            event_time={"timestamp": time.time(), "description": "昨天"},
            time_context={"season": "夏天"},
            recurrence={"is_recurring": True, "frequency": "daily"},
        )
        
        d = metadata.to_dict()
        loaded = TemporalMetadata.from_dict(d)
        
        assert loaded.event_time["description"] == "昨天"
        assert loaded.time_context["season"] == "夏天"
        assert loaded.recurrence["is_recurring"] == True

    def test_get_age_in_days(self):
        # 创建 2 天前的时间戳
        two_days_ago = time.time() - 2 * 86400
        metadata = TemporalMetadata(
            event_time={"timestamp": two_days_ago}
        )
        
        age = metadata.get_age_in_days()
        assert age is not None
        assert abs(age - 2.0) < 0.1

    def test_is_recent(self):
        # 创建 3 天前的时间戳
        three_days_ago = time.time() - 3 * 86400
        metadata = TemporalMetadata(
            event_time={"timestamp": three_days_ago}
        )
        
        assert metadata.is_recent(days=7) == True
        assert metadata.is_recent(days=2) == False


class TestMemoryLayer:
    """测试 MemoryLayer"""

    def test_from_importance_core(self):
        layer = MemoryLayer.from_importance(importance=0.9, emotion_intensity=0.5)
        assert layer == MemoryLayer.CORE

    def test_from_importance_important(self):
        layer = MemoryLayer.from_importance(importance=0.7, emotion_intensity=0.5)
        assert layer == MemoryLayer.IMPORTANT

    def test_from_importance_regular(self):
        layer = MemoryLayer.from_importance(importance=0.3, emotion_intensity=0.3)
        assert layer == MemoryLayer.REGULAR

    def test_from_importance_high_emotion(self):
        layer = MemoryLayer.from_importance(importance=0.5, emotion_intensity=0.9)
        assert layer == MemoryLayer.CORE

    def test_get_forgetting_strength(self):
        assert MemoryLayer.CORE.get_forgetting_strength() == 10.0
        assert MemoryLayer.IMPORTANT.get_forgetting_strength() == 2.0
        assert MemoryLayer.REGULAR.get_forgetting_strength() == 1.0

    def test_get_retrieval_weight(self):
        assert MemoryLayer.CORE.get_retrieval_weight() == 1.0
        assert MemoryLayer.IMPORTANT.get_retrieval_weight() == 0.8
        assert MemoryLayer.REGULAR.get_retrieval_weight() == 0.5


class TestMigration:
    """测试数据库迁移脚本"""

    def test_migration_v1_to_v2(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
            db_path = f.name

        try:
            # 创建 v1 数据库
            conn = sqlite3.connect(db_path)
            conn.execute("""
                CREATE TABLE memories (
                    user_id TEXT NOT NULL,
                    memory_id TEXT NOT NULL,
                    data TEXT NOT NULL,
                    PRIMARY KEY (user_id, memory_id)
                )
            """)

            # 插入测试数据
            test_data_1 = {
                "id": "test_1",
                "content": "用户喜欢编程",
                "importance": 0.9,
                "emotion_intensity": 0.5,
            }
            test_data_2 = {
                "id": "test_2",
                "content": "用户非常焦虑",
                "importance": 0.5,
                "emotion_intensity": 0.9,
            }
            conn.execute(
                "INSERT INTO memories (user_id, memory_id, data) VALUES (?, ?, ?)",
                ("test_user", "test_1", json.dumps(test_data_1))
            )
            conn.execute(
                "INSERT INTO memories (user_id, memory_id, data) VALUES (?, ?, ?)",
                ("test_user", "test_2", json.dumps(test_data_2))
            )
            conn.commit()
            conn.close()

            # 执行迁移
            from migration_v2 import migrate_to_v2
            migrate_to_v2(db_path)

            # 验证
            conn = sqlite3.connect(db_path)

            # 检查 schema_version
            versions = [row[0] for row in conn.execute(
                "SELECT version FROM schema_version ORDER BY version"
            ).fetchall()]
            assert 1 in versions, "应该补上 v1 记录"
            assert 2 in versions, "应该有 v2 记录"

            # 检查 memories 表新字段
            row1 = conn.execute(
                "SELECT data FROM memories WHERE user_id = ? AND memory_id = ?",
                ("test_user", "test_1")
            ).fetchone()
            data1 = json.loads(row1[0])
            assert "layer" in data1, "应该有 layer 字段"
            assert data1["layer"] == 1, "importance=0.9 应该是核心记忆"

            row2 = conn.execute(
                "SELECT data FROM memories WHERE user_id = ? AND memory_id = ?",
                ("test_user", "test_2")
            ).fetchone()
            data2 = json.loads(row2[0])
            assert data2["layer"] == 1, "emotion_intensity=0.9 应该是核心记忆"

            conn.close()
        finally:
            os.unlink(db_path)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
