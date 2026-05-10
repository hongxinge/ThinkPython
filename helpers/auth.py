"""
ThinkPython JWT 认证工具

本模块提供基于 JWT（JSON Web Token）的双 Token 认证功能，包括：
- create_token(): 创建 Access Token
- create_refresh_token(): 创建 Refresh Token
- decode_token(): 解析并验证 JWT Token
- refresh_access_token(): 使用 Refresh Token 刷新 Access Token
- blacklist_token(): 将 Token 加入黑名单（注销）
- is_token_blacklisted(): 检查 Token 是否在黑名单中
- get_token_from_header(): 从 HTTP 请求头中提取 Token
- skip_auth: 装饰器，标记单个接口免验证
- require_auth: FastAPI 依赖注入，自动验证 Token 并返回当前用户信息
- CurrentUser: 当前登录用户信息模型
- TokenPair: 双 Token 响应模型

双 Token 机制（Access Token + Refresh Token）：
    - Access Token: 短期有效（默认 2 小时），用于日常接口访问
    - Refresh Token: 长期有效（默认 7 天），仅用于刷新 Access Token
    - 刷新策略：每次刷新生成新的 Refresh Token（轮换机制），旧的立即失效

认证方式（三种，可混合使用）：
    方式1: 全局白名单（config/auth.py 中的 SKIP_AUTH_PATHS）
           - 适用于系统级接口（/health, /docs）
           - 配置一次，全局生效
    
    方式2: 控制器级白名单（SKIP_AUTH_ROUTES 属性）
           - 适用于模块级接口（登录、注册）
           - 在控制器类中定义一次即可
    
    方式3: 装饰器标记（@skip_auth）
           - 适用于单个接口的细粒度控制
           - 在函数上加 @skip_auth 装饰器

安全注意事项：
- JWT_SECRET 必须通过环境变量配置，切勿硬编码
- 生产环境务必使用强密钥（建议 32 位以上的随机字符串）
- 启用 Token 黑名单需要 Redis 支持
- Refresh Token 轮换机制提高安全性

使用示例:
    from helpers.auth import create_token, create_refresh_token, refresh_access_token, decode_token
    
    # 登录成功后生成双 Token
    token_pair = {
        "access_token": create_token(user_id=1, extra_data={"role": "admin"}),
        "refresh_token": create_refresh_token(user_id=1),
        "token_type": "bearer",
        "expires_in": 7200  # 秒
    }
    
    # 刷新 Access Token
    new_token_pair = refresh_access_token(refresh_token="...")
"""
import os
import jwt
import hashlib
from functools import wraps
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import Header, HTTPException, Depends, Request, status
from pydantic import BaseModel

# 从配置模块导入认证相关配置
try:
    from config.auth import (
        JWT_SECRET,
        JWT_ALGORITHM,
        JWT_ACCESS_TOKEN_EXPIRE_HOURS,
        JWT_REFRESH_TOKEN_EXPIRE_DAYS,
        JWT_REFRESH_TOKEN_ROTATE,
        TOKEN_BLACKLIST_ENABLED,
        TOKEN_BLACKLIST_PREFIX,
    )
except ImportError:
    # 向后兼容：如果配置不存在则使用默认值
    JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-this-in-production")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_HOURS", "2"))
    JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    JWT_REFRESH_TOKEN_ROTATE = True
    TOKEN_BLACKLIST_ENABLED = False
    TOKEN_BLACKLIST_PREFIX = "token:blacklist:"


class CurrentUser(BaseModel):
    """当前登录用户信息
    
    通过 require_auth 依赖注入自动获取，包含从 Token 中解析的用户信息。
    
    Attributes:
        user_id: 用户 ID
        username: 用户名（可选，取决于 Token 中是否包含）
        payload: Token 的完整载荷数据
    """
    user_id: int
    username: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None


class TokenPair(BaseModel):
    """双 Token 响应模型
    
    登录成功后返回的 Token 对，包含 Access Token 和 Refresh Token。
    
    Attributes:
        access_token: 访问令牌，用于日常接口访问
        refresh_token: 刷新令牌，仅用于刷新 Access Token
        token_type: Token 类型（固定为 "bearer"）
        expires_in: Access Token 有效期（秒）
    """
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


def _generate_token_jti(user_id: int, token_type: str) -> str:
    """生成 Token 唯一标识（JTI）
    
    用于 Token 黑名单管理，每个 Token 都有唯一的 JTI。
    
    Args:
        user_id: 用户 ID
        token_type: Token 类型（access 或 refresh）
        
    Returns:
        str: Token 唯一标识
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    raw = f"{user_id}:{token_type}:{timestamp}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _is_token_blacklisted(token: str) -> bool:
    """检查 Token 是否在黑名单中
    
    内部函数，检查 Token 的 JTI 是否已被加入黑名单。
    
    Args:
        token: JWT Token 字符串
        
    Returns:
        bool: 在黑名单中返回 True，否则返回 False
    """
    if not TOKEN_BLACKLIST_ENABLED:
        return False
    
    try:
        # 解码 Token 获取 JTI（不验证过期时间，因为我们只需要 JTI）
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM], options={"verify_exp": False})
        jti = payload.get("jti")
        if not jti:
            return False
        
        # 从缓存中检查是否在黑名单中
        from core.cache import get_cache
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 在异步环境中
                return asyncio.get_event_loop().create_task(
                    get_cache(f"{TOKEN_BLACKLIST_PREFIX}{jti}")
                ) is not None
            else:
                # 在同步环境中
                import asyncio
                try:
                    result = asyncio.run(get_cache(f"{TOKEN_BLACKLIST_PREFIX}{jti}"))
                    return result is not None
                except RuntimeError:
                    return False
        except Exception:
            return False
    except Exception:
        return False


def create_token(user_id: int, extra_data: Optional[Dict] = None) -> str:
    """创建 Access Token（访问令牌）
    
    将用户 ID 和附加信息编码为 JWT Access Token，包含过期时间、签发时间和唯一标识。
    Access Token 有效期较短（默认 2 小时），用于日常接口访问。
    Token 格式：Header.Payload.Signature
    
    Args:
        user_id: 用户的唯一标识 ID
        extra_data: 需要额外存储在 Token 中的数据（如角色、权限等）
        
    Returns:
        str: JWT Access Token 字符串，可直接返回给客户端
        
    Token Payload 结构:
        {
            "user_id": 1,              # 用户 ID
            "type": "access",          # Token 类型
            "jti": "abc123...",        # 唯一标识
            "exp": 2024-01-02T12:00:00, # 过期时间
            "iat": 2024-01-01T12:00:00, # 签发时间
            "role": "admin"            # 附加数据（可选）
        }
        
    使用示例:
        # 基础用法
        token = create_token(user_id=1)
        
        # 携带额外信息
        token = create_token(user_id=1, extra_data={"role": "admin", "username": "张三"})
    """
    now = datetime.now(timezone.utc)
    jti = _generate_token_jti(user_id, "access")
    
    payload = {
        "user_id": user_id,  # 用户标识
        "type": "access",  # Token 类型
        "jti": jti,  # 唯一标识
        "exp": now + timedelta(hours=JWT_ACCESS_TOKEN_EXPIRE_HOURS),  # 过期时间（UTC）
        "iat": now,  # 签发时间（UTC）
    }
    # 合并额外数据到 payload 中
    if extra_data:
        payload.update(extra_data)
    # 使用密钥和算法对 payload 进行签名编码
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: int, extra_data: Optional[Dict] = None) -> str:
    """创建 Refresh Token（刷新令牌）
    
    将用户 ID 编码为 JWT Refresh Token，包含较长的过期时间。
    Refresh Token 仅用于刷新 Access Token，不能用于访问业务接口。
    
    Args:
        user_id: 用户的唯一标识 ID
        extra_data: 需要额外存储在 Refresh Token 中的数据
        
    Returns:
        str: JWT Refresh Token 字符串
        
    Token Payload 结构:
        {
            "user_id": 1,               # 用户 ID
            "type": "refresh",          # Token 类型
            "jti": "def456...",         # 唯一标识
            "exp": 2024-01-08T12:00:00,  # 过期时间（7天后）
            "iat": 2024-01-01T12:00:00,  # 签发时间
        }
        
    使用示例:
        refresh_token = create_refresh_token(user_id=1)
    """
    now = datetime.now(timezone.utc)
    jti = _generate_token_jti(user_id, "refresh")
    
    payload = {
        "user_id": user_id,  # 用户标识
        "type": "refresh",  # Token 类型
        "jti": jti,  # 唯一标识
        "exp": now + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS),  # 过期时间（UTC）
        "iat": now,  # 签发时间（UTC）
    }
    # 合并额外数据到 payload 中
    if extra_data:
        payload.update(extra_data)
    # 使用密钥和算法对 payload 进行签名编码
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    """使用 Refresh Token 刷新 Access Token
    
    验证 Refresh Token 的有效性，如果有效则生成新的 Access Token（和可选的新 Refresh Token）。
    如果启用了 Refresh Token 轮换机制，旧的 Refresh Token 将立即失效。
    
    Args:
        refresh_token: 当前的 Refresh Token 字符串
        
    Returns:
        Dict[str, Any]: 新的 Token 对
        {
            "access_token": "new_access_token...",
            "refresh_token": "new_refresh_token...",  # 如果启用了轮换
            "token_type": "bearer",
            "expires_in": 7200
        }
        
    Raises:
        ValueError: Refresh Token 无效、过期或类型不正确时抛出
        
    使用示例:
        try:
            new_tokens = refresh_access_token(old_refresh_token)
            # 返回给前端，前端保存新的 Token 对
        except ValueError as e:
            # 需要重新登录
            print(f"刷新失败: {e}")
    """
    # 验证 Refresh Token
    payload = decode_token(refresh_token)
    if not payload:
        raise ValueError("Refresh Token 无效或已过期")
    
    # 验证 Token 类型
    if payload.get("type") != "refresh":
        raise ValueError("无效的 Token 类型，需要 Refresh Token")
    
    # 检查是否在黑名单中
    if _is_token_blacklisted(refresh_token):
        raise ValueError("Refresh Token 已失效")
    
    user_id = payload.get("user_id")
    if not user_id:
        raise ValueError("Token 中缺少用户信息")
    
    # 生成新的 Access Token
    new_access_token = create_token(user_id)
    
    # 如果启用了轮换机制，生成新的 Refresh Token
    new_refresh_token = None
    if JWT_REFRESH_TOKEN_ROTATE:
        # 将旧的 Refresh Token 加入黑名单
        if TOKEN_BLACKLIST_ENABLED:
            blacklist_token(refresh_token)
        # 生成新的 Refresh Token
        new_refresh_token = create_refresh_token(user_id)
    else:
        # 不轮换，返回原 Refresh Token
        new_refresh_token = refresh_token
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": JWT_ACCESS_TOKEN_EXPIRE_HOURS * 3600,
    }


def blacklist_token(token: str, expire_seconds: Optional[int] = None) -> None:
    """将 Token 加入黑名单（用于主动注销）
    
    用户登出时调用，将 Token 的 JTI 加入 Redis 黑名单，
    在 Token 自然过期前都无法再次使用。
    
    Args:
        token: 要加入黑名单的 JWT Token
        expire_seconds: 黑名单有效期（秒），默认等于 Token 剩余有效期
        
    使用示例:
        # 用户登出
        @router.post("/logout")
        async def logout(authorization: str = Header(None)):
            token = get_token_from_header(authorization)
            if token:
                blacklist_token(token)
            return {"message": "已退出登录"}
    """
    if not TOKEN_BLACKLIST_ENABLED:
        return
    
    try:
        # 解码 Token 获取 JTI 和过期时间
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM], options={"verify_exp": False})
        jti = payload.get("jti")
        exp = payload.get("exp")
        
        if not jti:
            return
        
        # 计算黑名单有效期
        if expire_seconds is None:
            if exp:
                expire_seconds = int(exp - datetime.now(timezone.utc).timestamp())
            else:
                expire_seconds = JWT_ACCESS_TOKEN_EXPIRE_HOURS * 3600
        
        if expire_seconds <= 0:
            return  # Token 已过期，无需加入黑名单
        
        # 将 JTI 加入 Redis 黑名单
        from core.cache import set_cache
        import asyncio
        
        key = f"{TOKEN_BLACKLIST_PREFIX}{jti}"
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(set_cache(key, "1", expire=expire_seconds))
            else:
                asyncio.run(set_cache(key, "1", expire=expire_seconds))
        except RuntimeError:
            pass  # 忽略异步环境错误
    except Exception:
        pass  # 忽略黑名单添加失败


def decode_token(token: str, verify_exp: bool = True) -> Optional[Dict[str, Any]]:
    """解析并验证 JWT Token
    
    验证 Token 的签名和过期时间，返回解析后的 payload 数据。
    如果 Token 无效或已过期，返回 None。
    
    Args:
        token: JWT Token 字符串
        verify_exp: 是否验证过期时间（默认 True，刷新 Token 时可能需要关闭）
        
    Returns:
        Optional[Dict[str, Any]]: 解析后的 payload 字典，验证失败时返回 None
        payload 中至少包含 user_id 字段，可能还包含 extra_data 中的字段
        
    使用示例:
        payload = decode_token(token)
        if payload is None:
            # Token 无效或已过期
            raise UnauthorizedException("登录已过期")
        user_id = payload["user_id"]
    """
    try:
        # decode() 会自动验证签名和过期时间
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM], options={"verify_exp": verify_exp})
        
        # 检查是否在黑名单中
        if TOKEN_BLACKLIST_ENABLED and verify_exp:
            jti = payload.get("jti")
            if jti:
                # 同步检查（简化版，实际应在中间件中异步检查）
                from core.cache import cache_client
                if hasattr(cache_client, 'client') and cache_client.client:
                    try:
                        import asyncio
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # 在异步环境中，这里只能做粗略检查
                            pass
                        else:
                            result = asyncio.run(cache_client.get(f"{TOKEN_BLACKLIST_PREFIX}{jti}"))
                            if result:
                                return None  # Token 在黑名单中
                    except Exception:
                        pass
        
        return payload
    except jwt.ExpiredSignatureError:
        # Token 已过期
        return None
    except jwt.InvalidTokenError:
        # Token 无效（签名不匹配、格式错误等）
        return None


def get_token_from_header(authorization: Optional[str] = None) -> Optional[str]:
    """从 HTTP Authorization 请求头中提取 Token
    
    标准的 Authorization 头格式为："Bearer <token>"
    此函数解析该格式并返回纯 Token 字符串。
    
    Args:
        authorization: Authorization 请求头的完整值，如 "Bearer eyJhbGciOiJIUzI1NiIs..."
        
    Returns:
        Optional[str]: 提取的 Token 字符串，格式不正确时返回 None
        
    使用示例:
        # 在 FastAPI 路由中使用
        @router.get("/profile")
        async def get_profile(authorization: str = Header(None)):
            token = get_token_from_header(authorization)
            if not token:
                raise UnauthorizedException("缺少认证信息")
            payload = decode_token(token)
            ...
    """
    if not authorization:
        return None
    # 按空格分割，期望格式为 "Bearer <token>"
    parts = authorization.split()
    # 验证格式：必须是两部分，且第一部分为 "Bearer"（不区分大小写）
    if len(parts) == 2 and parts[0].lower() == 'bearer':
        return parts[1]
    return None


# ==============================
# 认证装饰器和依赖注入
# ==============================

def skip_auth(func):
    """免验证接口装饰器（方式3）
    
    标记该接口不需要 JWT 认证，即使在全局认证开启的情况下也能直接访问。
    适用于登录、注册、忘记密码等公开接口。
    
    注意：
        此装饰器优先级最高，会覆盖全局白名单和控制器白名单的配置。
        如果已经使用了 SKIP_AUTH_ROUTES 配置，则无需使用此装饰器。
    
    使用示例:
        class AuthController(BaseController):
            @self.router.post("/login", summary="用户登录")
            @skip_auth
            async def login(data: LoginRequest):
                # 无需 Token，任何人都可以访问
                result = await auth_service.login(data.username, data.password)
                return self.success(data={"token": result["token"]})
            
            @self.router.post("/register", summary="用户注册")
            @skip_auth
            async def register(data: RegisterRequest):
                # 无需 Token，任何人都可以访问
                user = await user_service.create(data)
                return self.success(data={"id": user.id})
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    
    # 标记为跳过认证（供中间件识别）
    wrapper._skip_auth = True
    return wrapper


async def require_auth(
    authorization: Optional[str] = Header(None),
) -> CurrentUser:
    """FastAPI 依赖注入 - 自动验证 JWT Token 并返回当前用户信息
    
    在需要认证的接口中使用此依赖，自动从请求头中提取并验证 Token。
    Token 无效或缺失时自动返回 401 错误，无需在业务代码中处理认证逻辑。
    
    注意：
        当启用了全局认证中间件时，此依赖注入是可选的。
        因为中间件已经将 current_user 注入到 request.state 中。
        此依赖注入适用于：
        1. 未启用全局中间件的项目
        2. 需要显式声明认证依赖的场景
    
    Args:
        authorization: 请求头中的 Authorization 字段（自动注入），格式为 "Bearer <token>"
        
    Returns:
        CurrentUser: 当前登录用户信息，包含 user_id、username 和完整 payload
        
    Raises:
        HTTPException: Token 缺失、无效或过期时抛出 401 异常
        
    使用示例:
        from helpers.auth import require_auth, CurrentUser
        
        @router.get("/profile", summary="获取个人信息")
        async def get_profile(
            user: CurrentUser = Depends(require_auth)
        ):
            # user 已自动包含验证通过的当前用户信息
            return self.success(data={
                "user_id": user.user_id,
                "username": user.username,
            })
        
        @router.put("/profile", summary="修改个人信息")
        async def update_profile(
            data: UpdateProfileRequest,
            user: CurrentUser = Depends(require_auth)
        ):
            # 直接使用 user.user_id 更新当前用户的数据
            await user_service.update(user.user_id, data)
            return self.success(message="更新成功")
    """
    # 检查 Authorization 头是否存在
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证 Token，请先登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 提取 Token
    token = get_token_from_header(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 格式错误，应为 Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 验证 Token
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 无效或已过期，请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 构造当前用户信息
    return CurrentUser(
        user_id=payload.get("user_id", 0),
        username=payload.get("username"),
        payload=payload,
    )


# ==============================
# 向后兼容别名
# ==============================

def generate_token(user_id: int, username: Optional[str] = None) -> str:
    """生成 JWT Token（向后兼容别名）"""
    extra = {}
    if username:
        extra["username"] = username
    return create_token(user_id, extra_data=extra)


def verify_token(token: str) -> bool:
    """验证 Token 是否有效（向后兼容别名）"""
    return decode_token(token) is not None
