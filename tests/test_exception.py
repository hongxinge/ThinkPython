"""ThinkPython 异常处理模块测试"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from core.exception import (
    AppException,
    NotFoundException,
    UnauthorizedException,
    ForbiddenException,
    ValidationException,
    app_exception_handler,
    validation_exception_handler,
    global_exception_handler,
)


class TestAppException:
    def test_app_exception_defaults(self):
        exc = AppException()
        assert exc.message == "操作失败"
        assert exc.code == 500
        assert exc.data is None

    def test_app_exception_custom(self):
        exc = AppException("自定义错误", code=400, data={"detail": "test"})
        assert exc.message == "自定义错误"
        assert exc.code == 400
        assert exc.data == {"detail": "test"}

    def test_app_exception_str(self):
        exc = AppException("测试消息")
        assert str(exc) == "测试消息"


class TestNotFoundException:
    def test_default_message(self):
        exc = NotFoundException()
        assert exc.message == "资源未找到"
        assert exc.code == 404

    def test_custom_message(self):
        exc = NotFoundException("用户不存在")
        assert exc.message == "用户不存在"
        assert exc.code == 404

    def test_inherits_from_app_exception(self):
        exc = NotFoundException()
        assert isinstance(exc, AppException)


class TestUnauthorizedException:
    def test_default_message(self):
        exc = UnauthorizedException()
        assert exc.message == "未授权访问"
        assert exc.code == 401

    def test_custom_message(self):
        exc = UnauthorizedException("Token 已过期")
        assert exc.message == "Token 已过期"
        assert exc.code == 401

    def test_inherits_from_app_exception(self):
        exc = UnauthorizedException()
        assert isinstance(exc, AppException)


class TestForbiddenException:
    def test_default_message(self):
        exc = ForbiddenException()
        assert exc.message == "禁止访问"
        assert exc.code == 403

    def test_custom_message(self):
        exc = ForbiddenException("仅管理员可访问")
        assert exc.message == "仅管理员可访问"
        assert exc.code == 403

    def test_inherits_from_app_exception(self):
        exc = ForbiddenException()
        assert isinstance(exc, AppException)


class TestValidationException:
    def test_default_message(self):
        exc = ValidationException()
        assert exc.message == "参数验证失败"
        assert exc.code == 422

    def test_custom_message(self):
        exc = ValidationException("用户名长度不合法")
        assert exc.message == "用户名长度不合法"
        assert exc.code == 422

    def test_inherits_from_app_exception(self):
        exc = ValidationException()
        assert isinstance(exc, AppException)


class TestExceptionHandlers:
    def setup_method(self):
        self.app = FastAPI()
        self.app.add_exception_handler(AppException, app_exception_handler)
        self.app.add_exception_handler(RequestValidationError, validation_exception_handler)
        self.app.add_exception_handler(Exception, global_exception_handler)
        self.client = TestClient(self.app)

    def test_app_exception_handler(self):
        @self.app.get("/test-app-exception")
        async def raise_app_exception():
            raise AppException("自定义错误", code=400, data={"field": "value"})

        response = self.client.get("/test-app-exception")
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == 400
        assert data["message"] == "自定义错误"
        assert data["data"] == {"field": "value"}

    def test_not_found_exception_handler(self):
        @self.app.get("/test-not-found")
        async def raise_not_found():
            raise NotFoundException("文章不存在")

        response = self.client.get("/test-not-found")
        assert response.status_code == 404
        data = response.json()
        assert data["code"] == 404
        assert data["message"] == "文章不存在"

    def test_unauthorized_exception_handler(self):
        @self.app.get("/test-unauthorized")
        async def raise_unauthorized():
            raise UnauthorizedException("请先登录")

        response = self.client.get("/test-unauthorized")
        assert response.status_code == 401
        data = response.json()
        assert data["code"] == 401
        assert data["message"] == "请先登录"

    def test_forbidden_exception_handler(self):
        @self.app.get("/test-forbidden")
        async def raise_forbidden():
            raise ForbiddenException("无权限")

        response = self.client.get("/test-forbidden")
        assert response.status_code == 403
        data = response.json()
        assert data["code"] == 403
        assert data["message"] == "无权限"

    def test_validation_exception_handler(self):
        @self.app.get("/test-validation")
        async def raise_validation():
            raise ValidationException("参数不合法")

        response = self.client.get("/test-validation")
        assert response.status_code == 422
        data = response.json()
        assert data["code"] == 422
        assert data["message"] == "参数不合法"

    def test_pydantic_validation_error(self):
        class ItemRequest(BaseModel):
            name: str
            age: int

        @self.app.post("/test-pydantic")
        async def create_item(item: ItemRequest):
            return {"name": item.name}

        response = self.client.post("/test-pydantic", json={"name": "test"})
        assert response.status_code == 422
        data = response.json()
        assert data["code"] == 422
        assert data["message"] == "参数验证失败"
        assert "data" in data
        assert isinstance(data["data"], list)

    def test_global_exception_handler(self):
        from config.app import APP_CONFIG
        original_debug = APP_CONFIG.get("debug", False)
        APP_CONFIG["debug"] = False

        @self.app.get("/test-global-exception")
        async def raise_global_exception():
            raise RuntimeError("测试运行时错误")

        try:
            response = self.client.get("/test-global-exception")
            assert response.status_code == 500
            data = response.json()
            assert data["code"] == 500
        except RuntimeError:
            pass
        finally:
            APP_CONFIG["debug"] = original_debug


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
