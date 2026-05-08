"""
ThinkPython JWT 认证工具

本模块提供基于 JWT（JSON Web Token）的用户认证功能，包括：
- create_token(): 创建 JWT Token
- decode_token(): 解析并验证 JWT Token
- get_token_from_header(): 从 HTTP 请求头中提取 Token

JWT 认证流程：
1. 用户登录成功后，服务端调用 create_token() 生成 Token 返回给客户端
2. 客户端在后续请求中将 Token 放在 Authorization 请求头中
3. 服务端调用 decode_token() 验证 Token 有效性并获取用户信息
4. get_token_from_header() 用于从请求头中提取 Token 字符串

安全注意事项：
- JWT_SECRET 必须通过环境变量配置，切勿硬编码
- 生产环境务必使用强密钥（建议 32 位以上的随机字符串）
- Token 有过期时间，过期后需要重新登录

使用示例:
    from helpers.auth import create_token, decode_token, get_token_from_header
    
    # 登录成功后生成 Token
    token = create_token(user_id=1, extra_data={"role": "admin"})
    
    # 解析 Token
    payload = decode_token(token)
    if payload:
        user_id = payload["user_id"]
    
    # 从请求头获取 Token
    token = get_token_from_header("Bearer eyJhbGciOiJIUzI1NiIs...")
"""
import os
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# 从环境变量读取 JWT 配置，避免硬编码敏感信息
# JWT_SECRET: 签名密钥，用于加密和验证 Token
# JWT_ALGORITHM: 签名算法，默认 HS256（对称加密）
# JWT_EXPIRE_HOURS: Token 过期时间（小时），默认 24 小时
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-this-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))


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
