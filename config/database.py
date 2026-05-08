"""
ThinkPython 数据库配置文件

本文件负责配置和管理数据库连接参数，支持多种数据库类型：
- MySQL（通过 aiomysql 异步驱动）
- PostgreSQL（通过 asyncpg 异步驱动）
- SQLite（内置，无需额外安装驱动）
- SQL Server / MSSQL（通过 aioodbc 异步驱动）

所有配置项均支持通过 .env 环境变量覆盖。

使用示例：
    from config.database import DATABASE_CONFIG, get_database_url
    
    # 获取数据库 URL
    db_url = get_database_url()  # 返回: "sqlite:///G:/ThinkPython/data/database.db"
    
    # 直接使用配置字典
    pool_size = DATABASE_CONFIG["pool_size"]
"""
import os
from pathlib import Path


# 数据库配置字典，集中管理所有数据库连接参数
DATABASE_CONFIG = {
    # 数据库类型，支持: mysql, postgresql, sqlite, mssql
    # 默认使用 sqlite（零配置，适合开发和测试）
    "type": os.getenv("DB_TYPE", "sqlite"),
    
    # 是否启用数据库连接，设为 False 时可关闭数据库功能
    "enabled": os.getenv("DB_ENABLED", "True").lower() == "true",
    
    # MySQL / PostgreSQL / MSSQL 的连接参数
    # 当 type=sqlite 时，这些参数不会被使用
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "database": os.getenv("DB_NAME", "thinkpython"),
    "username": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    
    # 数据库连接池配置
    # 连接池可以复用数据库连接，避免频繁创建/销毁连接带来的性能损耗
    "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),  # 连接池基础大小（保持的空闲连接数）
    "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),  # 允许超出 pool_size 的最大连接数
    "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "3600")),  # 连接回收时间（秒），防止连接过期
    "pool_pre_ping": os.getenv("DB_POOL_PRE_PING", "True").lower() == "true",  # 使用前检测连接是否有效
    
    # SQLite 专属配置
    # 当 type=sqlite 时使用此路径作为数据库文件
    # 默认存放在项目根目录的 data/database.db
    "sqlite_path": os.getenv("DB_SQLITE_PATH", str(Path(__file__).resolve().parent.parent / "data" / "database.db")),
    
    # 数据库字符编码，utf8mb4 支持存储 Emoji 等特殊字符
    "charset": os.getenv("DB_CHARSET", "utf8mb4"),
    
    # 其他配置
    "echo": os.getenv("DB_ECHO", "False").lower() == "true",  # 是否打印 SQL 语句到控制台（开发调试用）
}


def get_database_url(config: dict = None) -> str:
    """根据当前数据库配置生成 SQLAlchemy 连接 URL
    
    不同数据库类型对应不同的异步驱动和 URL 格式：
    - SQLite: sqlite:///path/to/database.db
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
        'sqlite:///G:/ThinkPython/data/database.db'
        
        >>> get_database_url({"type": "mysql", "username": "root", "password": "123",
        ...                   "host": "localhost", "port": 3306, "database": "test",
        ...                   "charset": "utf8mb4"})
        'mysql+aiomysql://root:123@localhost:3306/test?charset=utf8mb4'
    """
    cfg = config or DATABASE_CONFIG
    db_type = cfg["type"]
    
    if db_type == "sqlite":
        # SQLite 使用本地文件路径，三个斜杠 /// 表示绝对路径
        return f"sqlite:///{cfg['sqlite_path']}"
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
