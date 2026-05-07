"""
中间件配置
"""
import time
import uuid
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from config.app import APP_CONFIG


def setup_cors(app):
    """配置CORS中间件"""
    cors_config = APP_CONFIG["cors"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_config["allow_origins"],
        allow_credentials=cors_config["allow_credentials"],
        allow_methods=cors_config["allow_methods"],
        allow_headers=cors_config["allow_headers"],
    )


async def request_log_middleware(request: Request, call_next):
    """请求日志中间件 - 记录请求耗时和追踪ID"""
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    # 将request_id添加到请求头，方便后续使用
    request.state.request_id = request_id
    
    logger.info(f"请求开始 [{request_id}] {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(
        f"请求完成 [{request_id}] {request.method} {request.url.path} - "
        f"{response.status_code} - {process_time:.4f}s"
    )
    
    # 在响应头中添加request_id
    response.headers["X-Request-ID"] = request_id
    
    return response
