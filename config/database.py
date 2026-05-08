"""
数据库配置文件
支持多种数据库类型: mysql, postgresql, sqlite, mssql
"""
import os
from pathlib import Path


DATABASE_CONFIG = {
    # 数据库类型: mysql, postgresql, sqlite, mssql
    "type": os.getenv("DB_TYPE", "sqlite"),
    
    # 是否启用数据库
    "enabled": os.getenv("DB_ENABLED", "True").lower() == "true",
    
    # MySQL/PostgreSQL/MSSQL 配置
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "database": os.getenv("DB_NAME", "thinkpython"),
    "username": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    
    # 连接池配置
    "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
    "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
    "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "3600")),
    "pool_pre_ping": os.getenv("DB_POOL_PRE_PING", "True").lower() == "true",
    
    # SQLite 配置 (当 type=sqlite 时使用)
    "sqlite_path": os.getenv("DB_SQLITE_PATH", str(Path(__file__).resolve().parent.parent / "data" / "database.db")),
    
    # 编码
    "charset": os.getenv("DB_CHARSET", "utf8mb4"),
    
    # 其他配置
    "echo": os.getenv("DB_ECHO", "False").lower() == "true",  # 是否打印SQL语句
}


def get_database_url(config: dict = None) -> str:
    """获取数据库连接URL"""
    cfg = config or DATABASE_CONFIG
    db_type = cfg["type"]
    
    if db_type == "sqlite":
        return f"sqlite:///{cfg['sqlite_path']}"
    elif db_type == "mysql":
        return f"mysql+aiomysql://{cfg['username']}:{cfg['password']}@{cfg['host']}:{cfg['port']}/{cfg['database']}?charset={cfg['charset']}"
    elif db_type == "postgresql":
        return f"postgresql+asyncpg://{cfg['username']}:{cfg['password']}@{cfg['host']}:{cfg['port']}/{cfg['database']}"
    elif db_type == "mssql":
        return f"mssql+aioodbc://{cfg['username']}:{cfg['password']}@{cfg['host']}:{cfg['port']}/{cfg['database']}?driver=ODBC+Driver+17+for+SQL+Server"
    else:
        raise ValueError(f"Unsupported database type: {db_type}")
