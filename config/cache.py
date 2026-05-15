"""
ThinkPython 缓存配置文件

本文件负责配置和管理缓存连接参数，支持多种缓存后端：
- Redis（生产环境推荐，支持持久化和分布式）
- Memory（内存缓存，适合开发和测试，无需额外依赖）
- Memcached（即将支持）

配置原则：
- 优先支持 REDIS_URL 一行配置（开发者友好）
- 同时兼容独立参数配置（host、port、password 等）
- 环境变量优先，未配置时使用合理默认值

使用示例：
    # 方式 1：一行 URL 配置（推荐）
    # .env 中设置: REDIS_URL=redis://:password@localhost:6379/0
    
    # 方式 2：独立参数配置
    # .env 中设置: CACHE_TYPE=redis, REDIS_HOST=localhost, REDIS_PORT=6379
    
    # 兼容旧的 CACHE_CONFIG 字典接口（框架内部使用）
    from config.cache import CACHE_CONFIG
    cache_type = CACHE_CONFIG["type"]
"""
import os


# ==============================
# Redis 配置（支持 URL 或独立参数）
# ==============================

# 优先使用 REDIS_URL 一行配置（开发者友好）
# 格式: redis://[:password]@host:port/db
# 示例: redis://:mypassword@127.0.0.1:6379/0
REDIS_URL = os.getenv("REDIS_URL", "")

# Redis 独立参数（当 REDIS_URL 未设置时使用）
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_MAX_CONNECTIONS = int(os.getenv("REDIS_MAX_CONNECTIONS", "20"))
REDIS_DECODE_RESPONSES = True
REDIS_SOCKET_TIMEOUT = 5
REDIS_SOCKET_CONNECT_TIMEOUT = 5


# ==============================
# 缓存全局配置
# ==============================

# 缓存类型：memory / redis / memcached
CACHE_TYPE = os.getenv("CACHE_TYPE", "memory")

# 是否启用缓存
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "True").lower() == "true"

# 默认过期时间（秒）
CACHE_DEFAULT_TTL = int(os.getenv("CACHE_DEFAULT_TTL", "3600"))

# 缓存键前缀
CACHE_PREFIX = os.getenv("CACHE_PREFIX", "thinkpython:")

# 内存缓存配置
MEMORY_CACHE_MAX_SIZE = int(os.getenv("MEMORY_CACHE_MAX_SIZE", "1000"))
MEMORY_CACHE_TTL = int(os.getenv("MEMORY_CACHE_TTL", "300"))


# ==============================
# 兼容旧接口：CACHE_CONFIG 字典
# ==============================
# 保留 CACHE_CONFIG 字典以兼容框架内部已有的引用方式
# 新代码推荐直接使用上面的独立常量

CACHE_CONFIG = {
    "type": CACHE_TYPE,
    "enabled": CACHE_ENABLED,
    "redis": {
        "host": REDIS_HOST,
        "port": REDIS_PORT,
        "db": REDIS_DB,
        "password": REDIS_PASSWORD,
        "max_connections": REDIS_MAX_CONNECTIONS,
        "decode_responses": REDIS_DECODE_RESPONSES,
        "socket_timeout": REDIS_SOCKET_TIMEOUT,
        "socket_connect_timeout": REDIS_SOCKET_CONNECT_TIMEOUT,
    },
    "memcached": {
        "servers": os.getenv("MEMCACHED_SERVERS", "127.0.0.1:11211").split(","),
        "username": os.getenv("MEMCACHED_USERNAME", None),
        "password": os.getenv("MEMCACHED_PASSWORD", None),
    },
    "memory": {
        "max_size": MEMORY_CACHE_MAX_SIZE,
        "ttl": MEMORY_CACHE_TTL,
    },
    "default_ttl": CACHE_DEFAULT_TTL,
    "prefix": CACHE_PREFIX,
}
