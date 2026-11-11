"""数据库支持矩阵回归：连接串正确性、跨方言 DDL、可选真实连接

设计约束：
- 默认测试**不依赖任何外部数据库**，离线即可跑完（方言 DDL 编译 + URL 解析）；
- 真实连接测试由环境变量 ``TP_TEST_DATABASE_URL`` 显式启用，未提供则跳过，
  不引入 Docker / 容器编排，符合项目的裸机部署约定；
- 集成测试只做连通性与 ``SELECT 1``，不建表不写数据，避免污染外部库。
"""
import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.dialects import mssql, mysql, postgresql, sqlite
from sqlalchemy.engine import make_url
from sqlalchemy.schema import CreateTable

from config.database import default_db_port, get_database_url, get_sync_database_url


def _config(db_type: str, password: str) -> dict:
    return {
        "type": db_type,
        "username": "u#x",
        "password": password,
        "host": "127.0.0.1",
        "port": default_db_port(db_type),
        "database": "demo",
        "charset": "utf8mb4",
    }


# ==================================================================
# 一、P0：密码特殊字符与默认端口
# ==================================================================

@pytest.mark.parametrize("db_type", ["mysql", "postgresql", "mssql"])
@pytest.mark.parametrize("password", ["pass", "P@ss/2026", "a:b#c%d", "中文密码"])
def test_password_special_chars_round_trip(db_type, password):
    """含 @ / : / # / % / 中文的密码必须原样还原，且迁移 URL 同样不丢字符"""
    url = get_database_url(_config(db_type, password))
    assert make_url(url).password == password, url

    sync_url = get_sync_database_url(url)
    assert make_url(sync_url).password == password, sync_url
    # 用户名含 # 也要能还原
    assert make_url(sync_url).username == "u#x"


@pytest.mark.parametrize(
    "db_type, expected",
    [("mysql", 3306), ("mariadb", 3306), ("postgresql", 5432),
     ("mssql", 1433), ("sqlite", 3306), ("oracle", 3306)],
)
def test_default_port_follows_db_type(db_type, expected):
    """切库后不再需要手工改端口；未知类型回落 3306"""
    assert default_db_port(db_type) == expected


def test_sqlite_paths_are_not_percent_encoded():
    """SQLite 不能走 URL.create：盘符冒号与 :memory: 被编码会导致连不上"""
    for path in [":memory:", "G:/ThinkPython/data/database.db", "./data/database.db"]:
        url = get_database_url({"type": "sqlite", "sqlite_path": path})
        assert "%3A" not in url, url
        assert path in url, url


@pytest.mark.parametrize(
    "async_driver, sync_driver",
    [
        ("mysql+aiomysql", "mysql+pymysql"),
        ("postgresql+asyncpg", "postgresql+psycopg2"),
        ("mssql+aioodbc", "mssql+pyodbc"),
        ("sqlite+aiosqlite", "sqlite"),
    ],
)
def test_sync_driver_mapping(async_driver, sync_driver):
    """Alembic 迁移的同步驱动映射覆盖四种方言"""
    url = f"{async_driver}://u:p@127.0.0.1:1/demo"
    converted = get_sync_database_url(url)
    assert make_url(converted).drivername == sync_driver, converted


# ==================================================================
# 二、P2：离线跨方言 DDL 兼容性（始终运行，不需要真实数据库）
# ==================================================================

@pytest.mark.parametrize(
    "dialect_cls",
    [sqlite.dialect, mysql.dialect, postgresql.dialect, mssql.dialect],
    ids=["sqlite", "mysql", "postgresql", "mssql"],
)
def test_user_table_ddl_compiles_on_all_dialects(dialect_cls):
    """核心表结构能在四种方言下编译出 DDL，不依赖方言专属类型"""
    from app.common.model.user_model import User

    ddl = str(CreateTable(User.__table__).compile(dialect=dialect_cls()))
    for column in ("username", "email", "token_version", "role", "status"):
        assert column in ddl, (dialect_cls, column)


# ==================================================================
# 三、P2：可选真实连接集成测试（显式启用，不做 DDL）
# ==================================================================

@pytest.mark.integration
def test_external_database_connection():
    """提供 TP_TEST_DATABASE_URL 时验证「异步应用链路 + 同步迁移链路」都能连通

    例：
        TP_TEST_DATABASE_URL=mysql+aiomysql://user:pwd@127.0.0.1:3306/demo \\
            pytest tests/test_database_matrix.py -m integration
    """
    url = os.getenv("TP_TEST_DATABASE_URL")
    if not url:
        pytest.skip("未设置 TP_TEST_DATABASE_URL，跳过真实数据库连接测试")

    import asyncio

    from sqlalchemy.ext.asyncio import create_async_engine

    async def check_async():
        engine = create_async_engine(url, pool_pre_ping=True)
        try:
            async with engine.connect() as conn:
                assert (await conn.execute(text("SELECT 1"))).scalar() == 1
        finally:
            await engine.dispose()

    asyncio.run(check_async())

    sync_engine = create_engine(get_sync_database_url(url), pool_pre_ping=True)
    try:
        with sync_engine.connect() as conn:
            assert conn.execute(text("SELECT 1")).scalar() == 1
    finally:
        sync_engine.dispose()
