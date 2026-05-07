"""
缓存连接管理
支持 Redis, Memory, Memcached
"""
import time
import json
try:
    import redis.asyncio as aioredis
except ImportError:
    try:
        import aioredis
    except ImportError:
        aioredis = None
from typing import Any, Optional
from config.cache import CACHE_CONFIG
from loguru import logger

cache_client = None


def _serialize_value(value: Any) -> str:
    """序列化值用于存储"""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, default=str)


def _deserialize_value(value: Any) -> Any:
    """反序列化缓存值"""
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    return value


class MemoryCache:
    """内存缓存实现 - 支持TTL过期机制"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 300):
        self._cache = {}
        self._max_size = max_size
        self._ttl = ttl
    
    async def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            item = self._cache[key]
            # 检查是否过期
            if item["expire_at"] and time.time() > item["expire_at"]:
                # 已过期，删除并返回None
                del self._cache[key]
                return None
            return item["value"]
        return None
    
    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        # 如果缓存已满，删除最旧的一个
        if len(self._cache) >= self._max_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        
        # 计算过期时间
        expire_seconds = ex if ex is not None else self._ttl
        expire_at = time.time() + expire_seconds if expire_seconds > 0 else None
        
        self._cache[key] = {
            "value": value,
            "expire_at": expire_at,
            "created_at": time.time()
        }
        return True
    
    async def delete(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    async def clear(self) -> bool:
        self._cache.clear()
        return True
    
    async def close(self) -> None:
        self._cache.clear()


async def init_cache():
    """初始化缓存连接"""
    global cache_client
    
    if not CACHE_CONFIG["enabled"]:
        cache_client = None
        return
    
    cache_type = CACHE_CONFIG["type"]
    
    if cache_type == "redis":
        if aioredis is None:
            raise ImportError("redis package is required for Redis cache. Install with: pip install redis")
        redis_cfg = CACHE_CONFIG["redis"]
        cache_client = aioredis.from_url(
            f"redis://{redis_cfg['host']}:{redis_cfg['port']}/{redis_cfg['db']}",
            password=redis_cfg["password"],
            max_connections=redis_cfg["max_connections"],
            decode_responses=redis_cfg["decode_responses"],
        )
    elif cache_type == "memory":
        mem_cfg = CACHE_CONFIG["memory"]
        cache_client = MemoryCache(
            max_size=mem_cfg["max_size"],
            ttl=mem_cfg["ttl"],
        )
    elif cache_type == "memcached":
        raise NotImplementedError("Memcached support coming soon")
    else:
        raise ValueError(f"Unsupported cache type: {cache_type}")


async def close_cache():
    """关闭缓存连接"""
    global cache_client
    if cache_client and hasattr(cache_client, "close"):
        await cache_client.close()


async def get_cache(key: str) -> Optional[Any]:
    """获取缓存值"""
    if cache_client is None:
        return None
    full_key = f"{CACHE_CONFIG['prefix']}{key}"
    value = await cache_client.get(full_key)
    return _deserialize_value(value)


async def set_cache(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """设置缓存值"""
    if cache_client is None:
        return False
    full_key = f"{CACHE_CONFIG['prefix']}{key}"
    expire = ttl or CACHE_CONFIG["default_ttl"]
    serialized_value = _serialize_value(value)
    return await cache_client.set(full_key, serialized_value, ex=expire)


async def delete_cache(key: str) -> bool:
    """删除缓存值"""
    if cache_client is None:
        return False
    full_key = f"{CACHE_CONFIG['prefix']}{key}"
    return await cache_client.delete(full_key)
