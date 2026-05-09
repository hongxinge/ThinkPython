"""ThinkPython 框架核心功能测试"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from starlette.testclient import TestClient
from main import app
from helpers.response import success_response, error_response
from helpers.auth import create_token, decode_token, skip_auth
from core.auth_middleware import _paths_match, _is_in_global_whitelist
from core.database import Base
from core.inspector import ColumnInfo, TableInfo, DatabaseInspector
from config.auth import SKIP_AUTH_PATHS, AUTH_ENABLED, JWT_SECRET, JWT_EXPIRE_HOURS
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


# ============== 测试数据库 ==============
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ============== 响应测试 ==============
class TestResponseHelpers:
    """响应辅助函数测试"""

    def test_success_response(self):
        """测试成功响应"""
        result = success_response(data={"key": "value"}, message="操作成功")
        assert result["code"] == 200
        assert result["message"] == "操作成功"
        assert result["data"] == {"key": "value"}

    def test_success_response_default(self):
        """测试成功响应默认值"""
        result = success_response()
        assert result["code"] == 200
        assert result["message"] == "success"
        assert result["data"] is None

    def test_error_response(self):
        """测试错误响应"""
        result = error_response(message="操作失败", code=400)
        assert result["code"] == 400
        assert result["message"] == "操作失败"
        assert result["data"] is None

    def test_error_response_default(self):
        """测试错误响应默认值"""
        result = error_response()
        assert result["code"] == 500
        assert result["message"] == "error"
        assert result["data"] is None


# ============== 认证测试 ==============
class TestAuthHelpers:
    """认证辅助函数测试"""

    def test_generate_token(self):
        """测试生成 JWT Token"""
        user_id = 1
        username = "testuser"
        token = create_token(user_id, extra_data={"username": username})
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_token_valid(self):
        """测试验证有效 Token"""
        user_id = 1
        username = "testuser"
        token = create_token(user_id, extra_data={"username": username})
        result = decode_token(token)
        assert result is not None
        assert result["user_id"] == user_id

    def test_verify_token_invalid(self):
        """测试验证无效 Token"""
        result = decode_token("invalid.token.here")
        assert result is None

    def test_verify_token_empty(self):
        """测试验证空 Token"""
        result = decode_token("")
        assert result is None

    def test_decode_token(self):
        """测试解码 Token"""
        user_id = 1
        username = "testuser"
        token = create_token(user_id, extra_data={"username": username})
        payload = decode_token(token)
        assert payload is not None
        assert payload["user_id"] == user_id

    def test_skip_auth_decorator(self):
        """测试 skip_auth 装饰器"""
        @skip_auth
        async def public_endpoint():
            return {"status": "ok"}
        
        assert hasattr(public_endpoint, "_skip_auth")
        assert public_endpoint._skip_auth is True


# ============== 认证中间件测试 ==============
class TestAuthMiddleware:
    """认证中间件测试"""

    def test_paths_match_exact(self):
        """测试精确路径匹配"""
        assert _paths_match("/api/login", "/api/login") is True
        assert _paths_match("/api/login", "/api/register") is False

    def test_paths_match_with_params(self):
        """测试路径参数匹配"""
        assert _paths_match("/user/123", "/user/{user_id}") is True
        assert _paths_match("/user/456", "/user/{user_id}") is True
        assert _paths_match("/user/123/profile", "/user/{user_id}/profile") is True

    def test_paths_match_different_lengths(self):
        """测试不同长度路径不匹配"""
        assert _paths_match("/api/login", "/api/login/extra") is False

    def test_is_in_global_whitelist(self):
        """测试全局白名单路由"""
        assert _is_in_global_whitelist("/health") is True
        assert _is_in_global_whitelist("/docs") is True
        assert _is_in_global_whitelist("/redoc") is True
        assert _is_in_global_whitelist("/openapi.json") is True
        assert _is_in_global_whitelist("/some/random") is False

    def test_skip_auth_paths_config(self):
        """测试跳过认证路径配置"""
        assert isinstance(SKIP_AUTH_PATHS, list)
        assert len(SKIP_AUTH_PATHS) > 0


# ============== 配置测试 ==============
class TestConfig:
    """配置测试"""

    def test_auth_config(self):
        """测试认证配置"""
        assert isinstance(AUTH_ENABLED, bool)
        assert isinstance(JWT_SECRET, str)
        assert len(JWT_SECRET) > 0
        assert isinstance(JWT_EXPIRE_HOURS, (int, float))
        assert JWT_EXPIRE_HOURS > 0

    def test_skip_auth_paths_not_empty(self):
        """测试跳过认证路径不为空"""
        assert len(SKIP_AUTH_PATHS) > 0
        assert "/health" in SKIP_AUTH_PATHS
        assert "/docs" in SKIP_AUTH_PATHS


# ============== 数据库测试 ==============
class TestDatabase:
    """数据库测试"""

    def test_base_model(self):
        """测试基础模型"""
        assert Base is not None
        assert hasattr(Base, "metadata")

    def test_database_config(self):
        """测试数据库配置"""
        from config.database import DATABASE_CONFIG
        assert isinstance(DATABASE_CONFIG, dict)
        assert "type" in DATABASE_CONFIG
        assert DATABASE_CONFIG["type"] in ["mysql", "postgresql", "sqlite", "mssql"]

    def test_get_database_url(self):
        """测试数据库 URL 生成"""
        from config.database import get_database_url
        url = get_database_url()
        assert isinstance(url, str)
        assert len(url) > 0


# ============== Inspector 测试 ==============
class TestInspector:
    """数据库检查器测试"""

    def test_column_info_creation(self):
        """测试 ColumnInfo 创建"""
        col = ColumnInfo(
            name="id",
            type="INTEGER",
            python_type="int",
            sqlalchemy_type="Integer",
            nullable=False,
            default=None,
            comment="主键",
            is_primary=True,
            is_auto_increment=True,
            max_length=None,
        )
        assert col.name == "id"
        assert col.python_type == "int"
        assert col.sqlalchemy_type == "Integer"
        assert col.is_primary is True
        assert col.is_auto_increment is True

    def test_table_info_creation(self):
        """测试 TableInfo 创建"""
        table = TableInfo(name="users", comment="用户表")
        col = ColumnInfo(name="id", type="INTEGER", python_type="int", sqlalchemy_type="Integer")
        table.add_column(col)
        table.primary_keys = ["id"]
        assert table.name == "users"
        assert table.comment == "用户表"
        assert len(table.columns) == 1
        assert table.primary_keys == ["id"]

    def test_database_inspector_init(self):
        """测试 DatabaseInspector 初始化"""
        inspector = DatabaseInspector()
        assert inspector is not None
        assert hasattr(inspector, "engine")

    def test_database_inspector_get_tables(self):
        """测试 DatabaseInspector 有 get_tables 方法"""
        inspector = DatabaseInspector()
        assert hasattr(inspector, "get_tables")
        assert hasattr(inspector, "get_table_info")
        assert hasattr(inspector, "connect")
        assert hasattr(inspector, "close")


# ============== API 路由测试 ==============
class TestAPIRoutes:
    """API 路由测试"""

    def setup_method(self):
        self.client = TestClient(app)

    def test_health_check(self):
        """测试健康检查"""
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["message"] == "ok"
        assert "app" in data["data"]

    def test_docs_endpoint(self):
        """测试 API 文档端点"""
        response = self.client.get("/docs")
        assert response.status_code == 200

    def test_openapi_json(self):
        """测试 OpenAPI JSON 端点"""
        response = self.client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data

    def test_redoc_endpoint(self):
        """测试 ReDoc 端点"""
        response = self.client.get("/redoc")
        assert response.status_code == 200

    def test_routes_exist(self):
        """测试路由存在"""
        routes = list(app.routes)
        assert len(routes) > 0


# ============== 控制器测试 ==============
class TestBaseController:
    """基础控制器测试"""

    def test_base_controller_import(self):
        """测试基础控制器导入"""
        from core.base_controller import BaseController
        assert BaseController is not None

    def test_base_controller_methods(self):
        """测试基础控制器方法"""
        from core.base_controller import BaseController
        assert hasattr(BaseController, "success")
        assert hasattr(BaseController, "error")
        assert hasattr(BaseController, "paginate")


# ============== 缓存测试 ==============
class TestCache:
    """缓存测试"""

    def test_cache_config(self):
        """测试缓存配置"""
        from config.cache import CACHE_CONFIG
        assert isinstance(CACHE_CONFIG, dict)
        assert "type" in CACHE_CONFIG
        assert CACHE_CONFIG["type"] in ["redis", "memory", "memcached"]

    def test_cache_module_structure(self):
        """测试缓存模块结构"""
        from core import cache
        assert hasattr(cache, "init_cache")
        assert hasattr(cache, "close_cache")
        assert hasattr(cache, "get_cache")
        assert hasattr(cache, "set_cache")
        assert hasattr(cache, "delete_cache")
        assert hasattr(cache, "cache_client")


# ============== 集成测试 ==============
class TestIntegration:
    """集成测试"""

    def test_app_startup(self):
        """测试应用启动"""
        from main import app
        assert app is not None
        assert "ThinkPython" in app.title

    def test_app_middleware(self):
        """测试中间件配置"""
        from main import app
        middlewares = [m for m in app.user_middleware]
        assert len(middlewares) > 0

    def test_env_example_exists(self):
        """测试 .env.example 存在"""
        assert os.path.exists(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env.example"))

    def test_requirements_exists(self):
        """测试 requirements.txt 存在"""
        assert os.path.exists(os.path.join(os.path.dirname(os.path.dirname(__file__)), "requirements.txt"))

    def test_docs_directory_exists(self):
        """测试 docs 目录存在"""
        docs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")
        assert os.path.exists(docs_dir)
        assert os.path.exists(os.path.join(docs_dir, "README.md"))


# ============== 运行测试 ==============
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
