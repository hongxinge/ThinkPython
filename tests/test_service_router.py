"""ThinkPython BaseService 和 Router 测试"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import DeclarativeBase

from core.base_service import BaseService
from core.database import Base


class TestModel(Base):
    __tablename__ = "test_models_sr"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100))

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


# ============== BaseService 测试 ==============

class TestBaseServiceInit:
    """BaseService 初始化测试"""

    def test_init_with_valid_db(self):
        """测试使用有效 db 初始化"""
        mock_db = AsyncMock()
        service = BaseService(mock_db)
        service.model_class = TestModel
        assert service.db == mock_db

    def test_init_with_none_db(self):
        """测试使用 None db 初始化"""
        from core.exception import AppException
        with pytest.raises(AppException, match="数据库连接未初始化"):
            BaseService(None)


class TestBaseServiceCrud:
    """BaseService CRUD 操作测试"""

    @pytest.fixture
    def service(self):
        """创建测试服务实例"""
        mock_db = AsyncMock()
        service = BaseService(mock_db)
        service.model_class = TestModel
        return service

    @pytest.mark.asyncio
    async def test_get_by_id(self, service):
        """测试根据 ID 获取记录"""
        expected = TestModel(id=1, name="test")
        service.db.get.return_value = expected
        
        result = await service.get_by_id(1)
        assert result == expected
        service.db.get.assert_called_once_with(TestModel, 1)

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, service):
        """测试获取不存在的记录"""
        service.db.get.return_value = None
        
        result = await service.get_by_id(999)
        assert result is None

    @pytest.mark.asyncio
    async def test_create(self, service):
        """测试创建记录"""
        data = {"name": "new_item", "email": "new@example.com"}
        created_instance = TestModel(id=1, **data)
        service.db.flush = AsyncMock()
        service.db.refresh = AsyncMock()
        
        result = await service.create(data)
        
        service.db.add.assert_called_once()
        service.db.flush.assert_called_once()
        service.db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_existing(self, service):
        """测试更新已存在的记录"""
        existing = TestModel(id=1, name="old", email="old@example.com")
        service.db.get = AsyncMock(return_value=existing)
        service.db.flush = AsyncMock()
        service.db.refresh = AsyncMock()
        
        result = await service.update(1, {"name": "new"})
        
        assert result is not None
        assert result.name == "new"
        service.db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_nonexistent(self, service):
        """测试更新不存在的记录"""
        service.db.get = AsyncMock(return_value=None)
        
        result = await service.update(999, {"name": "new"})
        
        assert result is None
        service.db.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_existing(self, service):
        """测试删除已存在的记录"""
        existing = TestModel(id=1, name="test")
        service.db.get = AsyncMock(return_value=existing)
        service.db.flush = AsyncMock()
        
        result = await service.delete(1)
        
        assert result is True
        service.db.delete.assert_called_once_with(existing)
        service.db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, service):
        """测试删除不存在的记录"""
        service.db.get = AsyncMock(return_value=None)
        service.db.delete = AsyncMock()
        service.db.flush = AsyncMock()
        
        result = await service.delete(999)
        
        assert result is False
        service.db.delete.assert_not_called()


class TestBaseServicePagination:
    """BaseService 分页测试"""

    @pytest.fixture
    def service(self):
        """创建测试服务实例"""
        mock_db = AsyncMock()
        service = BaseService(mock_db)
        service.model_class = TestModel
        return service

    @pytest.mark.asyncio
    async def test_get_all_basic(self, service):
        """测试基础分页查询"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 10
        mock_result.scalars.return_value.all.return_value = []
        
        service.db.execute = AsyncMock(return_value=mock_result)
        
        items, total = await service.get_all(page=1, page_size=10)
        
        assert total == 10
        assert service.db.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_get_all_invalid_page(self, service):
        """测试无效页码"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_result.scalars.return_value.all.return_value = []
        
        service.db.execute = AsyncMock(return_value=mock_result)
        
        items, total = await service.get_all(page=-1, page_size=10)
        assert total == 0

    @pytest.mark.asyncio
    async def test_get_all_invalid_page_size(self, service):
        """测试无效页大小"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_result.scalars.return_value.all.return_value = []
        
        service.db.execute = AsyncMock(return_value=mock_result)
        
        items, total = await service.get_all(page=1, page_size=200)
        assert total == 0


# ============== Router 测试 ==============

class TestRouterModule:
    """路由模块测试"""

    def test_get_router_by_mode_import(self):
        """测试导入 get_router_by_mode"""
        from router import get_router_by_mode
        assert callable(get_router_by_mode)

    def test_get_router_by_mode_returns_router(self):
        """测试返回路由器实例"""
        from router import get_router_by_mode
        router = get_router_by_mode()
        assert router is not None

    def test_register_controller_routes_function(self):
        """测试 _register_controller_routes 函数存在"""
        from router import _register_controller_routes
        assert callable(_register_controller_routes)

    def test_register_controller_routes_empty_module(self):
        """测试空模块的路由注册"""
        from router import _register_controller_routes
        from fastapi import APIRouter
        
        empty_module = type(sys)("empty_module")
        main_router = APIRouter()
        
        count = _register_controller_routes(main_router, empty_module)
        assert count == 0

    def test_register_controller_routes_with_controller(self):
        from router import _register_controller_routes
        from core.base_controller import BaseController
        from fastapi import APIRouter

        class MockController(BaseController):
            def __init__(self):
                super().__init__()

            def _setup_routes(self):
                @self.router.get("/test")
                async def test_endpoint():
                    return {"message": "test"}

        MockController.__module__ = "mock_module"

        mock_module = type(sys)("mock_module")
        mock_module.MockController = MockController
        mock_module.__name__ = "mock_module"

        main_router = APIRouter()
        count = _register_controller_routes(main_router, mock_module)
        assert count == 1


class TestRouterAutoDiscovery:
    """路由自动发现测试"""

    def test_register_single_module_directory_not_exists(self, caplog):
        """测试单模块目录不存在的情况"""
        from router import register_single_module
        from fastapi import APIRouter
        
        main_router = APIRouter()
        register_single_module(main_router)

    def test_register_multi_modules_auto_discover(self, caplog):
        """测试多模块自动发现"""
        from router import register_multi_modules
        from fastapi import APIRouter
        from config.app import APP_CONFIG
        
        original_modules = APP_CONFIG["modules"]
        try:
            APP_CONFIG["modules"] = [""]
            main_router = APIRouter()
            register_multi_modules(main_router)
        finally:
            APP_CONFIG["modules"] = original_modules


# ============== 自定义服务子类测试 ==============

class TestCustomService:
    """自定义服务子类（用于测试）"""

    def __init__(self, db):
        self.db = db
        self.model_class = TestModel

    async def custom_method(self):
        return "custom_result"


class TestCustomServiceSubclass:
    @pytest.mark.asyncio
    async def test_custom_method(self):
        mock_db = AsyncMock()
        service = TestCustomService(mock_db)
        result = await service.custom_method()
        assert result == "custom_result"

    @pytest.mark.asyncio
    async def test_inherited_get_by_id(self):
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=TestModel(id=1))
        service = BaseService(mock_db)
        service.model_class = TestModel

        result = await service.get_by_id(1)
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
