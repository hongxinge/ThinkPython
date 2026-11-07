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
from typing import Optional

from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from starlette.datastructures import MutableHeaders

from config.app import APP_CONFIG
from core.context import bind_request_id
from helpers.net import get_client_ip


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

    # 安全提醒：allow_origins 含 "*" 且允许携带凭证的组合，浏览器会拒绝生效且存在安全风险
    if "*" in cors_config["allow_origins"] and cors_config["allow_credentials"]:
        logger.warning(
            "CORS 配置了 allow_origins=['*'] 且 allow_credentials=True，"
            "该组合违反 CORS 规范（浏览器会拒绝携带凭证的跨域请求）。"
            "生产环境请在 .env 中通过 CORS_ORIGINS 指定明确的域名列表"
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_config["allow_origins"],  # 允许的来源域名
        allow_credentials=cors_config["allow_credentials"],  # 是否允许携带 Cookie
        allow_methods=cors_config["allow_methods"],  # 允许的 HTTP 方法（GET/POST/PUT/DELETE 等）
        allow_headers=cors_config["allow_headers"],  # 允许的请求头（Content-Type/Authorization 等）
    )


# 客户端可自带追踪 ID 时沿用它，便于「客户端日志 ↔ 服务端日志」对齐。
# 只接受安全字符与合理长度，避免日志注入或超长头占用内存。
_REQUEST_ID_HEADER = "X-Request-ID"
_REQUEST_ID_SAFE_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")
_MAX_REQUEST_ID_LENGTH = 64


def _resolve_request_id(request: Request) -> str:
    """解析请求追踪 ID

    优先使用客户端传入的 ``X-Request-ID``（移动端弱网重试时能保持同一 ID），
    缺失或格式非法时生成新的 UUID4。

    Args:
        request: FastAPI 请求对象

    Returns:
        str: 合法的请求追踪 ID
    """
    incoming = (request.headers.get(_REQUEST_ID_HEADER) or "").strip()
    if (
        incoming
        and len(incoming) <= _MAX_REQUEST_ID_LENGTH
        and all(ch in _REQUEST_ID_SAFE_CHARS for ch in incoming)
    ):
        return incoming
    return str(uuid.uuid4())


def _client_ip(request: Request) -> str:
    """获取客户端 IP（兼容反向代理，受 TRUST_PROXY 控制）"""
    return get_client_ip(request)


class RequestLogMiddleware:
    """请求日志中间件（纯 ASGI 实现）

    记录耗时与追踪 ID，并把 ``X-Request-ID`` 注入响应头。

    行为约定：

    - **沿用客户端 X-Request-ID**：移动端重试时能串起同一次业务操作；
    - **只在结束时打一条日志**：避免每请求两条日志把生产日志量翻倍；
    - **慢请求单独告警**：超过 ``LOG_SLOW_REQUEST_MS`` 用 WARNING 级别，
      便于直接按级别抓慢接口；
    - **异常也记录**：未捕获异常会带上 request_id 与耗时再抛出，
      由全局异常处理器转成 500。

    为什么是纯 ASGI：``BaseHTTPMiddleware`` 会把响应包进 anyio 内存流逐块转发，
    每个请求多一次拷贝，且让下游的 GZip 失去尺寸判断能力（详见
    ``core/auth_middleware.AuthMiddleware`` 的说明）。
    """

    def __init__(self, app, slow_request_ms: Optional[int] = None):
        self.app = app
        self.slow_threshold_ms = (
            slow_request_ms
            if slow_request_ms is not None
            else APP_CONFIG["log"].get("slow_request_ms", 500)
        )

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        request_id = _resolve_request_id(request)
        client_ip = _client_ip(request)

        # 供控制器与异常处理器读取（Request.state 本身基于 scope["state"]）
        scope.setdefault("state", {})["request_id"] = request_id

        method = scope.get("method", "")
        path = scope.get("path", "")
        # perf_counter 是单调时钟，不受系统时间调整影响，比 time.time 更准
        start = time.perf_counter()
        status_code = 500

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                # 客户端可据此上报问题，服务端按 ID 检索完整链路
                MutableHeaders(scope=message)[_REQUEST_ID_HEADER] = request_id
            await send(message)

        with bind_request_id(request_id, client_ip):
            try:
                await self.app(scope, receive, send_wrapper)
            except Exception:
                elapsed_ms = (time.perf_counter() - start) * 1000
                logger.exception(
                    f"{method} {path} -> 未捕获异常 | "
                    f"{elapsed_ms:.1f}ms | ip={client_ip} | request_id={request_id}"
                )
                raise

            elapsed_ms = (time.perf_counter() - start) * 1000
            log = logger.warning if elapsed_ms >= self.slow_threshold_ms else logger.info
            log(
                f"{method} {path} -> {status_code} | "
                f"{elapsed_ms:.1f}ms | ip={client_ip} | request_id={request_id}"
            )


async def request_log_middleware(request: Request, call_next):
    """[兼容保留] 函数式请求日志中间件

    旧代码里的 ``app.middleware("http")(request_log_middleware)`` 仍然可用，
    但会重新引入 ``BaseHTTPMiddleware`` 的流包装开销。
    新代码请改用 ``app.add_middleware(RequestLogMiddleware)``。

    Args:
        request: FastAPI 请求对象
        call_next: 下一个中间件或路由处理函数

    Returns:
        Response: 处理后的响应（带 X-Request-ID 响应头）
    """
    request_id = _resolve_request_id(request)
    client_ip = _client_ip(request)

    # 保留 request.state 上的副本，兼容既有控制器代码的读取习惯
    request.state.request_id = request_id

    start = time.perf_counter()
    slow_threshold_ms = APP_CONFIG["log"].get("slow_request_ms", 500)

    with bind_request_id(request_id, client_ip):
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                f"{request.method} {request.url.path} -> 未捕获异常 | "
                f"{elapsed_ms:.1f}ms | ip={client_ip} | request_id={request_id}"
            )
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000
        log = logger.warning if elapsed_ms >= slow_threshold_ms else logger.info
        log(
            f"{request.method} {request.url.path} -> {response.status_code} | "
            f"{elapsed_ms:.1f}ms | ip={client_ip} | request_id={request_id}"
        )

        # 客户端可据此上报问题，服务端按 ID 检索完整链路
        response.headers[_REQUEST_ID_HEADER] = request_id
        return response
