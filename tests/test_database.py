"""ThinkPython 数据库操作测试"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import core.database as db_module
from core.database import Base, init_database, close_database, get_db


from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

class TestModelForDB(Base):
    __tablename__ = "test_models_db"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100))


class TestDatabaseConfig:
    def test_database_config_type(self):
        from config.database import DATABASE_CONFIG
        assert "type" in DATABASE_CONFIG

    def test_database_config_enabled(self):
        from config.database import DATABASE_CONFIG
        assert "enabled" in DATABASE_CONFIG
        assert isinstance(DATABASE_CONFIG["enabled"], bool)

    def test_database_config_pool_size(self):
        from config.database import DATABASE_CONFIG
        assert "pool_size" in DATABASE_CONFIG
        assert DATABASE_CONFIG["pool_size"] > 0

    def test_database_config_charset(self):
        from config.database import DATABASE_CONFIG
        assert "charset" in DATABASE_CONFIG

    def test_get_database_url_sqlite(self):
        from config.database import get_database_url
        config = {"type": "sqlite", "sqlite_path": "/tmp/test.db"}
        url = get_database_url(config)
        assert "sqlite" in url

    def test_get_database_url_mysql(self):
        from config.database import get_database_url
        config = {
            "type": "mysql",
            "username": "root",
            "password": "pass",
            "host": "localhost",
            "port": 3306,
            "database": "test",
            "charset": "utf8mb4",
        }
        url = get_database_url(config)
        assert "mysql+aiomysql" in url
        assert "root:pass@localhost:3306/test" in url

    def test_get_database_url_postgresql(self):
        from config.database import get_database_url
        config = {
            "type": "postgresql",
            "username": "postgres",
            "password": "pass",
            "host": "localhost",
            "port": 5432,
            "database": "test",
        }
        url = get_database_url(config)
        assert "postgresql+asyncpg" in url

    def test_get_database_url_unsupported(self):
        from config.database import get_database_url
        config = {"type": "oracle"}
        with pytest.raises(ValueError, match="Unsupported database type"):
            get_database_url(config)


class TestDatabaseConnection:

    @pytest.fixture
    def db_engine_and_session(self):
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        import asyncio
        async def setup():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

        async def teardown():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()

        async def run_setup_and_return_session():
            await setup()
            session = async_session()
            return session, engine

        session, eng = asyncio.get_event_loop().run_until_complete(run_setup_and_return_session())
        yield session, eng
        async def cleanup():
            await session.close()
            await teardown()
        asyncio.get_event_loop().run_until_complete(cleanup())

    @pytest.mark.asyncio
    async def test_create_model(self, db_engine_and_session):
        session, _ = db_engine_and_session
        model = TestModelForDB(name="test", email="test@example.com")
        session.add(model)
        await session.commit()
        assert model.id is not None

    @pytest.mark.asyncio
    async def test_query_model(self, db_engine_and_session):
        from sqlalchemy import select
        session, _ = db_engine_and_session
        model = TestModelForDB(name="query_test", email="query@example.com")
        session.add(model)
        await session.commit()
        result = await session.execute(select(TestModelForDB).where(TestModelForDB.name == "query_test"))
        found = result.scalars().first()
        assert found is not None
        assert found.name == "query_test"

    @pytest.mark.asyncio
    async def test_update_model(self, db_engine_and_session):
        from sqlalchemy import select
        session, _ = db_engine_and_session
        model = TestModelForDB(name="update_test", email="old@example.com")
        session.add(model)
        await session.commit()
        result = await session.execute(select(TestModelForDB).where(TestModelForDB.name == "update_test"))
        found = result.scalars().first()
        found.email = "new@example.com"
        await session.commit()
        result = await session.execute(select(TestModelForDB).where(TestModelForDB.id == found.id))
        updated = result.scalars().first()
        assert updated.email == "new@example.com"

    @pytest.mark.asyncio
    async def test_delete_model(self, db_engine_and_session):
        from sqlalchemy import select
        session, _ = db_engine_and_session
        model = TestModelForDB(name="delete_test", email="delete@example.com")
        session.add(model)
        await session.commit()
        await session.delete(model)
        await session.commit()
        result = await session.execute(select(TestModelForDB).where(TestModelForDB.name == "delete_test"))
        found = result.scalars().first()
        assert found is None

    @pytest.mark.asyncio
    async def test_query_multiple_models(self, db_engine_and_session):
        from sqlalchemy import select
        session, _ = db_engine_and_session
        for i in range(5):
            session.add(TestModelForDB(name=f"test_{i}", email=f"test_{i}@example.com"))
        await session.commit()
        result = await session.execute(select(TestModelForDB))
        items = result.scalars().all()
        assert len(items) == 5


class TestBaseModel:
    def test_base_metadata(self):
        assert Base is not None
        assert hasattr(Base, "metadata")


class TestDatabaseInit:
    @pytest.mark.asyncio
    async def test_init_database(self):
        os.environ["DB_TYPE"] = "sqlite"
        os.environ["DB_SQLITE_PATH"] = ":memory:"
        await init_database()
        await close_database()

    @pytest.mark.asyncio
    async def test_close_database(self):
        await close_database()


class TestGetDb:
    @pytest.mark.asyncio
    async def test_get_db_yields_session(self):
        os.environ["DB_TYPE"] = "sqlite"
        os.environ["DB_SQLITE_PATH"] = ":memory:"
        await init_database()
        async for session in get_db():
            assert session is not None
            break
        await close_database()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
