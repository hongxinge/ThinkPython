"""
ThinkPython 数据库连接管理

本模块负责管理 SQLAlchemy 异步数据库连接的生命周期，包括：
- 初始化数据库引擎和会话工厂
- 提供依赖注入接口，用于 FastAPI 路由中获取数据库会话
- 优雅地关闭数据库连接

核心组件：
- engine: SQLAlchemy 异步引擎，负责创建和管理数据库连接池
- async_session: 异步会话工厂，用于创建数据库会话（Session）
- Base: SQLAlchemy 声明式基类，所有 ORM 模型都继承自此基类

使用示例:
    # 在应用启动时初始化
    from core.database import init_database, get_db
    
    await init_database()
    
    # 在 FastAPI 路由中使用依赖注入
    from fastapi import Depends
    from sqlalchemy.ext.asyncio import AsyncSession
    
    @router.get("/users")
    async def get_users(db: AsyncSession = Depends(get_db)):
        # db 是一个已经打开的数据库会话，请求结束后自动提交/回滚
        result = await db.execute(select(User))
        return result.scalars().all()
"""
import time
from typing import AsyncGenerator, Optional

from loguru import logger
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

from config.database import DATABASE_CONFIG, DATABASE_URL, DB_SLOW_QUERY_MS, get_database_url
from core.context import get_request_id

# 全局数据库引擎实例，负责管理连接池和执行 SQL 语句
engine = None

# 全局异步会话工厂，用于创建 AsyncSession 实例
async_session = None

# SQLAlchemy 声明式基类，所有 ORM 模型都应继承此基类
# 通过继承 Base，模型类会自动注册到 Base.metadata 中，方便统一创建表
Base = declarative_base()


def _enable_sqlite_pragmas(engine) -> None:
    """为 SQLite 文件数据库设置必要的 PRAGMA

    这三项是 SQLite 上生产可用的前提，默认值都不合适：

    ======================  ==========  ========================================
    PRAGMA                  默认值      开启后
    ======================  ==========  ========================================
    journal_mode            delete      WAL：读写不互相阻塞，并发请求不会整库排队
    synchronous             FULL        NORMAL：配合 WAL 仍能保证崩溃一致性，写入快数倍
    foreign_keys            OFF         ON：默认竟然不校验外键，数据一致性全靠应用层
    busy_timeout            0           5000ms：并发写入时等待而非立即报 database is locked
    ======================  ==========  ========================================

    内存库不调用此函数（``:memory:`` 不支持 WAL）。
    """
    from sqlalchemy import event

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):  # noqa: ANN001, ARG001
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
        finally:
            cursor.close()


def install_slow_query_logging(engine, threshold_ms: Optional[int] = None, sink=None) -> None:
    """为引擎注册慢 SQL 监听（SQLAlchemy 事件，无侵入）

    在 ``before_cursor_execute`` / ``after_cursor_execute`` 之间计时，超过阈值时
    以 WARNING 级别记录耗时、request_id 与截断后的 SQL。记录语句而不记录参数，
    避免把密码、手机号、Token 等敏感值写进日志。

    Args:
        engine: SQLAlchemy 引擎（同步或异步均可，事件挂在 ``sync_engine`` 上）
        threshold_ms: 阈值（毫秒）；不传则读 ``DB_SLOW_QUERY_MS``，<= 0 表示关闭
        sink: 可注入的日志接收函数，便于单元测试；默认 ``logger.warning``

    说明：计时栈存在 ``Connection.info`` 里，与单个 Connection 生命周期绑定，
    连接池复用 DBAPI 连接时不会把上一请求的计时带过来。
    """
    threshold = DB_SLOW_QUERY_MS if threshold_ms is None else threshold_ms
    if threshold <= 0:
        return
    emit = sink or logger.warning
    key = "_tp_sql_start"
    # 异步引擎有 sync_engine；同步引擎（测试/脚本）直接用自身
    target = getattr(engine, "sync_engine", engine)

    @event.listens_for(target, "before_cursor_execute")
    def _before(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001, ARG001
        conn.info.setdefault(key, []).append(time.perf_counter())

    @event.listens_for(target, "after_cursor_execute")
    def _after(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001, ARG001
        starts = conn.info.get(key)
        if not starts:
            return
        elapsed_ms = (time.perf_counter() - starts.pop()) * 1000
        if elapsed_ms < threshold:
            return
        sql = " ".join(statement.split())[:300]
        emit(
            f"slow_sql | {elapsed_ms:.1f}ms | "
            f"request_id={get_request_id() or '-'} | {sql}"
        )


async def init_database():
    """初始化数据库连接
    
    根据 config/database.py 中的配置创建异步数据库引擎和会话工厂。
    仅在 DATABASE_CONFIG["enabled"] 为 True 时执行初始化。
    
    初始化过程：
    1. 根据配置生成数据库连接 URL（支持 DATABASE_URL 一行配置）
    2. 创建异步引擎（含连接池配置）
    3. 创建异步会话工厂
    
    使用示例:
        from core.database import init_database
        
        # 应用启动时调用
        await init_database()
    """
    global engine, async_session
    
    # 如果数据库功能未启用，直接返回
    if not DATABASE_CONFIG["enabled"]:
        return
    
    # 从配置中获取数据库连接 URL（优先使用 DATABASE_URL）
    db_url = get_database_url()
    
    # 判断是否为 SQLite，SQLite 不需要连接池配置
    is_sqlite = "sqlite" in db_url
    
    if is_sqlite:
        # SQLite 是文件数据库，不需要连接池复用
        engine = create_async_engine(
            db_url,
            echo=DATABASE_CONFIG["echo"],
        )
        # 内存库不支持 WAL（每次连接是独立库），文件库才启用
        if ":memory:" not in db_url:
            _enable_sqlite_pragmas(engine)
    else:
        # MySQL / PostgreSQL / MSSQL 使用连接池
        # create_async_engine 是 SQLAlchemy 提供的异步版本引擎创建函数
        engine = create_async_engine(
            db_url,
            pool_size=DATABASE_CONFIG["pool_size"],  # 连接池基础大小
            max_overflow=DATABASE_CONFIG["max_overflow"],  # 连接池最大溢出连接数
            pool_recycle=DATABASE_CONFIG["pool_recycle"],  # 连接回收时间（秒）
            pool_pre_ping=DATABASE_CONFIG["pool_pre_ping"],  # 使用前检测连接有效性
            echo=DATABASE_CONFIG["echo"],  # 是否打印 SQL 语句
        )
    
    # 慢 SQL 监听与方言无关，SQLite / MySQL / PostgreSQL / MSSQL 统一生效
    install_slow_query_logging(engine)

    # 创建异步会话工厂
    # async_sessionmaker 是会话的工厂类，每次调用都会创建新的 AsyncSession
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    # expire_on_commit=False: 提交后不使对象属性过期，避免后续访问时再次查询数据库


async def close_database():
    """关闭数据库连接
    
    释放引擎持有的所有数据库连接，通常在应用关闭时调用。
    
    使用示例:
        from core.database import close_database
        
        # 应用关闭时调用
        await close_database()
    """
    global engine
    if engine:
        # dispose() 会关闭连接池中的所有连接
        await engine.dispose()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话（用于 FastAPI 依赖注入）
    
    这是一个异步生成器函数，FastAPI 原生支持异步生成器作为依赖项。
    它会自动管理会话的生命周期：
    - 请求开始时创建新会话
    - 请求成功时自动提交
    - 请求异常时自动回滚
    - 请求结束时自动关闭会话
    
    使用方式:
        from fastapi import Depends
        from sqlalchemy.ext.asyncio import AsyncSession
        
        @router.get("/users/{user_id}")
        async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
            # 直接使用 db 进行数据库操作
            user = await db.get(User, user_id)
            return user
    
    Yields:
        AsyncSession: 一个已打开的数据库会话实例
        
    Raises:
        Exception: 当数据库连接未初始化时抛出
    """
    if async_session is None:
        # 如果尚未初始化，尝试自动初始化（支持测试环境和独立调用）
        await init_database()
        if async_session is None:
            raise Exception("数据库连接未初始化，请检查数据库配置")
    
    # 从会话工厂创建一个新会话
    async with async_session() as session:
        try:
            # 生成会话，供依赖注入使用
            yield session
            # 如果请求处理过程中没有异常，则提交事务
            await session.commit()
        except Exception:
            # 如果发生异常，回滚事务，防止数据不一致
            await session.rollback()
            raise
