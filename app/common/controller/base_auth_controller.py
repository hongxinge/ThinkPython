"""
ThinkPython 需要登录认证的控制器基类

本模块定义了 BaseAuthController 基类，所有需要登录认证后才能访问的控制器
都应该继承此类。它提供了：
- SKIP_AUTH_ROUTES: 控制器级白名单，配置哪些接口免验证
- get_current_user(): 从请求上下文中获取当前用户信息
- 兼容旧版的 get_current_user_id() 方法

设计意图：
    ThinkPython 采用"默认认证 + 白名单跳过"的安全策略：
    - 默认所有接口都需要 JWT Token 认证
    - 通过三种方式跳过认证：
      1. 全局白名单（config/auth.py 中的 SKIP_AUTH_PATHS）
      2. 控制器级白名单（SKIP_AUTH_ROUTES 属性）
      3. 装饰器标记（@skip_auth）

继承关系：
    BaseController (core)
        └── BaseAuthController (common) - 增加认证辅助方法
                └── 你的业务控制器（继承 BaseAuthController）

使用方式：
    # 方式1: 控制器级白名单（最推荐）
    from core.base_controller import BaseController
    
    class AuthController(BaseController):
        # 只需配置一次，这些接口免验证
        SKIP_AUTH_ROUTES = ["POST /login", "POST /register"]
        
        def _setup_routes(self):
            # 免验证接口 - 无需任何装饰器
            @self.router.post("/login")
            async def login():
                pass
            
            # 需要认证的接口 - 也无需装饰器，自动拦截
            @self.router.get("/profile")
            async def profile():
                user = self.get_current_user()
                pass
    
    # 方式2: 装饰器标记单个接口
    from helpers.auth import skip_auth
    
    @self.router.post("/forgot-password")
    @skip_auth
    async def forgot_password():
        pass
"""
from typing import Any, List, Optional
from fastapi import Header, HTTPException, status, Request
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from core.base_controller import BaseController
from core.database import get_db
from core.cache import get_cache, set_cache
from app.common.service.auth_service import AuthService
from helpers.auth import CurrentUser


class BaseAuthController(BaseController):
    """需要登录认证的控制器基类
    
    继承此类后，控制器自动享有：
    - SKIP_AUTH_ROUTES 属性：声明哪些接口免验证（配置一次，全局生效）
    - get_current_user() 方法：从请求上下文获取当前用户
    - get_current_user_id() 方法：兼容旧版，获取当前用户 ID
    
    认证策略：
        默认所有接口都需要 JWT Token 认证，通过以下方式跳过：
        1. SKIP_AUTH_ROUTES: 控制器中配置的免验证路径列表
        2. @skip_auth 装饰器: 标记单个接口免验证
        3. 全局白名单: config/auth.py 中配置的系统级免验证路径
    
    SKIP_AUTH_ROUTES 配置格式：
        - 精确匹配: "POST /login"
        - 通配符: "GET /api/*"（匹配 GET /api/xxx 所有路径）
        - 方法可选: "/health"（匹配所有 HTTP 方法）
    
    使用示例:
        class UserController(BaseAuthController):
            # 免验证接口白名单
            SKIP_AUTH_ROUTES = [
                "POST /login",       # 登录接口免验证
                "POST /register",    # 注册接口免验证
            ]
            
            def _setup_routes(self):
                # 免验证接口 - 无需装饰器
                @self.router.post("/login")
                async def login():
                    pass
                
                # 需要认证的接口 - 自动拦截
                @self.router.get("/profile")
                async def get_profile(request: Request):
                    user = self.get_current_user(request)
                    return self.success(data={"user_id": user.user_id})
    """
    
    # 免验证路由白名单（格式: "METHOD /path" 或 "/path"）
    # 例如: ["POST /login", "POST /register", "GET /health"]
    SKIP_AUTH_ROUTES: List[str] = []
    
    def get_current_user(self, request: Request) -> Optional[CurrentUser]:
        """从请求上下文中获取当前登录用户信息
        
        当启用了全局认证中间件时，用户信息已自动注入到 request.state 中。
        此方法从 request.state 中提取用户信息。
        
        Args:
            request: FastAPI 请求对象
            
        Returns:
            Optional[CurrentUser]: 当前登录用户信息，未登录时返回 None
            
        使用示例:
            @self.router.get("/profile")
            async def get_profile(request: Request):
                user = self.get_current_user(request)
                return self.success(data={"user_id": user.user_id})
        """
        return getattr(request.state, "current_user", None)
    
    async def get_current_user_id(
        self,
        authorization: str,
        db: AsyncSession = Depends(get_db),
    ) -> int:
        """从请求头中验证 Token 并获取当前登录用户的 ID（兼容旧版）
        
        注意：
            推荐使用 get_current_user() 方法配合全局中间件使用。
            此方法保留是为了向后兼容，新项目建议使用中间件方案。
        
        Args:
            authorization: 请求头中的 Authorization 字段，格式为 "Bearer <token>"
            db: 数据库会话，自动注入
            
        Returns:
            int: 当前登录用户的 ID
            
        Raises:
            HTTPException: Token 无效或已过期时抛出 401 异常
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
