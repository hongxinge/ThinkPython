"""
ThinkPython 数据库迁移工具 - Alembic 配置

本文件是 Alembic 数据库迁移工具的配置文件，用于管理和执行数据库结构的变更。
Alembic 是 SQLAlchemy 官方的数据库迁移工具，支持：
- 自动根据模型变更生成迁移脚本
- 版本化的数据库结构管理
- 安全的向前/向后迁移（升级/降级）

工作原理：
1. Alembic 读取 SQLAlchemy 的 Base.metadata 获取所有模型定义
2. 对比模型定义与数据库当前状态，生成迁移脚本
3. 执行迁移脚本，应用变更到数据库

使用方式:
    # 1. 初始化 Alembic（仅首次需要）
    alembic init alembic
    
    # 2. 自动生成迁移脚本（根据模型变更）
    alembic revision --autogenerate -m "添加用户表"
    
    # 3. 执行迁移（应用变更到数据库）
    alembic upgrade head
    
    # 4. 回滚迁移（撤销最近一次变更）
    alembic downgrade -1

注意事项:
- 此配置文件使用在线模式（online mode），直接连接数据库执行迁移
- 离线模式（offline mode）生成纯 SQL 脚本，不直接连接数据库，暂不支持
- 修改模型后务必先生成迁移脚本，再执行迁移，切勿直接修改数据库结构
"""
import os
from pathlib import Path
from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig

from config.database import get_database_url, DATABASE_CONFIG

# Alembic Config 对象，从 alembic.ini 文件中加载配置
config = context.config

# 设置数据库连接 URL，从 config/database.py 中读取
# 这样可以保持与应用的数据库配置一致
config.set_main_option("sqlalchemy.url", get_database_url())

# 加载 Alembic 日志配置（如果 alembic.ini 存在）
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def run_migrations_online():
    """在线模式运行数据库迁移
    
    在线模式直接连接数据库并执行迁移操作。
    这是最常用的迁移模式，适用于开发和生产环境。
    
    迁移流程：
    1. 创建数据库引擎（使用 NullPool 避免连接池干扰迁移过程）
    2. 连接到数据库
    3. 配置 Alembic 上下文
    4. 在事务中执行迁移操作
    
    注意：使用 NullPool 而非连接池，因为迁移过程是短期的，
    不需要复用连接，且可以避免连接状态冲突。
    """
    # 从 Alembic 配置中创建数据库引擎
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),  # 获取 alembic.ini 中的配置
        prefix="sqlalchemy.",  # 配置键的前缀
        poolclass=pool.NullPool,  # 不使用连接池，每次操作创建新连接
    )
    
    # 连接数据库并执行迁移
    with connectable.connect() as connection:
        # 配置 Alembic 迁移上下文
        context.configure(
            connection=connection,
            target_metadata=None,  # TODO: 设置为目标模型的元数据，用于自动检测变更
            # target_metadata=Base.metadata  # 取消注释并导入 Base 以启用自动检测
        )
        
        # 在事务中执行迁移，确保要么全部成功，要么全部回滚
        with context.begin_transaction():
            context.run_migrations()


# 判断 Alembic 运行模式
if context.is_offline_mode():
    # 离线模式：生成 SQL 脚本而不直接连接数据库
    # 通常用于 DBA 审核或无法直接连接数据库的场景
    raise Exception("离线模式暂不支持，请使用在线模式运行迁移")
else:
    # 在线模式：直接连接数据库执行迁移
    run_migrations_online()
