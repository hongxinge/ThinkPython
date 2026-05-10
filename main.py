"""
ThinkPython 应用入口

本文件是整个 FastAPI 应用的入口点，负责：
1. 创建 FastAPI 应用实例
2. 配置应用生命周期管理（启动/关闭时的初始化操作）
3. 注册中间件（CORS、请求日志等）
4. 注册全局异常处理器
5. 自动注册路由（支持单模块/多模块切换）
6. 提供健康检查接口

应用架构：
    请求 -> 中间件 -> 路由 -> 控制器 -> 服务 -> 模型 -> 数据库
                |          |         |        |
              CORS      路由解析   参数校验  业务逻辑
              日志      控制器注册  响应封装  数据访问

使用方式:
    # 方式1: 使用 uvicorn 命令行启动
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    
    # 方式2: 使用 CLI 工具启动
    python think.py run
    
    # 方式3: 直接运行此文件
    python main.py
"""
import os
from fastapi import FastAPI
from contextlib import asynccontextmanager
from loguru import logger

from config.app import APP_CONFIG
from middleware import setup_cors, request_log_middleware
from middleware.ratelimit import setup_rate_limit
from core.database import init_database, close_database
from core.cache import init_cache, close_cache
from core.auth_middleware import auth_middleware
from core.exception import (
    app_exception_handler,
    validation_exception_handler,
    global_exception_handler,
    AppException,
)
from fastapi.exceptions import RequestValidationError
from router import get_router_by_mode


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理器
    
    使用 FastAPI 的 lifespan 上下文管理器来处理应用的启动和关闭事件。
    yield 之前的代码在应用启动时执行，yield 之后的代码在应用关闭时执行。
    
    启动时执行：
    1. 打印应用名称和版本信息
    2. 安全配置检查（JWT 密钥等）
    3. 初始化数据库连接（连接池）
    4. 初始化缓存连接（Redis 或 Memory）
    
    关闭时执行：
    1. 关闭数据库连接池
    2. 关闭缓存连接
    
    Args:
        app: FastAPI 应用实例
    """
    # ===== 启动时执行 =====
    logger.info(f"🚀 {APP_CONFIG['name']} v{APP_CONFIG['version']} 启动中...")
    logger.info(f"📦 模块模式: {APP_CONFIG['module_mode']}")
    
    # 安全配置检查
    try:
        from config.auth import USING_DEFAULT_JWT_SECRET
        if USING_DEFAULT_JWT_SECRET:
            logger.warning(
                "⚠️  检测到使用默认 JWT_SECRET，存在安全风险！\n"
                "   请通过环境变量配置强随机密钥：\n"
                "   export JWT_SECRET=$(openssl rand -hex 32)\n"
                "   或在 .env 文件中添加：JWT_SECRET=<your-secret-key>"
            )
    except ImportError:
        pass
    
    # 初始化数据库连接（创建连接池）
    await init_database()
    # 初始化缓存连接（Redis 连接或内存缓存）
    await init_cache()
    
    logger.info("✅ 数据库和缓存初始化完成")
    
    yield  # 应用在此处运行，处理 HTTP 请求
    
    # ===== 关闭时执行 =====
    await close_database()  # 释放数据库连接池
    await close_cache()  # 关闭缓存连接
    logger.info("👋 应用已关闭")


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例
    
    这是应用工厂函数，负责组装 FastAPI 应用的所有组件：
    1. 创建 FastAPI 实例（含基本信息和调试配置）
    2. 配置 CORS 中间件和请求日志中间件
    3. 注册全局异常处理器
    4. 注册路由（根据模块模式自动扫描控制器）
    5. 添加健康检查接口
    
    Returns:
        FastAPI: 配置完成的 FastAPI 应用实例
        
    使用示例:
        from main import create_app
        
        app = create_app()
        # app 已经包含了所有中间件、路由和异常处理器
    """
    # 创建 FastAPI 应用实例
    app = FastAPI(
        title=APP_CONFIG["name"],  # 应用名称，显示在 API 文档中
        version=APP_CONFIG["version"],  # 应用版本号
        debug=APP_CONFIG["debug"],  # 调试模式
        lifespan=lifespan,  # 绑定生命周期管理器
        # 仅在调试模式下启用 API 文档（Swagger UI 和 ReDoc）
        # 生产环境关闭文档接口，防止暴露 API 结构
        docs_url="/docs" if APP_CONFIG["debug"] else None,
        redoc_url="/redoc" if APP_CONFIG["debug"] else None,
    )
    
    # ===== 配置中间件 =====
    setup_cors(app)  # 添加 CORS 跨域中间件
    app.middleware("http")(request_log_middleware)  # 添加请求日志中间件
    setup_rate_limit(app)  # 添加 API 限流中间件
    
    # 注册全局认证中间件
    app.middleware("http")(auth_middleware)
    
    # ===== 注册异常处理器 =====
    # 处理自定义应用异常（AppException 及其子类）
    app.add_exception_handler(AppException, app_exception_handler)
    # 处理 Pydantic 参数验证异常
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    # 处理所有未被捕获的未知异常
    app.add_exception_handler(Exception, global_exception_handler)
    
    # ===== 注册路由 =====
    # 根据配置自动扫描并注册控制器路由（支持单模块/多模块模式）
    main_router = get_router_by_mode()
    app.include_router(main_router)
    
    # ===== 健康检查接口 =====
    @app.get("/health", summary="健康检查")
    async def health_check():
        """健康检查接口
        
        用于负载均衡器、容器编排系统（如 Kubernetes）检测应用是否存活。
        返回应用的基本信息，不含敏感数据。
        
        Returns:
            Dict: 应用状态信息
        """
        return {
            "code": 200,
            "message": "ok",
            "data": {
                "app": APP_CONFIG["name"],
                "version": APP_CONFIG["version"],
                "debug": APP_CONFIG["debug"],
            },
        }
    
    return app


# 创建全局应用实例，供 uvicorn 等 ASGI 服务器使用
app = create_app()


if __name__ == "__main__":
    # 直接运行此文件时启动开发服务器
    import uvicorn
    uvicorn.run(
        "main:app",  # 指定应用模块路径
        host="0.0.0.0",  # 监听所有网络接口
        port=8000,  # 默认端口
        reload=APP_CONFIG["debug"],  # 调试模式下开启热重载
    )
