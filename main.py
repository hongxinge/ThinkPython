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
from fastapi.responses import JSONResponse
from sqlalchemy import text
from contextlib import asynccontextmanager
from loguru import logger

from config.app import APP_CONFIG
from middleware import RequestLogMiddleware, setup_cors
from middleware.idempotency import IdempotencyMiddleware
from middleware.ratelimit import setup_rate_limit
from core.database import init_database, close_database
from core.cache import init_cache, close_cache
from core.auth_middleware import AuthMiddleware
from core.exception import (
    app_exception_handler,
    validation_exception_handler,
    global_exception_handler,
    AppException,
)
from fastapi.exceptions import RequestValidationError
from router import get_router_by_mode
from core.logger import setup_logging

# 初始化日志（幂等）：控制台 + 轮转文件，级别与时区来自 LOG_LEVEL / TIMEZONE
setup_logging()


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
    
    # 安全配置检查：使用默认密钥时，生产环境必须拒绝启动
    try:
        from config.auth import USING_DEFAULT_JWT_SECRET, validate_secret_config

        if validate_secret_config(USING_DEFAULT_JWT_SECRET, APP_CONFIG["debug"]):
            logger.warning(
                "检测到使用默认 JWT_SECRET，存在严重安全风险！\n"
                "   请生成强随机密钥并写入 .env：\n"
                "   python -c \"import secrets; print('JWT_SECRET=' + secrets.token_hex(32))\"\n"
                "   （当前为 debug 模式，暂时放行；生产环境将拒绝启动）"
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
        # 仅在调试模式下启用交互式 API 文档（Swagger UI 和 ReDoc）
        # 生产环境默认关闭文档页面，防止暴露 API 结构
        docs_url="/docs" if APP_CONFIG["debug"] else None,
        redoc_url="/redoc" if APP_CONFIG["debug"] else None,
        # schema 端点独立开关：客户端团队需要用 /openapi.json 生成 SDK，
        # 因此默认与 debug 同步，但允许通过 OPENAPI_ENABLED 单独打开或关闭。
        # 关闭后 think.py openapi / make-client 仍可工作（直接调用 app.openapi()）。
        openapi_url="/openapi.json" if APP_CONFIG["openapi_enabled"] else None,
    )
    
    # ===== 配置中间件 =====
    # 注意：FastAPI/Starlette 中间件的执行顺序与注册顺序相反（后注册的在最外层、最先执行）。
    # 期望的执行顺序（从外到内）：GZip -> 请求日志 -> CORS -> 限流 -> 认证 -> 幂等 -> 路由
    # 这样设计可确保：
    #   1. 压缩在最外层：所有响应（含中间件自身产生的 401/429）都能按尺寸决定是否压缩
    #   2. CORS 在认证之外：浏览器跨域预检请求(OPTIONS)不会被认证拦截，
    #      401/429 等错误响应也会携带 CORS 头，前端能正常读取错误信息
    #   3. 限流在认证之外：登录等免认证接口同样受到限流保护（防暴力破解）
    #   4. 请求日志在外层：所有请求（含被中间件拦截的请求）都会被记录
    #   5. 幂等在认证之内：需要读取 current_user 做用户维度隔离，
    #      且认证失败的请求不应写入幂等缓存
    #
    # 为什么全部用 add_middleware 而不是 app.middleware("http")(fn)：
    # 函数式中间件底层是 BaseHTTPMiddleware，会把响应包进 anyio 内存流逐块转发。
    # 那样每个请求多一次拷贝，且 GZipMiddleware 只在收到「单次完整 body」时才比较
    # minimum_size，流式响应会被无条件压缩——87 字节的 /health 会被压成 106 字节，
    # 越压越大。改纯 ASGI 后响应保持原始形态，门限才真正生效。
    app.add_middleware(IdempotencyMiddleware)  # 幂等键（最内层）
    app.add_middleware(AuthMiddleware)  # 全局认证中间件
    setup_rate_limit(app)  # API 限流中间件
    setup_cors(app)  # CORS 跨域中间件
    app.add_middleware(RequestLogMiddleware)  # 请求日志中间件

    if APP_CONFIG["gzip"]["enabled"]:
        from starlette.middleware.gzip import GZipMiddleware

        app.add_middleware(
            GZipMiddleware,  # 最外层
            minimum_size=APP_CONFIG["gzip"]["minimum_size"],
            compresslevel=APP_CONFIG["gzip"]["compresslevel"],
        )
    
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
    @app.get("/health", summary="存活检查")
    async def health_check():
        """存活检查（liveness）

        只返回进程状态，**不访问数据库与缓存**。
        用途：容器编排判断进程是否存活，失败则重启容器。
        刻意保持轻量，避免探活流量把数据库打满。

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

    @app.get("/health/ready", summary="就绪检查")
    async def readiness_check():
        """就绪检查（readiness）

        检查应用依赖是否可用：数据库连通性、缓存可用性。
        用途：负载均衡摘流 / 发布流程等待依赖就绪。
        任一依赖不可用时返回 HTTP 503，客户端与网关据此停止转发流量。

        Returns:
            JSONResponse: 200 就绪 / 503 未就绪，data 中给出各依赖状态
        """
        checks = {}
        ready = True

        # 数据库连通性：一次 SELECT 1，开销约等于一次往返
        try:
            from core import database as db_module

            if db_module.async_session is None:
                checks["database"] = "not_initialized"
                ready = False
            else:
                async with db_module.async_session() as session:
                    await session.execute(text("SELECT 1"))
                checks["database"] = "ok"
        except Exception as exc:  # noqa: BLE001 - 就绪检查需要吞掉异常并上报
            checks["database"] = f"error: {type(exc).__name__}"
            ready = False

        # 缓存可用性：写入后立即读回
        try:
            from core.cache import get_cache, set_cache

            await set_cache("health:probe", "1", ttl=5)
            checks["cache"] = "ok" if await get_cache("health:probe") is not None else "degraded"
        except Exception as exc:  # noqa: BLE001
            checks["cache"] = f"error: {type(exc).__name__}"
            ready = False

        return JSONResponse(
            status_code=200 if ready else 503,
            content={
                "code": 200 if ready else 503,
                "message": "ready" if ready else "not ready",
                "data": checks,
            },
        )

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
