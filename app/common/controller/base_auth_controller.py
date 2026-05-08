"""
ThinkPython 公共基类控制器 - 需要登录认证

本模块定义了 BaseAuthController 基类，所有需要登录认证后才能访问的控制器
都应该继承此类。它提供了统一的 Token 验证逻辑。

设计意图：
    在多模块项目中，很多接口都需要用户登录后才能访问。
    例如：
    - admin 模块：后台管理接口，需要管理员登录
    - api 模块：用户个人中心接口，需要用户登录
    
    将这些接口共用的认证逻辑提取到 BaseAuthController 中，
    避免在每个控制器中重复编写 Token 验证代码。

继承关系：
    BaseController (core)
        └── BaseAuthController (common) - 增加 Token 验证
                └── 你的业务控制器（继承 BaseAuthController）

使用方式：
    # 在需要认证的控制器中继承 BaseAuthController
    from app.common.controller.base_auth_controller import BaseAuthController
    
    class ProfileController(BaseAuthController):
        def _setup_routes(self):
            @self.router.get("/profile", summary="获取个人信息")
            async def get_profile(
                authorization: str = Header(...),
                db: AsyncSession = Depends(get_db),
            ):
                user_id = await self.get_current_user_id(authorization, db)
                return self.success(data={"user_id": user_id})
"""
from typing import Any
from fastapi import Header, HTTPException, status
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from core.base_controller import BaseController
from core.database import get_db
from core.cache import get_cache, set_cache
from app.common.service.auth_service import AuthService


class BaseAuthController(BaseController):
    """需要登录认证的控制器基类
    
    继承此类后，子类控制器在每个接口中需要手动调用 self.get_current_user_id() 验证 Token。
    这是为了保持灵活性，让开发者可以根据需要选择哪些接口需要认证。
    
    认证流程：
    1. 从请求头 Authorization 中提取 Token（格式: "Bearer <token>"）
    2. 先检查缓存是否有该 Token 对应的用户（提升性能）
    3. 缓存未命中则验证 Token 签名和有效期
    4. Token 有效则返回 user_id，无效则返回 401
    
    使用示例:
        class ProfileController(BaseAuthController):
            def _setup_routes(self):
                @self.router.get("/profile", summary="获取个人信息")
                async def get_profile(
                    authorization: str = Header(...),
                    db: AsyncSession = Depends(get_db),
                ):
                    # 手动调用验证方法获取 user_id
                    user_id = await self.get_current_user_id(authorization, db)
                    return self.success(data={"user_id": user_id})
    """
    
    async def get_current_user_id(
        self,
        authorization: str,
        db: AsyncSession = Depends(get_db),
    ) -> int:
        """从请求头中验证 Token 并获取当前登录用户的 ID
        
        此方法需要在每个需要认证的接口中手动调用。
        
        Args:
            authorization: 请求头中的 Authorization 字段，格式为 "Bearer <token>"
            db: 数据库会话，自动注入
            
        Returns:
            int: 当前登录用户的 ID
            
        Raises:
            HTTPException: Token 无效或已过期时抛出 401 异常
            
        使用方式:
            @self.router.get("/profile")
            async def get_profile(
                authorization: str = Header(...),
                db: AsyncSession = Depends(get_db),
            ):
                user_id = await self.get_current_user_id(authorization, db)
        """
        # 从 Authorization 头中提取 Token
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="未提供认证 Token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token = authorization.split("Bearer ")[1]
        
        # 先检查缓存中是否有该 Token 对应的用户信息（提升性能）
        cache_key = f"auth:token:{token}"
        cached_user_id = await get_cache(cache_key)
        if cached_user_id:
            return int(cached_user_id)
        
        # 缓存未命中，验证 Token 签名和有效期
        auth_service = AuthService(db)
        payload = await auth_service.verify_token(token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token 无效或已过期",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user_id = payload.get("user_id")
        
        # 将 Token 与用户 ID 的映射关系缓存起来，提升后续请求的性能
        # 缓存时间设置为 24 小时，与 Token 有效期一致
        await set_cache(cache_key, str(user_id), ttl=86400)
        
        return user_id
