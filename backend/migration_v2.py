"""
数据库迁移脚本 v1 → v2

修复：
1. 统计输出在 conn.close() 之前执行
2. 使用 emotion_intensity 分配 layer
3. 补上 v1 记录
"""

import sqlite3
import json
import time
import shutil


def get_current_version(conn: sqlite3.Connection) -> int:
    """获取当前数据库版本"""
    try:
        row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
        return row[0] if row and row[0] else 1
    except sqlite3.OperationalError:
        # schema_version 表不存在，说明是 v1
        return 1


def migrate_to_v2(db_path: str):
    """迁移数据库到 v2 版本（修复版）"""
    
    # 1. 备份数据库
    backup_path = db_path + f".backup_{int(time.time())}"
    shutil.copy(db_path, backup_path)
    print(f"✓ 已备份到 {backup_path}")
    
    conn = sqlite3.connect(db_path)
    
    # 2. 检查当前版本
    current_version = get_current_version(conn)
    if current_version >= 2:
        print(f"数据库已是 v{current_version}，无需迁移")
        conn.close()
        return
    
    print(f"开始从 v{current_version} 迁移到 v2...")
    
    # 3. 创建 schema_version 表（如果不存在）
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at REAL NOT NULL,
            description TEXT
        )
    """)
    
    # 4. 补上 v1 记录（如果不存在）
    existing_versions = [row[0] for row in conn.execute("SELECT version FROM schema_version").fetchall()]
    if 1 not in existing_versions:
        conn.execute(
            "INSERT INTO schema_version (version, applied_at, description) VALUES (?, ?, ?)",
            (1, time.time(), "初始版本（补记录）")
        )
    
    # 5. 创建 user_profiles 表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id TEXT PRIMARY KEY,
            profile_data TEXT NOT NULL,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            version INTEGER DEFAULT 1
        )
    """)
    
    # 6. 为现有记忆增加 layer 和 temporal_data 字段（修复版：使用 emotion_intensity）
    rows = conn.execute("SELECT user_id, memory_id, data FROM memories").fetchall()
    now = time.time()
    
    migrated_count = 0
    layer_stats = {1: 0, 2: 0, 3: 0}  # 统计各层级数量
    
    for user_id, memory_id, data_str in rows:
        memory_data = json.loads(data_str)
        importance = memory_data.get("importance", 0.5)
        emotion_intensity = memory_data.get("emotion_intensity", 0.5)  # 修复：使用 emotion_intensity
        
        # 根据重要性和情感强度分配层级（与 MemoryLayer.from_importance 一致）
        if importance >= 0.8 or emotion_intensity >= 0.8:
            layer = 1  # 核心
        elif importance >= 0.6 or emotion_intensity >= 0.7:
            layer = 2  # 重要
        else:
            layer = 3  # 常规
        
        # 增加新字段
        memory_data["layer"] = layer
        memory_data["temporal_data"] = {}
        
        # 更新 JSON
        new_data_str = json.dumps(memory_data, ensure_ascii=False)
        conn.execute(
            "UPDATE memories SET data = ? WHERE user_id = ? AND memory_id = ?",
            (new_data_str, user_id, memory_id)
        )
        
        layer_stats[layer] += 1
        migrated_count += 1
    
    # 7. 记录迁移版本
    conn.execute(
        "INSERT INTO schema_version (version, applied_at, description) VALUES (?, ?, ?)",
        (2, now, "记忆系统升级：档案卡+分层+时间标签")
    )
    
    conn.commit()
    
    # 8. 统计输出（修复：在 conn.close() 之前）
    print(f"✓ 已迁移 {migrated_count} 条记忆")
    print(f"✓ 层级分布: 核心={layer_stats[1]}, 重要={layer_stats[2]}, 常规={layer_stats[3]}")
    
    conn.close()
    print("✓ 迁移完成！")


def rollback_to_v1(db_path: str, backup_path: str):
    """回滚到 v1 版本"""
    print(f"正在回滚到 {backup_path}...")
    shutil.copy(backup_path, db_path)
    print("✓ 回滚完成")


if __name__ == "__main__":
    import os
    
    # 默认数据库路径
    db_path = os.path.join(os.path.dirname(__file__), "giftia.db")
    
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        exit(1)
    
    migrate_to_v2(db_path)
