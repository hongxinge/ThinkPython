"""
数据库迁移工具
使用 Alembic 进行数据库迁移
"""
import os
from pathlib import Path
from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig

from config.database import get_database_url, DATABASE_CONFIG

# Alembic Config 对象
config = context.config

# 数据库URL
config.set_main_option("sqlalchemy.url", get_database_url())

# 日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def run_migrations_online():
    """在线模式运行迁移"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=None,
        )
        
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    raise Exception("离线模式暂不支持")
else:
    run_migrations_online()
