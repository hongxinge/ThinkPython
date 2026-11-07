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


# 异步驱动 -> 同步驱动映射
# Alembic 的迁移命令在同步上下文中执行，必须使用同步驱动。
# SQLite 的同步驱动（pysqlite）由标准库提供，零额外依赖；
# MySQL 使用 pymysql（aiomysql 已依赖它，无需额外安装）；
# PostgreSQL / MSSQL 的同步驱动属于可选依赖，缺失时给出明确提示。
_SYNC_DRIVER_MAP = {
    "sqlite": "sqlite",
    "mysql": "mysql+pymysql",
    "mariadb": "mariadb+pymysql",
    "postgresql": "postgresql+psycopg2",
    "mssql": "mssql+pyodbc",
}

# 同步驱动的可选依赖安装提示
_SYNC_DRIVER_HINTS = {
    "postgresql": "pip install psycopg2-binary",
    "mssql": "pip install pyodbc",
}


def get_sync_database_url(url: str = None) -> str:
    """把应用使用的异步数据库 URL 转换成同步驱动 URL

    Alembic 迁移在同步上下文中运行，直接使用 ``mysql+aiomysql`` 这类异步 URL
    会抛出 ``MissingGreenlet``。此函数负责驱动替换，其余部分（主机、账号、
    密码、库名、查询参数）原样保留，避免手工拼接字符串导致特殊字符转义错误。

    Args:
        url: 待转换的 URL，不传则使用 :func:`get_database_url` 的解析结果

    Returns:
        str: 同步驱动 URL

    Raises:
        ValueError: URL 无法解析，或后端没有已知的同步驱动

    使用示例:
        >>> get_sync_database_url("sqlite+aiosqlite:///./data/database.db")
        'sqlite:///./data/database.db'
        >>> get_sync_database_url("mysql+aiomysql://root:pwd@db:3306/app")
        'mysql+pymysql://root:pwd@db:3306/app'
    """
    # 延迟导入：仅迁移场景需要，避免 config 模块在极简环境下的导入成本
    from sqlalchemy.engine import make_url

    async_url = url or get_database_url()

    try:
        parsed = make_url(async_url)
    except Exception as exc:  # noqa: BLE001 - 统一转换为可读的配置错误
        raise ValueError(f"数据库 URL 无法解析: {async_url}") from exc

    backend = parsed.get_backend_name()
    sync_driver = _SYNC_DRIVER_MAP.get(backend)
    if sync_driver is None:
        raise ValueError(
            f"数据库类型 {backend} 没有配置同步驱动，无法执行 Alembic 迁移。"
            f"请在 config/database.py 的 _SYNC_DRIVER_MAP 中补充映射。"
        )

    if parsed.drivername == sync_driver:
        return async_url

    if backend == "sqlite":
        # SQLite 的 :memory: 与相对路径会被 make_url 重新编码（:memory: -> %3Amemory%3A），
        # 直接替换驱动前缀可以完整保留原始路径写法。
        prefix = f"{parsed.drivername}://"
        if async_url.startswith(prefix):
            return "sqlite://" + async_url[len(prefix):]

    try:
        return parsed.set(drivername=sync_driver).render_as_string(hide_password=False)
    except ModuleNotFoundError as exc:
        hint = _SYNC_DRIVER_HINTS.get(backend, f"pip install {sync_driver}")
        raise ValueError(
            f"执行数据库迁移需要同步驱动 {sync_driver}，请先安装：{hint}"
        ) from exc


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
