"""
应用入口
"""
import os
from fastapi import FastAPI
from contextlib import asynccontextmanager

from config.app import APP_CONFIG
from middleware import setup_cors
from core.database import init_database, close_database
from core.cache import init_cache, close_cache
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
    """应用生命周期管理"""
    # 启动时执行
    print(f"🚀 {APP_CONFIG['name']} v{APP_CONFIG['version']} 启动中...")
    print(f"📦 模块模式: {APP_CONFIG['module_mode']}")
    
    await init_database()
    await init_cache()
    
    print("✅ 数据库和缓存初始化完成")
    
    yield
    
    # 关闭时执行
    await close_database()
    await close_cache()
    print("👋 应用已关闭")


def create_app() -> FastAPI:
    """创建FastAPI应用实例"""
    app = FastAPI(
        title=APP_CONFIG["name"],
        version=APP_CONFIG["version"],
        debug=APP_CONFIG["debug"],
        lifespan=lifespan,
        docs_url="/docs" if APP_CONFIG["debug"] else None,
        redoc_url="/redoc" if APP_CONFIG["debug"] else None,
    )
    
    # 配置中间件
    setup_cors(app)
    
    # 注册异常处理器
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, global_exception_handler)
    
    # 注册路由
    main_router = get_router_by_mode()
    app.include_router(main_router)
    
    # 健康检查
    @app.get("/health")
    async def health_check():
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


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=APP_CONFIG["debug"],
    )
