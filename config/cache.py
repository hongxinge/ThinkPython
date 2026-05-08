"""
ThinkPython 缓存配置文件

本文件负责配置和管理缓存连接参数，支持多种缓存后端：
- Redis（生产环境推荐，支持持久化和分布式）
- Memory（内存缓存，适合开发和测试，无需额外依赖）
- Memcached（即将支持）

所有配置项均支持通过 .env 环境变量覆盖。

使用示例：
    from config.cache import CACHE_CONFIG
    
    # 查看当前缓存类型
    cache_type = CACHE_CONFIG["type"]  # "memory" 或 "redis"
    
    # 获取 Redis 配置
    redis_host = CACHE_CONFIG["redis"]["host"]
"""
import os


# 缓存配置字典，集中管理所有缓存连接参数
CACHE_CONFIG = {
    # 缓存类型，支持: redis, memory, memcached
    # 默认使用 memory（零配置，适合开发环境）
    # 生产环境建议使用 redis，支持持久化和分布式缓存
    "type": os.getenv("CACHE_TYPE", "memory"),
    
    # 是否启用缓存，设为 False 时可完全关闭缓存功能
    "enabled": os.getenv("CACHE_ENABLED", "True").lower() == "true",
    
    # Redis 配置
    # Redis 是一个高性能的内存键值存储数据库，支持丰富的数据结构和持久化
    "redis": {
        "host": os.getenv("REDIS_HOST", "127.0.0.1"),  # Redis 服务器地址
        "port": int(os.getenv("REDIS_PORT", "6379")),  # Redis 端口，默认 6379
        "db": int(os.getenv("REDIS_DB", "0")),  # Redis 数据库编号（0-15），用于隔离不同业务的缓存数据
        "password": os.getenv("REDIS_PASSWORD", None),  # Redis 认证密码，未设置密码时为 None
        "max_connections": int(os.getenv("REDIS_MAX_CONNECTIONS", "20")),  # 连接池最大连接数
        "decode_responses": True,  # 自动将返回的 bytes 解码为 str，方便直接使用
        "socket_timeout": 5,  # Socket 读取超时时间（秒）
        "socket_connect_timeout": 5,  # Socket 连接超时时间（秒）
    },
    
    # Memcached 配置
    # Memcached 是一个高性能的分布式内存对象缓存系统
    "memcached": {
        "servers": os.getenv("MEMCACHED_SERVERS", "127.0.0.1:11211").split(","),  # Memcached 服务器列表，支持集群
        "username": os.getenv("MEMCACHED_USERNAME", None),  # SASL 认证用户名
        "password": os.getenv("MEMCACHED_PASSWORD", None),  # SASL 认证密码
    },
    
    # 内存缓存配置（适用于开发环境）
    # 使用 Python 字典实现，无需安装额外依赖，但数据不会持久化
    "memory": {
        "max_size": int(os.getenv("MEMORY_CACHE_MAX_SIZE", "1000")),  # 最大缓存条目数，超出时删除最旧的
        "ttl": int(os.getenv("MEMORY_CACHE_TTL", "300")),  # 默认过期时间（秒），300秒 = 5分钟
    },
    
    # 默认过期时间（秒），所有缓存操作不指定过期时间时使用此值
    # 3600秒 = 1小时
    "default_ttl": int(os.getenv("CACHE_DEFAULT_TTL", "3600")),
    
    # 缓存键前缀，用于区分不同应用或环境的缓存数据
    # 例如前缀为 "thinkpython:" 时，实际存储的键为 "thinkpython:user:1"
    "prefix": os.getenv("CACHE_PREFIX", "thinkpython:"),
}
