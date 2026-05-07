"""
数据库连接管理
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from config.database import DATABASE_CONFIG, get_database_url

engine = None
async_session = None
Base = declarative_base()


async def init_database():
    """初始化数据库连接"""
    global engine, async_session
    
    if not DATABASE_CONFIG["enabled"]:
        return
    
    db_url = get_database_url()
    engine = create_async_engine(
        db_url,
        pool_size=DATABASE_CONFIG["pool_size"],
        max_overflow=DATABASE_CONFIG["max_overflow"],
        pool_recycle=DATABASE_CONFIG["pool_recycle"],
        pool_pre_ping=DATABASE_CONFIG["pool_pre_ping"],
        echo=DATABASE_CONFIG["echo"],
    )
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )


async def close_database():
    """关闭数据库连接"""
    global engine
    if engine:
        await engine.dispose()


async def get_db() -> AsyncSession:
    """获取数据库会话 (用于依赖注入)"""
    if async_session is None:
        raise Exception("数据库连接未初始化")
    
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
