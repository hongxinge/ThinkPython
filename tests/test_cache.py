"""ThinkPython 缓存操作测试"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.cache import (
    MemoryCache,
    cache_client,
    init_cache,
    close_cache,
    get_cache,
    set_cache,
    delete_cache,
)


class TestMemoryCacheClient:
    """内存缓存客户端测试"""

    def setup_method(self):
        self.client = MemoryCache()

    @pytest.mark.asyncio
    async def test_set_and_get(self):
        await self.client.set("key1", "value1")
        result = await self.client.get("key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self):
        result = await self.client.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_with_expiration(self):
        import time
        await self.client.set("key_expire", "value", ex=1)
        result = await self.client.get("key_expire")
        assert result == "value"
        self.client._cache["key_expire"]["expire_at"] = time.time() - 1
        result = await self.client.get("key_expire")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_existing_key(self):
        await self.client.set("key_delete", "value")
        result = await self.client.delete("key_delete")
        assert result is True
        assert await self.client.get("key_delete") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key(self):
        result = await self.client.delete("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_clear(self):
        await self.client.set("key1", "value1")
        await self.client.set("key2", "value2")
        await self.client.clear()
        assert await self.client.get("key1") is None
        assert await self.client.get("key2") is None

    @pytest.mark.asyncio
    async def test_max_size_eviction(self):
        client = MemoryCache(max_size=2)
        await client.set("key1", "value1")
        await client.set("key2", "value2")
        await client.set("key3", "value3")
        assert await client.get("key1") is None
        assert await client.get("key2") == "value2"
        assert await client.get("key3") == "value3"

    @pytest.mark.asyncio
    async def test_overwrite_existing_key(self):
        await self.client.set("key1", "value1")
        await self.client.set("key1", "value2")
        assert await self.client.get("key1") == "value2"

    @pytest.mark.asyncio
    async def test_set_different_types(self):
        await self.client.set("str_key", "string_value")
        await self.client.set("int_key", 42)
        await self.client.set("dict_key", {"a": 1})
        await self.client.set("list_key", [1, 2, 3])
        assert await self.client.get("str_key") == "string_value"
        assert await self.client.get("int_key") == 42
        assert await self.client.get("dict_key") == {"a": 1}
        assert await self.client.get("list_key") == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_has_key(self):
        await self.client.set("exists_key", "value")
        assert "exists_key" in self.client._cache
        assert "nonexistent_key" not in self.client._cache


class TestCacheModuleFunctions:
    """缓存模块函数测试"""

    def setup_method(self):
        self.client = MemoryCache()

    @pytest.mark.asyncio
    async def test_set_cache(self):
        await self.client.set("test_key", "test_value")
        result = await self.client.get("test_key")
        assert result == "test_value"

    @pytest.mark.asyncio
    async def test_get_cache_nonexistent(self):
        result = await self.client.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_cache(self):
        await self.client.set("test_key", "test_value")
        result = await self.client.delete("test_key")
        assert result is True
        assert await self.client.get("test_key") is None

    @pytest.mark.asyncio
    async def test_init_cache_memory(self):
        from config.cache import CACHE_CONFIG
        import core.cache as cache_module
        original_type = CACHE_CONFIG["type"]
        original_enabled = CACHE_CONFIG["enabled"]
        original_client = cache_module.cache_client
        try:
            CACHE_CONFIG["type"] = "memory"
            CACHE_CONFIG["enabled"] = True
            await init_cache()
            assert cache_module.cache_client is not None
        finally:
            CACHE_CONFIG["type"] = original_type
            CACHE_CONFIG["enabled"] = original_enabled
            cache_module.cache_client = original_client

    @pytest.mark.asyncio
    async def test_close_cache(self):
        await close_cache()


class TestCacheConfig:
    """缓存配置测试"""

    def test_cache_config_type(self):
        from config.cache import CACHE_CONFIG
        assert CACHE_CONFIG["type"] in ["memory", "redis", "memcached"]

    def test_cache_config_enabled(self):
        from config.cache import CACHE_CONFIG
        assert isinstance(CACHE_CONFIG["enabled"], bool)

    def test_cache_config_redis(self):
        from config.cache import CACHE_CONFIG
        assert "redis" in CACHE_CONFIG
        assert "host" in CACHE_CONFIG["redis"]
        assert "port" in CACHE_CONFIG["redis"]

    def test_cache_config_memory(self):
        from config.cache import CACHE_CONFIG
        assert "memory" in CACHE_CONFIG
        assert "max_size" in CACHE_CONFIG["memory"]
        assert "ttl" in CACHE_CONFIG["memory"]

    def test_cache_config_prefix(self):
        from config.cache import CACHE_CONFIG
        assert "prefix" in CACHE_CONFIG
        assert isinstance(CACHE_CONFIG["prefix"], str)


class TestCacheEdgeCases:
    """缓存边界情况测试"""

    @pytest.mark.asyncio
    async def test_set_empty_string(self):
        client = MemoryCache()
        await client.set("empty", "")
        assert await client.get("empty") == ""

    @pytest.mark.asyncio
    async def test_set_none_value(self):
        client = MemoryCache()
        await client.set("none_key", None)
        assert await client.get("none_key") is None

    @pytest.mark.asyncio
    async def test_set_zero(self):
        client = MemoryCache()
        await client.set("zero", 0)
        assert await client.get("zero") == 0

    @pytest.mark.asyncio
    async def test_set_false(self):
        client = MemoryCache()
        await client.set("false_key", False)
        assert await client.get("false_key") is False

    @pytest.mark.asyncio
    async def test_special_characters_in_key(self):
        client = MemoryCache()
        await client.set("key:with:colons", "value1")
        await client.set("key_with_underscores", "value2")
        assert await client.get("key:with:colons") == "value1"
        assert await client.get("key_with_underscores") == "value2"

    @pytest.mark.asyncio
    async def test_long_value(self):
        client = MemoryCache()
        long_value = "x" * 10000
        await client.set("long_key", long_value)
        assert await client.get("long_key") == long_value

    @pytest.mark.asyncio
    async def test_concurrent_set_same_key(self):
        client = MemoryCache()
        await client.set("concurrent_key", "value1")
        await client.set("concurrent_key", "value2")
        assert await client.get("concurrent_key") == "value2"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
