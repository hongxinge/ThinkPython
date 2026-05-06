"""
异常处理
"""
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


class AppException(Exception):
    """应用基础异常"""
    
    def __init__(self, message: str = "操作失败", code: int = 500, data: Any = None):
        self.message = message
        self.code = code
        self.data = data
        super().__init__(message)


class NotFoundException(AppException):
    """资源未找到异常"""
    
    def __init__(self, message: str = "资源未找到"):
        super().__init__(message=message, code=404)


class UnauthorizedException(AppException):
    """未授权异常"""
    
    def __init__(self, message: str = "未授权访问"):
        super().__init__(message=message, code=401)


class ForbiddenException(AppException):
    """禁止访问异常"""
    
    def __init__(self, message: str = "禁止访问"):
        super().__init__(message=message, code=403)


class ValidationException(AppException):
    """验证异常"""
    
    def __init__(self, message: str = "参数验证失败"):
        super().__init__(message=message, code=422)


async def app_exception_handler(request: Request, exc: AppException):
    """应用异常处理器"""
    return JSONResponse(
        status_code=exc.code,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": exc.data,
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """验证异常处理器"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
        })
    return JSONResponse(
        status_code=422,
        content={
            "code": 422,
            "message": "参数验证失败",
            "data": errors,
        },
    )


async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": f"服务器内部错误: {str(exc)}",
            "data": None,
        },
    )
