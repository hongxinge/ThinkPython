"""
缓存配置文件
支持多种缓存类型: redis, memory, memcached
"""
import os


CACHE_CONFIG = {
    # 缓存类型: redis, memory, memcached
    "type": os.getenv("CACHE_TYPE", "redis"),
    
    # 是否启用缓存
    "enabled": os.getenv("CACHE_ENABLED", "True").lower() == "true",
    
    # Redis 配置
    "redis": {
        "host": os.getenv("REDIS_HOST", "127.0.0.1"),
        "port": int(os.getenv("REDIS_PORT", "6379")),
        "db": int(os.getenv("REDIS_DB", "0")),
        "password": os.getenv("REDIS_PASSWORD", None),
        "max_connections": int(os.getenv("REDIS_MAX_CONNECTIONS", "20")),
        "decode_responses": True,
        "socket_timeout": 5,
        "socket_connect_timeout": 5,
    },
    
    # Memcached 配置
    "memcached": {
        "servers": os.getenv("MEMCACHED_SERVERS", "127.0.0.1:11211").split(","),
        "username": os.getenv("MEMCACHED_USERNAME", None),
        "password": os.getenv("MEMCACHED_PASSWORD", None),
    },
    
    # 内存缓存配置 (适用于开发环境)
    "memory": {
        "max_size": int(os.getenv("MEMORY_CACHE_MAX_SIZE", "1000")),
        "ttl": int(os.getenv("MEMORY_CACHE_TTL", "300")),  # 默认5分钟
    },
    
    # 默认过期时间 (秒)
    "default_ttl": int(os.getenv("CACHE_DEFAULT_TTL", "3600")),
    
    # 缓存前缀
    "prefix": os.getenv("CACHE_PREFIX", "thinkpython:"),
}
