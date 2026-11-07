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

    def test_database_url_priority(self, monkeypatch):
        """DATABASE_URL 非空时必须优先于分散的独立参数"""
        import config.database as db_config

        expected = "postgresql+asyncpg://user:pass@localhost:5432/demo"
        monkeypatch.setattr(db_config, "DATABASE_URL", expected)

        assert db_config.get_database_url() == expected
        # 即使传入自定义配置，DATABASE_URL 仍应优先
        assert db_config.get_database_url({"type": "sqlite", "sqlite_path": "./x.db"}) == expected

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
        """各数据库 URL 必须能被 SQLAlchemy 正确解析出驱动"""
        from sqlalchemy.engine import make_url

        expected = {
            "sqlite+aiosqlite:///./data/database.db": "sqlite+aiosqlite",
            "mysql+aiomysql://root:pass@localhost:3306/mydb?charset=utf8mb4": "mysql+aiomysql",
            "postgresql+asyncpg://user:pass@localhost:5432/mydb": "postgresql+asyncpg",
            "mssql+aioodbc://sa:pass@localhost:1433/mydb": "mssql+aioodbc",
        }
        for url, drivername in expected.items():
            assert make_url(url).drivername == drivername

    def test_valid_redis_url_formats(self):
        """Redis URL 必须能被正确解析出 scheme 与主机"""
        from urllib.parse import urlparse

        cases = [
            ("redis://127.0.0.1:6379/0", "127.0.0.1", 6379),
            ("redis://:password@127.0.0.1:6379/0", "127.0.0.1", 6379),
            ("redis://user:password@redis-server:6379/1", "redis-server", 6379),
        ]
        for url, host, port in cases:
            parsed = urlparse(url)
            assert parsed.scheme == "redis"
            assert parsed.hostname == host
            assert parsed.port == port


# ============== 配置优先级测试 ==============

class TestConfigPriority:
    """配置优先级测试"""

    def test_database_url_empty_uses_fallback(self, monkeypatch):
        """DATABASE_URL 为空时必须根据 DB_TYPE 生成可用的 fallback URL"""
        import config.database as db_config
        from sqlalchemy.engine import make_url

        monkeypatch.setattr(db_config, "DATABASE_URL", "")
        url = db_config.get_database_url()

        assert url
        # fallback 的方言必须与当前 DB_TYPE 一致
        assert make_url(url).get_backend_name() == db_config.DATABASE_CONFIG["type"]

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
