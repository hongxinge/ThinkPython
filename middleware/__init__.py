"""
中间件配置
"""
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
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
    """请求日志中间件"""
    import time
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    print(f"[{request.method}] {request.url.path} - {response.status_code} - {process_time:.4f}s")
    
    return response
