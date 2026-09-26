"""
ThinkPython 认证中间件

提供全局级别的自动认证拦截功能，核心特性：
- 默认所有接口都需要认证（安全优先）
- 通过白名单跳过认证（全局配置 + 控制器配置 + 装饰器三种方式）
- 支持将当前用户信息注入到请求上下文中
- 自动返回 401 错误，无需业务代码处理

认证拦截规则（按优先级从高到低）：
1. 装饰器标记：@skip_auth 标记的接口直接跳过认证
2. 控制器白名单：SKIP_AUTH_ROUTES 列表中配置的路径跳过认证
3. 全局白名单：SKIP_AUTH_PATHS 列表中配置的路径跳过认证
4. 其他所有接口：需要携带有效的 JWT Token

使用方式：
    # 方式1: 全局白名单（config/auth.py）
    SKIP_AUTH_PATHS = ["/health", "/auth/login", "/auth/register"]
    
    # 方式2: 控制器级白名单
    class AuthController(BaseController):
        SKIP_AUTH_ROUTES = ["POST /login", "POST /register"]
    
    # 方式3: 装饰器标记
    @self.router.post("/login")
    @skip_auth
    async def login():
        pass
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Callable
from functools import wraps

from helpers.auth import decode_token, get_token_from_header, CurrentUser, is_token_blacklisted
from config.auth import SKIP_AUTH_PATHS, AUTH_ENABLED
from router import iter_flat_routes


def skip_auth(func: Callable) -> Callable:
    """免验证接口装饰器
    
    标记该接口不需要 JWT 认证，即使在全局认证开启的情况下也能直接访问。
    适用于登录、注册、忘记密码等公开接口。
    
    注意：
        此装饰器优先级最高，会覆盖全局白名单和控制器白名单的配置。
    
    使用示例:
        class AuthController(BaseController):
            @self.router.post("/login", summary="用户登录")
            @skip_auth
            async def login():
                # 无需 Token，任何人都可以访问
                pass
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    
    # 标记为跳过认证
    wrapper._skip_auth = True
    return wrapper


def _is_skip_auth_route(method: str, path: str, route_obj) -> bool:
    """检查路由是否标记为免验证
    
    Args:
        method: HTTP 请求方法（GET/POST 等）
        path: 请求路径
        route_obj: FastAPI 路由对象
        
    Returns:
        bool: 是否跳过认证
    """
    # 检查路由函数本身是否被 @skip_auth 装饰
    endpoint = getattr(route_obj, "endpoint", None)
    if endpoint and getattr(endpoint, "_skip_auth", False):
        return True
    
    # 检查是否有 public_route 标记（旧版兼容）
    if endpoint and getattr(endpoint, "_is_public", False):
        return True
    
    return False


def _is_in_controller_whitelist(method: str, path: str, route_obj) -> bool:
    """检查路由是否在控制器的白名单中
    
    支持三种匹配方式：
    1. 精确匹配：白名单 "POST /auth/login" 匹配实际路由 "POST /api/auth/login"
    2. 相对路径匹配：白名单中的路径是路由路径的一部分即可匹配
    3. 通配符匹配："GET /api/*" 匹配所有 /api 下的路径
    
    Args:
        method: HTTP 请求方法
        path: 请求路径
        route_obj: FastAPI 路由对象
        
    Returns:
        bool: 是否在白名单中
    """
    # 获取路由所属的控制器实例
    # FastAPI 的路由存储在 route_obj.dependencies 或 route.endpoint 中
    endpoint = getattr(route_obj, "endpoint", None)
    if not endpoint:
        return False
    
    # 查找路由所属的控制器实例
    # 通过闭包查找 self 参数
    closure_vars = getattr(endpoint, "__closure__", None)
    if closure_vars:
        for cell in closure_vars:
            try:
                obj = cell.cell_contents
                # 检查是否有 SKIP_AUTH_ROUTES 属性
                if hasattr(obj, "SKIP_AUTH_ROUTES"):
                    skip_routes = obj.SKIP_AUTH_ROUTES
                    # 构造匹配路径：METHOD /path
                    route_pattern = f"{method.upper()} {path}"
                    for skip_pattern in skip_routes:
                        skip_pattern = skip_pattern.strip()
                        skip_upper = skip_pattern.upper()
                        
                        # 1. 精确匹配
                        if skip_upper == route_pattern.upper():
                            return True
                        
                        # 2. 路径包含匹配（如白名单 "POST /auth/login" 应匹配 "POST /api/auth/login"）
                        # 提取白名单中的路径部分
                        if " " in skip_pattern:
                            _, skip_path = skip_pattern.split(" ", 1)
                            # 实际路由路径等于白名单路径，或白名单路径是其段边界后缀时匹配
                            if path == skip_path or _suffix_match(path, skip_path):
                                return True
                        
                        # 3. 通配符匹配（如 "GET /api/*"）
                        if skip_pattern.endswith("*"):
                            prefix = skip_pattern[:-1].strip().upper()
                            if route_pattern.upper().startswith(prefix):
                                return True
            except ValueError:
                continue
    
    return False


def _is_in_global_whitelist(path: str) -> bool:
    """检查路径是否在全局白名单中
    
    Args:
        path: 请求路径
        
    Returns:
        bool: 是否在全局白名单中
    """
    for skip_path in SKIP_AUTH_PATHS:
        skip_path = skip_path.strip()
        # 精确匹配
        if path == skip_path:
            return True
        # 前缀匹配（如 "/docs" 匹配 "/docs" 和 "/docs/")
        if path.startswith(skip_path):
            return True
    return False


async def auth_middleware(request: Request, call_next):
    """全局认证中间件
    
    拦截所有请求，根据以下规则决定是否要求认证：
    1. 全局白名单（config/auth.py 中的 SKIP_AUTH_PATHS）
    2. 控制器白名单（控制器类中的 SKIP_AUTH_ROUTES）
    3. 装饰器标记（@skip_auth）
    
    如果请求需要认证但 Token 无效，返回 401 错误。
    如果 Token 有效，将当前用户信息注入到 request.state 中。
    
    Args:
        request: FastAPI 请求对象
        call_next: 下一个处理函数
        
    Returns:
        Response: HTTP 响应
    """
    # 如果全局认证未启用，直接放行
    if not AUTH_ENABLED:
        return await call_next(request)
    
    path = request.url.path
    method = request.method

    # 预检请求（OPTIONS）直接放行：
    # 浏览器跨域预检请求不会携带 Token，由外层的 CORS 中间件直接响应
    if method == "OPTIONS":
        return await call_next(request)

    # 1. 检查全局白名单
    if _is_in_global_whitelist(path):
        return await call_next(request)
    
    # 2. 检查控制器白名单和装饰器标记
    # 遍历所有路由（展平嵌套路由，兼容 FastAPI 0.141+），查找匹配的路由对象
    for route, route_prefix in iter_flat_routes(request.app.routes):
        try:
            # 检查路由是否匹配当前请求
            if not hasattr(route, "methods"):
                continue
            if method not in route.methods:
                continue

            route_path = getattr(route, "path", None)
            if not route_path:
                continue

            # 拼接模块前缀得到完整访问路径（如 /api + /auth/login）
            full_path = f"{route_prefix}{route_path}" if route_prefix else route_path

            # 简化路径匹配
            if not _paths_match(path, full_path):
                continue

            # 检查装饰器标记
            if _is_skip_auth_route(method, full_path, route):
                return await call_next(request)

            # 检查控制器白名单
            if _is_in_controller_whitelist(method, full_path, route):
                return await call_next(request)
        except (AttributeError, TypeError, ValueError):
            # 跳过无法解析的路由（如静态文件路由）
            continue
    
    # 3. 需要认证 - 验证 Token
    authorization = request.headers.get("Authorization")
    if not authorization:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "code": 401,
                "message": "未提供认证 Token，请先登录",
                "data": None,
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 提取 Token
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "code": 401,
                "message": "Token 格式错误，应为 Bearer <token>",
                "data": None,
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 验证 Token
    payload = decode_token(token)
    if not payload:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "code": 401,
                "message": "Token 无效或已过期，请重新登录",
                "data": None,
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 检查 Token 是否在黑名单中（需启用 TOKEN_BLACKLIST_ENABLED，支持 Redis/Memory 缓存）
    if await is_token_blacklisted(token):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "code": 401,
                "message": "Token 已失效，请重新登录",
                "data": None,
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Token 验证通过，注入用户信息到请求上下文
    request.state.current_user = CurrentUser(
        user_id=payload.get("user_id", 0),
        username=payload.get("username"),
        payload=payload,
    )
    
    # 放行请求
    return await call_next(request)


def _suffix_match(longer: str, shorter: str) -> bool:
    """判断 longer 是否以 shorter 为路径段后缀

    要求 shorter 以 / 开头，从而保证后缀天然位于路径段边界
    （如 /api/auth/login 匹配 /auth/login，而 /xuser/list 不会误匹配 /user/list）。

    Args:
        longer: 较长的路径（如 /api/auth/login）
        shorter: 较短的路径（如 /auth/login）

    Returns:
        bool: 是否为边界安全的后缀匹配
    """
    return (
        len(longer) > len(shorter)
        and shorter.startswith("/")
        and longer.endswith(shorter)
    )


def _paths_match(request_path: str, route_path: str) -> bool:
    """判断请求路径是否匹配路由路径

    支持：
    - 精确匹配：/auth/login == /auth/login
    - 路径参数：/user/123 匹配 /user/{user_id}
    - 模块前缀匹配：/api/auth/login 匹配 /auth/login（多模块模式，要求段边界）

    Args:
        request_path: 实际请求路径（如 /api/auth/login）
        route_path: 路由定义路径（如 /auth/login）

    Returns:
        bool: 是否匹配
    """
    # 精确匹配
    if request_path == route_path:
        return True

    # 路由路径是请求路径的后缀（多模块模式，如 /api/auth/login 匹配 /auth/login）
    if _suffix_match(request_path, route_path):
        return True

    # 请求路径是路由路径的后缀（反向情况较少见，但为了完整性也支持）
    if _suffix_match(route_path, request_path):
        return True

    # 路径参数匹配
    request_parts = request_path.strip("/").split("/")
    route_parts = route_path.strip("/").split("/")

    if len(request_parts) != len(route_parts):
        return False

    for req_part, route_part in zip(request_parts, route_parts):
        # 路由参数（如 {user_id}）匹配任何值
        if route_part.startswith("{") and route_part.endswith("}"):
            continue
        # 普通路径段必须精确匹配
        if req_part != route_part:
            return False

    return True
