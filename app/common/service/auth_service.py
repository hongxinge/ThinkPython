"""
ThinkPython 公共认证服务

本模块提供跨模块共用的认证业务逻辑，包括用户登录验证、密码校验、Token 管理等。

设计意图：
    在多模块项目中，admin 模块和 api 模块都需要用户认证功能。
    例如：
    - admin 模块：管理员登录后台
    - api 模块：用户登录获取 Token
    
    将认证逻辑放在 common/service 中，避免在不同模块中重复实现相同的认证逻辑。

使用方式：
    在任何模块的控制器中引入并使用：
        from app.common.service.auth_service import AuthService
        
        # 创建认证服务实例
        auth_service = AuthService(db)
        
        # 验证用户登录
        user = await auth_service.login("username", "password")
        
        # 验证 Token
        payload = await auth_service.verify_token(token)

架构分层：
    Controller -> AuthService (common) -> User Model (common) -> Database
"""
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.base_service import BaseService
from app.common.model.user_model import User
from helpers.auth import create_token, decode_token
from helpers.common import md5


class AuthService(BaseService):
    """公共认证服务 - 处理用户认证相关的业务逻辑
    
    本服务类提供统一的认证功能，包括：
    - 用户名密码登录验证
    - Token 生成和验证
    - 密码加密和校验
    - 用户状态检查
    
    Attributes:
        model_class: 关联到公共 User 模型
    """
    
    def __init__(self, db: AsyncSession):
        """初始化认证服务
        
        Args:
            db: 数据库会话，通过 FastAPI 依赖注入传入
        """
        super().__init__(db)
        # 关联到公共 User 模型，所有认证操作都基于此模型
        self.model_class = User
    
    async def login(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """用户登录验证
        
        验证用户名和密码是否正确，如果验证通过则生成 Token。
        
        Args:
            username: 用户名
            password: 明文密码
            
        Returns:
            Optional[Dict[str, Any]]: 登录成功返回用户信息和 Token，失败返回 None
            返回格式:
                {
                    "user": {User 模型实例},
                    "token": "JWT Token 字符串"
                }
                
        使用示例:
            auth_service = AuthService(db)
            result = await auth_service.login("admin", "123456")
            if result:
                print(f"登录成功，Token: {result['token']}")
            else:
                print("用户名或密码错误")
        """
        # 通过用户名查询用户
        stmt = select(User).where(User.username == username)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        
        # 用户不存在或密码不匹配
        if not user or not self._verify_password(password, user.password):
            return None
        
        # 检查用户状态是否为启用
        if user.status != 1:
            return None
        
        # 生成 JWT Token
        token = create_token(
            user_id=user.id,
            extra_data={"username": user.username},
        )
        
        return {
            "user": user,
            "token": token,
        }
    
    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证 JWT Token 的有效性
        
        解析 Token 并检查是否过期，如果 Token 有效则返回载荷数据。
        
        Args:
            token: JWT Token 字符串
            
        Returns:
            Optional[Dict[str, Any]]: Token 有效返回载荷数据，无效返回 None
            载荷数据包含:
                - user_id: 用户ID
                - username: 用户名
                - exp: Token 过期时间
                - iat: Token 签发时间
                
        使用示例:
            auth_service = AuthService(db)
            payload = await auth_service.verify_token("eyJhbGciOi...")
            if payload:
                print(f"用户ID: {payload['user_id']}")
            else:
                print("Token 无效或已过期")
        """
        payload = decode_token(token)
        if not payload:
            return None
        
        # 可选：从数据库检查用户是否仍然存在且状态正常
        user = await self.get_by_id(payload.get("user_id"))
        if not user or user.status != 1:
            return None
        
        return payload
    
    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """校验密码
        
        将明文密码进行哈希处理后与数据库中的哈希值比较。
        
        Args:
            plain_password: 用户输入的明文密码
            hashed_password: 数据库中存储的哈希密码
            
        Returns:
            bool: 密码匹配返回 True，不匹配返回 False
            
        注意：
            生产环境建议使用 bcrypt 等更安全的加密算法。
            这里使用 MD5 仅为示例，实际项目中应替换为 bcrypt。
        """
        return md5(plain_password) == hashed_password
    
    def hash_password(self, password: str) -> str:
        """对密码进行哈希加密
        
        Args:
            password: 明文密码
            
        Returns:
            str: 加密后的密码哈希值
            
        注意：
            生产环境建议使用 bcrypt 等更安全的加密算法。
            这里使用 MD5 仅为示例，实际项目中应替换为 bcrypt。
        """
        return md5(password)
