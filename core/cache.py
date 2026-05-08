"""
ThinkPython 缓存连接管理

本模块负责管理缓存后端（Redis / Memory / Memcached）的连接和操作，包括：
- 初始化缓存客户端连接
- 提供统一的缓存操作接口（get / set / delete）
- 实现内存缓存的 TTL 过期机制
- 自动序列化/反序列化缓存值

核心组件：
- cache_client: 全局缓存客户端实例，根据配置类型自动选择 Redis 或 Memory
- MemoryCache: 内存缓存实现类，支持 TTL 过期和容量限制
- init_cache() / close_cache(): 缓存连接生命周期管理
- get_cache() / set_cache() / delete_cache(): 统一的缓存操作函数

使用示例:
    from core.cache import init_cache, get_cache, set_cache, delete_cache
    
    # 应用启动时初始化
    await init_cache()
    
    # 设置缓存（默认过期时间 1 小时）
    await set_cache("user:1", {"name": "张三", "age": 25})
    
    # 设置缓存并指定过期时间（60 秒）
    await set_cache("user:1", {"name": "张三"}, ttl=60)
    
    # 获取缓存
    data = await get_cache("user:1")  # 返回 {"name": "张三", "age": 25}
    
    # 删除缓存
    await delete_cache("user:1")
    
    # 应用关闭时关闭连接
    await close_cache()
"""
import time
import json
# 尝试导入 Redis 异步客户端，支持两种包名（redis 和 aioredis）
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

# 全局缓存客户端实例，初始化后根据配置类型为 Redis 连接或 MemoryCache 实例
cache_client = None


def _serialize_value(value: Any) -> str:
    """将值序列化为字符串以便存储到缓存中
    
    对于字符串直接返回，对于其他类型（dict、list、对象等）使用 JSON 序列化。
    
    Args:
        value: 需要序列化的值，可以是任意类型
        
    Returns:
        str: 序列化后的字符串
        
    使用示例:
        >>> _serialize_value("hello")
        'hello'
        >>> _serialize_value({"name": "张三"})
        '{"name": "张三"}'
    """
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, default=str)


def _deserialize_value(value: Any) -> Any:
    """将缓存中读取的字符串反序列化为原始类型
    
    尝试将字符串解析为 JSON 对象，如果解析失败则返回原始字符串。
    
    Args:
        value: 从缓存中读取的值
        
    Returns:
        Any: 反序列化后的值，如果是 JSON 字符串则返回 dict/list，否则返回原始值
        
    使用示例:
        >>> _deserialize_value('{"name": "张三"}')
        {'name': '张三'}
        >>> _deserialize_value("hello")
        'hello'
        >>> _deserialize_value(None)
        None
    """
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            # 不是有效的 JSON 字符串，直接返回原始值
            return value
    return value


class MemoryCache:
    """内存缓存实现 - 支持 TTL 过期机制
    
    使用 Python 字典作为底层存储，适用于开发环境或不需要持久化的场景。
    特点：
    - 零依赖，无需安装 Redis 等外部服务
    - 支持 TTL（Time-To-Live）过期时间
    - 支持最大容量限制，超出时自动删除最旧的条目
    - 数据不持久化，进程重启后所有缓存丢失
    
    使用示例:
        cache = MemoryCache(max_size=1000, ttl=300)
        await cache.set("key", {"data": "value"})
        result = await cache.get("key")
        await cache.delete("key")
    """
    
    def __init__(self, max_size: int = 1000, ttl: int = 300):
        """初始化内存缓存
        
        Args:
            max_size: 缓存最大条目数，超出时删除最旧的条目
            ttl: 默认过期时间（秒），0 表示永不过期
        """
        self._cache = {}  # 底层存储字典，格式: {key: {"value": ..., "expire_at": ..., "created_at": ...}}
        self._max_size = max_size
        self._ttl = ttl
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值
        
        如果 key 存在且未过期，返回值；否则返回 None 并删除过期条目。
        
        Args:
            key: 缓存键
            
        Returns:
            Optional[Any]: 缓存值，不存在或已过期时返回 None
        """
        if key in self._cache:
            item = self._cache[key]
            # 检查是否过期（expire_at 为 None 表示永不过期）
            if item["expire_at"] and time.time() > item["expire_at"]:
                # 已过期，删除该条目并返回 None
                del self._cache[key]
                return None
            return item["value"]
        return None
    
    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """设置缓存值
        
        如果缓存已满，先删除最旧的条目再添加新条目。
        
        Args:
            key: 缓存键
            value: 缓存值
            ex: 过期时间（秒），不传则使用默认 TTL
            
        Returns:
            bool: 始终返回 True 表示设置成功
        """
        # 如果缓存已满，删除最旧的一个条目（按字典插入顺序）
        if len(self._cache) >= self._max_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        
        # 计算过期时间戳
        expire_seconds = ex if ex is not None else self._ttl
        expire_at = time.time() + expire_seconds if expire_seconds > 0 else None
        
        # 存储缓存条目
        self._cache[key] = {
            "value": value,
            "expire_at": expire_at,  # 过期时间戳，None 表示永不过期
            "created_at": time.time()  # 创建时间戳
        }
        return True
    
    async def delete(self, key: str) -> bool:
        """删除指定缓存键
        
        Args:
            key: 缓存键
            
        Returns:
            bool: 删除成功返回 True，键不存在返回 False
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    async def clear(self) -> bool:
        """清空所有缓存
        
        Returns:
            bool: 始终返回 True
        """
        self._cache.clear()
        return True
    
    async def close(self) -> None:
        """关闭缓存连接，清空所有数据"""
        self._cache.clear()


async def init_cache():
    """初始化缓存连接
    
    根据 config/cache.py 中的配置创建对应的缓存客户端：
    - redis: 创建 Redis 异步连接池
    - memory: 创建 MemoryCache 实例
    - memcached: 暂不支持，会抛出 NotImplementedError
    
    如果 CACHE_CONFIG["enabled"] 为 False，则不初始化任何缓存客户端。
    
    使用示例:
        from core.cache import init_cache
        
        await init_cache()
    """
    global cache_client
    
    if not CACHE_CONFIG["enabled"]:
        cache_client = None
        return
    
    cache_type = CACHE_CONFIG["type"]
    
    if cache_type == "redis":
        # 检查 Redis 依赖是否已安装
        if aioredis is None:
            raise ImportError("redis package is required for Redis cache. Install with: pip install redis")
        redis_cfg = CACHE_CONFIG["redis"]
        # 使用 from_url 方式创建 Redis 连接，自动管理连接池
        cache_client = aioredis.from_url(
            f"redis://{redis_cfg['host']}:{redis_cfg['port']}/{redis_cfg['db']}",
            password=redis_cfg["password"],
            max_connections=redis_cfg["max_connections"],
            decode_responses=redis_cfg["decode_responses"],
        )
    elif cache_type == "memory":
        # 创建内存缓存实例，使用配置中的容量和 TTL 参数
        mem_cfg = CACHE_CONFIG["memory"]
        cache_client = MemoryCache(
            max_size=mem_cfg["max_size"],
            ttl=mem_cfg["ttl"],
        )
    elif cache_type == "memcached":
        # Memcached 支持尚未实现
        raise NotImplementedError("Memcached support coming soon")
    else:
        raise ValueError(f"Unsupported cache type: {cache_type}")


async def close_cache():
    """关闭缓存连接
    
    如果缓存客户端有 close 方法，则调用它释放资源。
    Redis 客户端会关闭连接池中的所有连接，MemoryCache 会清空数据。
    
    使用示例:
        from core.cache import close_cache
        
        await close_cache()
    """
    global cache_client
    if cache_client and hasattr(cache_client, "close"):
        await cache_client.close()


async def get_cache(key: str) -> Optional[Any]:
    """获取缓存值
    
    自动添加配置的缓存前缀，并对读取的值进行反序列化处理。
    
    Args:
        key: 缓存键（不含前缀），例如 "user:1"
        
    Returns:
        Optional[Any]: 缓存值，缓存未启用或 key 不存在时返回 None
        
    使用示例:
        data = await get_cache("user:1")
        if data:
            print(data["name"])
    """
    if cache_client is None:
        return None
    # 拼接完整的缓存键（带前缀）
    full_key = f"{CACHE_CONFIG['prefix']}{key}"
    value = await cache_client.get(full_key)
    # 反序列化为 Python 对象
    return _deserialize_value(value)


async def set_cache(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """设置缓存值
    
    自动添加配置的缓存前缀，并对值进行序列化处理后存储。
    
    Args:
        key: 缓存键（不含前缀），例如 "user:1"
        value: 缓存值，可以是任意可 JSON 序列化的类型
        ttl: 过期时间（秒），不传则使用配置的默认过期时间
        
    Returns:
        bool: 设置成功返回 True，缓存未启用返回 False
        
    使用示例:
        # 使用默认过期时间
        await set_cache("user:1", {"name": "张三", "age": 25})
        
        # 指定 60 秒过期
        await set_cache("user:1", {"name": "张三"}, ttl=60)
    """
    if cache_client is None:
        return False
    # 拼接完整的缓存键（带前缀）
    full_key = f"{CACHE_CONFIG['prefix']}{key}"
    expire = ttl or CACHE_CONFIG["default_ttl"]
    # 序列化为 JSON 字符串
    serialized_value = _serialize_value(value)
    return await cache_client.set(full_key, serialized_value, ex=expire)


async def delete_cache(key: str) -> bool:
    """删除缓存值
    
    自动添加配置的缓存前缀后删除。
    
    Args:
        key: 缓存键（不含前缀），例如 "user:1"
        
    Returns:
        bool: 删除成功返回 True，缓存未启用返回 False
        
    使用示例:
        await delete_cache("user:1")
    """
    if cache_client is None:
        return False
    # 拼接完整的缓存键（带前缀）
    full_key = f"{CACHE_CONFIG['prefix']}{key}"
    return await cache_client.delete(full_key)
