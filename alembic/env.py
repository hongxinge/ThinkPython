"""ThinkPython Alembic 迁移环境配置

职责：
1. 从应用配置（DATABASE_URL / DB_TYPE）解析数据库连接，并转换为**同步驱动** URL；
2. 导入 app/ 下全部模型，向 Alembic 提供完整的 Base.metadata；
3. 按 Alembic 的离线 / 在线模式执行迁移。

为什么必须是同步驱动：
    Alembic 的迁移脚本在同步上下文中运行。若 url 里带 ``+aiomysql`` / ``+aiosqlite``
    等异步驱动，SQLAlchemy 会抛出 ``MissingGreenlet``。转换逻辑集中在
    ``config.database.get_sync_database_url()``，避免各处手工拼字符串。

为什么不再静默忽略模型导入失败：
    模型导入失败意味着 Base.metadata 缺表，自动生成的迁移会**漏表**或把已有表
    判定为"需要删除"。默认直接失败并给出模块名；确需跳过时设置环境变量
    ``ALEMBIC_ALLOW_MODEL_IMPORT_ERRORS=true``。

使用方式（统一走 CLI，自动携带项目配置）::

    python think.py db-migrate --auto -m "添加订单表"   # 生成迁移脚本
    python think.py db-migrate --upgrade               # 应用迁移
    python think.py db-migrate --downgrade             # 回滚一步
    python think.py db-migrate --history               # 查看历史
"""
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# 保证项目根目录可导入（alembic.ini 的 prepend_sys_path 之外的二次保险）
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.database import get_sync_database_url  # noqa: E402

# Alembic 配置对象
config = context.config

# 写入同步 URL。
# 注意：configparser 会把 "%" 当作插值符号，密码中含 % 时必须转义，
# 否则 set_main_option 会直接抛 InterpolationSyntaxError。
config.set_main_option("sqlalchemy.url", get_sync_database_url().replace("%", "%%"))

# 加载日志配置；disable_existing_loggers=False 避免 Alembic 关掉应用自己的 logger
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)


def import_all_models():
    """导入 app/ 下所有模型模块，返回 Base.metadata

    Alembic 只能看到"已被导入"的模型类。CLI 进程默认不加载任何模型，
    因此这里主动扫描 ``app/**/model/`` 目录：
    1. 先导入 model 包本身（执行其 ``__init__.py``，兼容 re-export 写法）；
    2. 再导入包内所有非下划线开头的模块。

    Returns:
        MetaData: SQLAlchemy 元数据对象

    Raises:
        RuntimeError: 存在模型导入失败且未开启宽松模式
    """
    from core.database import Base

    app_dir = BASE_DIR / "app"
    if not app_dir.exists():
        return Base.metadata

    allow_errors = os.getenv("ALEMBIC_ALLOW_MODEL_IMPORT_ERRORS", "false").lower() == "true"
    failed = []

    def _import_module_name(module_name: str) -> None:
        try:
            __import__(module_name)
        except Exception as exc:  # noqa: BLE001 - 需要一次性收集全部失败项
            failed.append((module_name, exc))

    for model_dir in sorted(app_dir.rglob("model")):
        if not model_dir.is_dir():
            continue

        # 1) 导入 model 包自身
        package_name = str(model_dir.relative_to(BASE_DIR)).replace(os.sep, ".")
        _import_module_name(package_name)

        # 2) 导入包内模块
        for model_file in sorted(model_dir.glob("*.py")):
            if model_file.name.startswith("_"):
                continue
            module_name = str(model_file.relative_to(BASE_DIR).with_suffix("")).replace(os.sep, ".")
            _import_module_name(module_name)

    if failed:
        details = "\n".join(f"  - {name}: {exc.__class__.__name__}: {exc}" for name, exc in failed)
        if allow_errors:
            print(
                f"[alembic] 警告：{len(failed)} 个模型导入失败，迁移可能漏表：\n{details}",
                file=sys.stderr,
            )
        else:
            raise RuntimeError(
                f"模型导入失败，无法安全生成迁移（共 {len(failed)} 个）：\n{details}\n"
                "请修复导入错误；若确认可忽略，设置 ALEMBIC_ALLOW_MODEL_IMPORT_ERRORS=true"
            )

    return Base.metadata


# 目标元数据
target_metadata = import_all_models()


def _configure_context(**kwargs) -> None:
    """统一的 context.configure 参数

    参数说明：
    - compare_type：字段类型变化也纳入自动检测（默认只在 Alembic 1.12+ 开启）
    - render_as_batch：SQLite 不支持 ALTER COLUMN，用 batch 模式重建表，
      否则后续给已有表改字段会直接报 "near ALTER: syntax error"
    """
    context.configure(
        target_metadata=target_metadata,
        compare_type=True,
        **kwargs,
    )


def run_migrations_offline() -> None:
    """离线模式：只生成 SQL，不连接数据库（供 DBA 审核）"""
    _configure_context(
        url=config.get_main_option("sqlalchemy.url"),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式：连接数据库并执行迁移"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        _configure_context(
            connection=connection,
            render_as_batch=connection.dialect.name == "sqlite",
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
