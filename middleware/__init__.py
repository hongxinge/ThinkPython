"""
ThinkPython 中间件配置

本模块负责配置和管理 FastAPI 中间件，包括：
- setup_cors(): 配置 CORS 跨域中间件
- request_log_middleware(): 请求日志中间件（记录请求耗时和追踪 ID）

中间件是 HTTP 请求处理管道中的中间层，可以在请求到达路由前后执行自定义逻辑。
典型的中间件用途包括：跨域处理、日志记录、认证校验、性能监控等。

请求处理流程：
    客户端请求 -> CORS 中间件 -> 请求日志中间件 -> 路由 -> 控制器 -> 响应
                                                              |
    客户端响应 <- CORS 中间件 <- 请求日志中间件 <- 控制器响应 <-
"""
import time
import uuid
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from config.app import APP_CONFIG


def setup_cors(app):
    """配置 CORS 跨域中间件
    
    CORS（Cross-Origin Resource Sharing，跨域资源共享）是浏览器的安全策略。
    当前端和后端部署在不同域名时，需要配置 CORS 允许前端跨域访问后端 API。
    
    配置项从 config/app.py 的 APP_CONFIG["cors"] 中读取，包括：
    - allow_origins: 允许的来源域名列表
    - allow_credentials: 是否允许携带认证信息
    - allow_methods: 允许的 HTTP 方法
    - allow_headers: 允许的 HTTP 请求头
    
    Args:
        app: FastAPI 应用实例
        
    使用示例:
        from middleware import setup_cors
        
        app = FastAPI()
        setup_cors(app)  # 启用跨域支持
    """
    cors_config = APP_CONFIG["cors"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_config["allow_origins"],  # 允许的来源域名
        allow_credentials=cors_config["allow_credentials"],  # 是否允许携带 Cookie
        allow_methods=cors_config["allow_methods"],  # 允许的 HTTP 方法（GET/POST/PUT/DELETE 等）
        allow_headers=cors_config["allow_headers"],  # 允许的请求头（Content-Type/Authorization 等）
    )


async def request_log_middleware(request: Request, call_next):
    """请求日志中间件 - 记录每个请求的耗时和追踪 ID
    
    此中间件在请求处理前后记录以下信息：
    - 唯一请求 ID（UUID），方便在日志中追踪同一请求的完整链路
    - 请求方法和路径
    - 响应状态码
    - 请求处理耗时
    
    请求 ID 会被附加到响应头 X-Request-ID 中，前端可以在需要时用于问题排查。
    
    Args:
        request: FastAPI 请求对象
        call_next: 下一个中间件或路由处理函数，调用它以继续请求处理链
        
    Returns:
        Response: 处理后的响应对象（已添加 X-Request-ID 响应头）
        
    使用示例:
        # 在 main.py 中注册
        from middleware import request_log_middleware
        
        app.middleware("http")(request_log_middleware)
    """
    start_time = time.time()  # 记录请求开始时间
    request_id = str(uuid.uuid4())  # 生成唯一的请求追踪 ID
    
    # 将 request_id 存储到请求状态中，方便后续中间件或路由使用
    request.state.request_id = request_id
    
    logger.info(f"请求开始 [{request_id}] {request.method} {request.url.path}")
    
    # 调用下一个中间件或路由处理函数
    response = await call_next(request)
    
    # 计算请求处理耗时
    process_time = time.time() - start_time
    logger.info(
        f"请求完成 [{request_id}] {request.method} {request.url.path} - "
        f"{response.status_code} - {process_time:.4f}s"
    )
    
    # 在响应头中添加 request_id，方便前端和运维排查问题
    response.headers["X-Request-ID"] = request_id
    
    return response
