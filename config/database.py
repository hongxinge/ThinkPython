"""
ThinkPython 数据库配置文件

本文件负责配置和管理数据库连接参数，支持多种数据库类型：
- SQLite（内置，零配置，适合开发和测试）
- MySQL（通过 aiomysql 异步驱动）
- PostgreSQL（通过 asyncpg 异步驱动）
- SQL Server / MSSQL（通过 aioodbc 异步驱动）

配置原则：
- 优先支持 DATABASE_URL 一行配置（开发者友好）
- 同时兼容独立参数配置（DB_TYPE、DB_HOST、DB_PORT 等）
- 环境变量优先，未配置时使用合理默认值

使用示例：
    # 方式 1：一行 URL 配置（推荐）
    # .env 中设置: DATABASE_URL=sqlite:///data/database.db
    # .env 中设置: DATABASE_URL=mysql+aiomysql://root:pass@localhost:3306/thinkpython?charset=utf8mb4
    # .env 中设置: DATABASE_URL=postgresql+asyncpg://root:pass@localhost:5432/thinkpython
    
    # 方式 2：独立参数配置
    # .env 中设置: DB_TYPE=sqlite, DB_SQLITE_PATH=/path/to/db.sqlite
    
    # 兼容旧的 DATABASE_CONFIG 字典接口（框架内部使用）
    from config.database import DATABASE_CONFIG
    pool_size = DATABASE_CONFIG["pool_size"]
"""
import os
from pathlib import Path


# ==============================
# 数据库连接配置（支持 URL 或独立参数）
# ==============================

# 优先使用 DATABASE_URL 一行配置（开发者友好）
# 格式: dialect+driver://username:password@host:port/database?params
# 示例: DATABASE_URL=sqlite+aiosqlite:///data/database.db
# 示例: DATABASE_URL=mysql+aiomysql://root:pass@localhost:3306/mydb?charset=utf8mb4
DATABASE_URL = os.getenv("DATABASE_URL", "")

# 数据库类型，支持: mysql, postgresql, sqlite, mssql
DB_TYPE = os.getenv("DB_TYPE", "sqlite")

# 是否启用数据库
DB_ENABLED = os.getenv("DB_ENABLED", "True").lower() == "true"

# MySQL / PostgreSQL / MSSQL 连接参数
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME", "thinkpython")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# 连接池配置
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))
DB_POOL_PRE_PING = os.getenv("DB_POOL_PRE_PING", "True").lower() == "true"

# SQLite 专属配置
DB_SQLITE_PATH = os.getenv("DB_SQLITE_PATH", str(Path(__file__).resolve().parent.parent / "data" / "database.db"))

# 其他配置
DB_CHARSET = os.getenv("DB_CHARSET", "utf8mb4")
DB_ECHO = os.getenv("DB_ECHO", "False").lower() == "true"


# ==============================
# 兼容旧接口：DATABASE_CONFIG 字典
# ==============================
# 保留 DATABASE_CONFIG 字典以兼容框架内部已有的引用方式
# 新代码推荐直接使用上面的独立常量

DATABASE_CONFIG = {
    "type": DB_TYPE,
    "enabled": DB_ENABLED,
    "host": DB_HOST,
    "port": DB_PORT,
    "database": DB_NAME,
    "username": DB_USER,
    "password": DB_PASSWORD,
    "pool_size": DB_POOL_SIZE,
    "max_overflow": DB_MAX_OVERFLOW,
    "pool_recycle": DB_POOL_RECYCLE,
    "pool_pre_ping": DB_POOL_PRE_PING,
    "sqlite_path": DB_SQLITE_PATH,
    "charset": DB_CHARSET,
    "echo": DB_ECHO,
}


def get_database_url(config: dict = None) -> str:
    """根据当前数据库配置生成 SQLAlchemy 连接 URL
    
    如果设置了 DATABASE_URL 环境变量，则直接返回该 URL（最高优先级）。
    否则根据 DATABASE_CONFIG 中的参数动态生成 URL。
    
    不同数据库类型对应不同的异步驱动和 URL 格式：
    - SQLite: sqlite+aiosqlite:///path/to/database.db
    - MySQL: mysql+aiomysql://user:pass@host:port/dbname?charset=utf8mb4
    - PostgreSQL: postgresql+asyncpg://user:pass@host:port/dbname
    - MSSQL: mssql+aioodbc://user:pass@host:port/dbname?driver=...
    
    Args:
        config: 自定义配置字典，不传则使用默认的 DATABASE_CONFIG
        
    Returns:
        str: 完整的数据库连接 URL，可直接传给 SQLAlchemy 的 create_async_engine
        
    Raises:
        ValueError: 当传入不支持的数据库类型时抛出
        
    使用示例:
        >>> get_database_url()
        'sqlite+aiosqlite:///G:/ThinkPython/data/database.db'
        
        >>> get_database_url({"type": "mysql", "username": "root", "password": "123",
        ...                   "host": "localhost", "port": 3306, "database": "test",
        ...                   "charset": "utf8mb4"})
        'mysql+aiomysql://root:123@localhost:3306/test?charset=utf8mb4'
    """
    # 最高优先级：DATABASE_URL 一行配置
    if DATABASE_URL:
        return DATABASE_URL
    
    cfg = config or DATABASE_CONFIG
    db_type = cfg["type"]
    
    if db_type == "sqlite":
        # SQLite 使用 aiosqlite 异步驱动，/// 表示绝对路径
        return f"sqlite+aiosqlite:///{cfg['sqlite_path']}"
    elif db_type == "mysql":
        # MySQL 使用 aiomysql 异步驱动
        return f"mysql+aiomysql://{cfg['username']}:{cfg['password']}@{cfg['host']}:{cfg['port']}/{cfg['database']}?charset={cfg['charset']}"
    elif db_type == "postgresql":
        # PostgreSQL 使用 asyncpg 异步驱动
        return f"postgresql+asyncpg://{cfg['username']}:{cfg['password']}@{cfg['host']}:{cfg['port']}/{cfg['database']}"
    elif db_type == "mssql":
        # SQL Server 使用 aioodbc 异步驱动，需要指定 ODBC Driver
        return f"mssql+aioodbc://{cfg['username']}:{cfg['password']}@{cfg['host']}:{cfg['port']}/{cfg['database']}?driver=ODBC+Driver+17+for+SQL+Server"
    else:
        raise ValueError(f"Unsupported database type: {db_type}")
