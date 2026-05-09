"""
ThinkPython JWT 认证工具

本模块提供基于 JWT（JSON Web Token）的用户认证功能，包括：
- create_token(): 创建 JWT Token
- decode_token(): 解析并验证 JWT Token
- get_token_from_header(): 从 HTTP 请求头中提取 Token
- skip_auth: 装饰器，标记单个接口免验证
- require_auth: FastAPI 依赖注入，自动验证 Token 并返回当前用户信息
- CurrentUser: 当前登录用户信息模型

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
- Token 有过期时间，过期后需要重新登录

使用示例:
    from helpers.auth import create_token, decode_token, skip_auth, require_auth, CurrentUser
    
    # 登录成功后生成 Token
    token = create_token(user_id=1, extra_data={"role": "admin"})
    
    # 解析 Token
    payload = decode_token(token)
    if payload:
        user_id = payload["user_id"]
    
    # 从请求头获取 Token
    token = get_token_from_header("Bearer eyJhbGciOiJIUzI1NiIs...")
    
    # 方式3: 装饰器标记免验证
    @router.post("/login")
    @skip_auth
    async def login():
        pass
    
    # 需要验证的接口（自动注入当前用户）
    @router.get("/profile")
    async def profile(user: CurrentUser = Depends(require_auth)):
        return {"user_id": user.user_id}
"""
import os
import jwt
from functools import wraps
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Header, HTTPException, Depends, Request, status
from pydantic import BaseModel

# 从环境变量读取 JWT 配置，避免硬编码敏感信息
# JWT_SECRET: 签名密钥，用于加密和验证 Token
# JWT_ALGORITHM: 签名算法，默认 HS256（对称加密）
# JWT_EXPIRE_HOURS: Token 过期时间（小时），默认 24 小时
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-this-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))


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


def create_token(user_id: int, extra_data: Optional[Dict] = None) -> str:
    """创建 JWT Token
    
    将用户 ID 和附加信息编码为 JWT Token，包含过期时间和签发时间。
    Token 格式：Header.Payload.Signature
    
    Args:
        user_id: 用户的唯一标识 ID
        extra_data: 需要额外存储在 Token 中的数据（如角色、权限等）
        
    Returns:
        str: JWT Token 字符串，可直接返回给客户端
        
    Token Payload 结构:
        {
            "user_id": 1,              # 用户 ID
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
    payload = {
        "user_id": user_id,  # 用户标识
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS),  # 过期时间（UTC）
        "iat": datetime.utcnow(),  # 签发时间（UTC）
    }
    # 合并额外数据到 payload 中
    if extra_data:
        payload.update(extra_data)
    # 使用密钥和算法对 payload 进行签名编码
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """解析并验证 JWT Token
    
    验证 Token 的签名和过期时间，返回解析后的 payload 数据。
    如果 Token 无效或已过期，返回 None。
    
    Args:
        token: JWT Token 字符串
        
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
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
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
