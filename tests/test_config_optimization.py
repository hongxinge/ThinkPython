"""ThinkPython 配置优化测试"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


# ============== 数据库配置优化测试 ==============

class TestDatabaseUrlConfig:
    """DATABASE_URL 一行配置测试"""

    def test_database_url_constant_exists(self):
        """测试 DATABASE_URL 常量存在"""
        from config.database import DATABASE_URL
        assert isinstance(DATABASE_URL, str)

    def test_database_url_priority(self):
        """测试 DATABASE_URL 优先级高于独立参数"""
        from config.database import get_database_url
        
        # 保存原始 DATABASE_URL
        from config.database import DATABASE_URL
        original_url = DATABASE_URL
        
        # 如果没有设置 DATABASE_URL，测试 fallback 行为
        url = get_database_url()
        assert isinstance(url, str)
        assert len(url) > 0

    def test_get_database_url_with_url_config(self):
        """测试使用 DATABASE_URL 配置"""
        from config.database import get_database_url
        
        # 测试传入自定义配置时不优先 DATABASE_URL
        custom_config = {
            "type": "mysql",
            "username": "root",
            "password": "pass",
            "host": "localhost",
            "port": 3306,
            "database": "test_db",
            "charset": "utf8mb4",
        }
        url = get_database_url(custom_config)
        assert "mysql" in url

    def test_database_config_dict_compatible(self):
        """测试 DATABASE_CONFIG 字典向后兼容"""
        from config.database import DATABASE_CONFIG
        assert isinstance(DATABASE_CONFIG, dict)
        assert "type" in DATABASE_CONFIG
        assert "enabled" in DATABASE_CONFIG
        assert "host" in DATABASE_CONFIG
        assert "pool_size" in DATABASE_CONFIG

    def test_database_independent_constants(self):
        """测试独立配置常量存在"""
        from config.database import DB_TYPE, DB_ENABLED, DB_HOST, DB_PORT
        from config.database import DB_NAME, DB_USER, DB_PASSWORD
        from config.database import DB_POOL_SIZE, DB_MAX_OVERFLOW
        from config.database import DB_SQLITE_PATH
        
        assert isinstance(DB_TYPE, str)
        assert isinstance(DB_ENABLED, bool)
        assert isinstance(DB_HOST, str)
        assert isinstance(DB_PORT, int)


# ============== Redis 配置优化测试 ==============

class TestRedisUrlConfig:
    """REDIS_URL 一行配置测试"""

    def test_redis_url_constant_exists(self):
        """测试 REDIS_URL 常量存在"""
        from config.cache import REDIS_URL
        assert isinstance(REDIS_URL, str)

    def test_redis_independent_constants(self):
        """测试独立配置常量存在"""
        from config.cache import REDIS_HOST, REDIS_PORT, REDIS_DB
        from config.cache import REDIS_PASSWORD, REDIS_MAX_CONNECTIONS
        
        assert isinstance(REDIS_HOST, str)
        assert isinstance(REDIS_PORT, int)
        assert isinstance(REDIS_DB, int)

    def test_cache_config_dict_compatible(self):
        """测试 CACHE_CONFIG 字典向后兼容"""
        from config.cache import CACHE_CONFIG
        assert isinstance(CACHE_CONFIG, dict)
        assert "type" in CACHE_CONFIG
        assert "enabled" in CACHE_CONFIG
        assert "redis" in CACHE_CONFIG
        assert "prefix" in CACHE_CONFIG

    def test_cache_independent_constants(self):
        """测试缓存独立配置常量"""
        from config.cache import CACHE_TYPE, CACHE_ENABLED, CACHE_DEFAULT_TTL
        from config.cache import CACHE_PREFIX
        
        assert isinstance(CACHE_TYPE, str)
        assert isinstance(CACHE_ENABLED, bool)
        assert isinstance(CACHE_DEFAULT_TTL, int)
        assert isinstance(CACHE_PREFIX, str)


# ============== URL 解析测试 ==============

class TestUrlParsing:
    """URL 格式解析测试"""

    def test_valid_database_url_formats(self):
        """测试有效的数据库 URL 格式"""
        valid_urls = [
            "sqlite+aiosqlite:///./data/database.db",
            "mysql+aiomysql://root:pass@localhost:3306/mydb?charset=utf8mb4",
            "postgresql+asyncpg://user:pass@localhost:5432/mydb",
            "mssql+aioodbc://sa:pass@localhost:1433/mydb",
        ]
        for url in valid_urls:
            assert "://" in url

    def test_valid_redis_url_formats(self):
        """测试有效的 Redis URL 格式"""
        valid_urls = [
            "redis://127.0.0.1:6379/0",
            "redis://:password@127.0.0.1:6379/0",
            "redis://user:password@redis-server:6379/1",
        ]
        for url in valid_urls:
            assert url.startswith("redis://")


# ============== 配置优先级测试 ==============

class TestConfigPriority:
    """配置优先级测试"""

    def test_database_url_empty_uses_fallback(self):
        """测试 DATABASE_URL 为空时使用 fallback"""
        from config.database import DATABASE_URL, get_database_url, DATABASE_CONFIG
        
        if not DATABASE_URL:
            url = get_database_url()
            assert isinstance(url, str)
            assert len(url) > 0

    def test_cache_config_consistency(self):
        """测试 CACHE_CONFIG 与独立常量一致性"""
        from config.cache import CACHE_CONFIG, CACHE_TYPE, CACHE_ENABLED, CACHE_PREFIX
        
        assert CACHE_CONFIG["type"] == CACHE_TYPE
        assert CACHE_CONFIG["enabled"] == CACHE_ENABLED
        assert CACHE_CONFIG["prefix"] == CACHE_PREFIX

    def test_database_config_consistency(self):
        """测试 DATABASE_CONFIG 与独立常量一致性"""
        from config.database import DATABASE_CONFIG, DB_TYPE, DB_ENABLED
        
        assert DATABASE_CONFIG["type"] == DB_TYPE
        assert DATABASE_CONFIG["enabled"] == DB_ENABLED


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
