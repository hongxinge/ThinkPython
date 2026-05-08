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
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from config.database import DATABASE_CONFIG, get_database_url

# 全局数据库引擎实例，负责管理连接池和执行 SQL 语句
engine = None

# 全局异步会话工厂，用于创建 AsyncSession 实例
async_session = None

# SQLAlchemy 声明式基类，所有 ORM 模型都应继承此基类
# 通过继承 Base，模型类会自动注册到 Base.metadata 中，方便统一创建表
Base = declarative_base()


async def init_database():
    """初始化数据库连接
    
    根据 config/database.py 中的配置创建异步数据库引擎和会话工厂。
    仅在 DATABASE_CONFIG["enabled"] 为 True 时执行初始化。
    
    初始化过程：
    1. 根据配置生成数据库连接 URL
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
    
    # 从配置中获取数据库连接 URL
    db_url = get_database_url()
    
    # 创建异步数据库引擎
    # create_async_engine 是 SQLAlchemy 提供的异步版本引擎创建函数
    engine = create_async_engine(
        db_url,
        pool_size=DATABASE_CONFIG["pool_size"],  # 连接池基础大小
        max_overflow=DATABASE_CONFIG["max_overflow"],  # 连接池最大溢出连接数
        pool_recycle=DATABASE_CONFIG["pool_recycle"],  # 连接回收时间（秒）
        pool_pre_ping=DATABASE_CONFIG["pool_pre_ping"],  # 使用前检测连接有效性
        echo=DATABASE_CONFIG["echo"],  # 是否打印 SQL 语句
    )
    
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
