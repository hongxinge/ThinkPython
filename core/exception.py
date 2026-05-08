"""
ThinkPython 异常处理模块

本模块定义了应用的异常体系和全局异常处理器，包括：
- AppException: 应用基础异常类，所有自定义异常的父类
- NotFoundException: 资源未找到异常（404）
- UnauthorizedException: 未授权访问异常（401）
- ForbiddenException: 禁止访问异常（403）
- ValidationException: 参数验证失败异常（422）
- app_exception_handler: 应用异常处理器
- validation_exception_handler: 验证异常处理器
- global_exception_handler: 全局异常处理器

所有异常都会以统一的 JSON 格式返回：
{"code": 状态码, "message": "提示信息", "data": 附加数据}

使用示例:
    from core.exception import NotFoundException, AppException
    
    # 在控制器或服务中抛出异常
    user = await get_user(1)
    if not user:
        raise NotFoundException("用户不存在")
    
    # 全局异常处理器会自动捕获并返回统一的 JSON 响应
"""
from typing import Any
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from loguru import logger
from config.app import APP_CONFIG


class AppException(Exception):
    """应用基础异常类 - 所有自定义异常的父类
    
    用于在业务逻辑中抛出自定义异常，由全局异常处理器统一处理。
    
    Args:
        message: 异常提示信息
        code: 业务状态码，对应 HTTP 状态码
        data: 附加的错误详情数据（可选）
        
    使用示例:
        raise AppException("操作失败", code=500)
        raise AppException("余额不足", code=400, data={"balance": 0})
    """
    
    def __init__(self, message: str = "操作失败", code: int = 500, data: Any = None):
        self.message = message
        self.code = code
        self.data = data
        super().__init__(message)


class NotFoundException(AppException):
    """资源未找到异常（HTTP 404）
    
    用于表示请求的资源不存在，如用户不存在、文章不存在等。
    
    使用示例:
        raise NotFoundException("用户不存在")
        raise NotFoundException(f"文章 {article_id} 不存在")
    """
    
    def __init__(self, message: str = "资源未找到"):
        super().__init__(message=message, code=404)


class UnauthorizedException(AppException):
    """未授权访问异常（HTTP 401）
    
    用于表示用户未登录或 Token 无效/过期。
    
    使用示例:
        raise UnauthorizedException("请先登录")
        raise UnauthorizedException("Token 已过期")
    """
    
    def __init__(self, message: str = "未授权访问"):
        super().__init__(message=message, code=401)


class ForbiddenException(AppException):
    """禁止访问异常（HTTP 403）
    
    用于表示用户已登录但没有权限访问该资源。
    
    使用示例:
        raise ForbiddenException("您没有权限执行此操作")
        raise ForbiddenException("仅管理员可访问")
    """
    
    def __init__(self, message: str = "禁止访问"):
        super().__init__(message=message, code=403)


class ValidationException(AppException):
    """参数验证失败异常（HTTP 422）
    
    用于表示请求参数不符合业务规则。
    注意：FastAPI 的 Pydantic 验证失败会触发 RequestValidationError，
    而非此异常。此异常用于自定义的业务参数验证。
    
    使用示例:
        raise ValidationException("用户名长度必须在3-20个字符之间")
    """
    
    def __init__(self, message: str = "参数验证失败"):
        super().__init__(message=message, code=422)


async def app_exception_handler(request: Request, exc: AppException):
    """应用异常处理器 - 处理所有 AppException 及其子类异常
    
    当业务代码抛出 AppException 或其子类（NotFoundException 等）时，
    FastAPI 会调用此处理器，返回统一的 JSON 格式响应。
    
    Args:
        request: FastAPI 请求对象
        exc: 捕获到的 AppException 实例
        
    Returns:
        JSONResponse: 格式化的错误响应
    """
    logger.warning(f"应用异常: {exc.message} [path: {request.url.path}]")
    return JSONResponse(
        status_code=exc.code,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": exc.data,
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """验证异常处理器 - 处理 FastAPI/Pydantic 参数验证失败
    
    当请求参数不符合 Pydantic 模型定义时（如类型错误、缺少必填字段等），
    FastAPI 会抛出 RequestValidationError，此处理器将其格式化为统一的响应格式。
    
    Args:
        request: FastAPI 请求对象
        exc: 捕获到的 RequestValidationError 实例
        
    Returns:
        JSONResponse: 格式化的参数验证错误响应，包含详细的字段错误信息
    """
    errors = []
    for error in exc.errors():
        errors.append({
            # 拼接错误字段路径，如 "body.username" 或 "path.user_id"
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],  # Pydantic 提供的错误描述
        })
    logger.warning(f"参数验证失败: {errors} [path: {request.url.path}]")
    return JSONResponse(
        status_code=422,
        content={
            "code": 422,
            "message": "参数验证失败",
            "data": errors,  # 返回详细的字段错误列表
        },
    )


async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器 - 捕获所有未被处理的异常
    
    这是最后一道防线，捕获所有未被其他处理器处理的异常。
    根据调试模式决定返回详细错误信息还是通用错误信息：
    - 开发环境（debug=True）：返回详细错误堆栈，方便调试
    - 生产环境（debug=False）：返回通用错误信息，防止敏感信息泄露
    
    Args:
        request: FastAPI 请求对象
        exc: 捕获到的异常实例
        
    Returns:
        JSONResponse: 格式化的服务器内部错误响应
    """
    # 记录完整错误堆栈到日志，方便排查问题
    logger.error(f"服务器内部错误: {str(exc)} [path: {request.url.path}]", exc_info=True)
    
    if APP_CONFIG["debug"]:
        # 开发环境：返回详细错误信息，帮助开发者快速定位问题
        message = f"服务器内部错误: {str(exc)}"
    else:
        # 生产环境：返回通用错误信息，防止数据库结构、代码路径等敏感信息泄露
        message = "服务器内部错误"
    
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": message,
            "data": None,
        },
    )
