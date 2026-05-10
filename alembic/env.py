"""
ThinkPython Alembic 迁移环境配置

本文件是 Alembic 数据库迁移的核心配置文件，负责：
1. 加载数据库连接配置
2. 导入所有模型元数据
3. 执行自动迁移检测

工作原理：
1. Alembic 读取 SQLAlchemy 的 Base.metadata 获取所有模型定义
2. 对比模型定义与数据库当前状态，生成迁移脚本
3. 执行迁移脚本，应用变更到数据库

使用方式:
    # 1. 自动生成迁移脚本（根据模型变更）
    python think.py db-migrate --auto -m "添加用户表"
    
    # 2. 执行迁移（应用变更到数据库）
    python think.py db-migrate
    
    # 3. 回滚迁移（撤销最近一次变更）
    python think.py db-migrate --downgrade
    
    # 4. 查看迁移历史
    python think.py db-migrate --history

注意事项:
- 修改模型后务必先生成迁移脚本，再执行迁移
- 切勿直接修改数据库结构，应通过迁移管理
- 生产环境执行迁移前建议备份数据库
"""
import os
import sys
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# 添加项目根目录到 Python 路径
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# 从 ThinkPython 配置中读取数据库连接
from config.database import get_database_url, DATABASE_CONFIG

# Alembic Config 对象，从 alembic.ini 文件中加载配置
config = context.config

# 设置数据库连接 URL，从 ThinkPython 配置中读取
config.set_main_option("sqlalchemy.url", get_database_url())

# 加载 Alembic 日志配置（如果 alembic.ini 存在）
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def import_all_models():
    """导入所有模型，使 Alembic 能够检测到模型变更
    
    此函数会扫描 app/ 目录下所有 model/ 子目录，
    并导入其中的所有模型文件。
    """
    from core.database import Base
    
    app_dir = BASE_DIR / "app"
    if not app_dir.exists():
        return
    
    # 递归扫描所有 model 目录
    for model_dir in app_dir.rglob("model"):
        if not model_dir.is_dir():
            continue
        
        # 导入该目录下的所有 Python 文件（除了 __init__.py）
        for model_file in model_dir.glob("*.py"):
            if model_file.name.startswith("_"):
                continue
            
            # 构造模块路径
            relative_path = model_file.relative_to(BASE_DIR)
            module_name = str(relative_path.with_suffix("")).replace(os.sep, ".")
            
            try:
                __import__(module_name)
            except Exception as e:
                # 忽略导入失败的模型（可能是依赖未安装）
                pass
    
    # 返回 Base.metadata 供 Alembic 使用
    from core.database import Base
    return Base.metadata


# 获取目标元数据
target_metadata = import_all_models()


def run_migrations_offline() -> None:
    """离线模式运行迁移
    
    离线模式生成 SQL 脚本而不直接连接数据库。
    通常用于 DBA 审核或无法直接连接数据库的场景。
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式运行迁移
    
    在线模式直接连接数据库并执行迁移操作。
    这是最常用的迁移模式，适用于开发和生产环境。
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


# 判断 Alembic 运行模式
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
