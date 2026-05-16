"""
ThinkPython 认证控制器 - 登录、注册、个人中心

本控制器演示 ThinkPython 框架的认证机制，使用"默认认证 + 白名单跳过"策略：
- 配置 SKIP_AUTH_ROUTES 声明免验证接口（登录、注册），配置一次即可
- 其余接口自动需要认证，无需逐个添加装饰器

访问路径（多模块模式下带 /api 前缀）：
- POST /auth/login              - 用户登录（免验证）
- POST /auth/register           - 用户注册（免验证）
- GET  /auth/profile            - 获取个人信息（需登录）
- PUT  /auth/profile            - 修改个人信息（需登录）
- POST /auth/change-password    - 修改密码（需登录）
- POST /auth/forgot-password    - 忘记密码（免验证，使用 @skip_auth 装饰器）

使用示例:
    # 登录（无需 Token）
    curl -X POST http://localhost:8000/api/auth/login \
      -H "Content-Type: application/json" \
      -d '{"username": "admin", "password": "123456"}'
    
    # 获取个人信息（需要 Token）
    curl -X GET http://localhost:8000/api/auth/profile \
      -H "Authorization: Bearer <token>"
"""
from typing import Optional
from pydantic import BaseModel, Field

from fastapi import Depends, Request

from core.base_controller import BaseController
from app.common.controller.base_auth_controller import BaseAuthController
from helpers.auth import skip_auth, require_auth, CurrentUser
from app.common.service.auth_service import AuthService
from core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.common.model.user_model import User


# ==============================
# 请求模型定义
# ==============================

class LoginRequest(BaseModel):
    """登录请求体"""
    username: str = Field(..., description="用户名", min_length=1, max_length=50)
    password: str = Field(..., description="密码", min_length=1, max_length=100)


class RegisterRequest(BaseModel):
    """注册请求体"""
    username: str = Field(..., description="用户名", min_length=2, max_length=50)
    password: str = Field(..., description="密码", min_length=6, max_length=100)
    email: Optional[str] = Field(None, description="邮箱地址")


class ChangePasswordRequest(BaseModel):
    """修改密码请求体"""
    old_password: str = Field(..., description="原密码", min_length=1)
    new_password: str = Field(..., description="新密码", min_length=6, max_length=100)


class UpdateProfileRequest(BaseModel):
    """修改个人信息请求体"""
    email: Optional[str] = Field(None, description="邮箱地址")
    nickname: Optional[str] = Field(None, description="昵称", max_length=50)


class ForgotPasswordRequest(BaseModel):
    """忘记密码请求体"""
    username: str = Field(..., description="用户名", min_length=1)
    email: str = Field(..., description="注册邮箱")


class AuthController(BaseAuthController):
    """认证控制器 - 演示"默认认证 + 白名单跳过"策略
    
    本控制器展示了 ThinkPython 框架最简洁的认证方式：
    1. SKIP_AUTH_ROUTES: 配置一次，声明哪些接口免验证
    2. 其余接口自动需要认证，中间件自动拦截
    3. @skip_auth 装饰器: 用于单个接口的细粒度控制
    
    对比旧方案：
    - 旧方案: 每个免验证接口加 @public_route，每个需验证接口加 @require_auth
    - 新方案: 配置 SKIP_AUTH_ROUTES 即可，其余全自动
    """
    
    # ==============================
    # 免验证接口白名单（方式2：控制器级配置）
    # ==============================
    # 只需在这里配置一次，以下接口免验证
    # 格式: "HTTP方法 /路由路径"（路由路径是 router.post("/xxx") 中定义的路径）
    SKIP_AUTH_ROUTES = [
        "POST /auth/login",           # 登录接口免验证
        "POST /auth/register",        # 注册接口免验证
        "POST /auth/forgot-password", # 忘记密码免验证
    ]
    
    def __init__(self):
        super().__init__()
        self._setup_routes()
    
    def _setup_routes(self):
        """初始化路由配置"""
        
        # ==============================
        # 免验证接口（在 SKIP_AUTH_ROUTES 中已配置，无需装饰器）
        # ==============================
        
        @self.router.post("/auth/login", summary="用户登录", response_model=dict)
        async def login(
            data: LoginRequest,
            db: AsyncSession = Depends(get_db),
        ):
            """用户登录接口
            
            验证用户名和密码，登录成功后返回 JWT Token。
            此接口在 SKIP_AUTH_ROUTES 中配置为免验证，无需任何装饰器。
            
            Args:
                data: 登录请求数据（用户名和密码）
                db: 数据库会话（自动注入）
                
            Returns:
                Dict: 登录成功返回 Token 和用户信息
            """
            auth_service = AuthService(db)
            result = await auth_service.login(data.username, data.password)
            
            if not result:
                return self.error(message="用户名或密码错误", code=401)
            
            return self.success(
                data={
                    "token": result["token"],
                    "user_id": result["user"].id,
                    "username": result["user"].username,
                },
                message="登录成功",
            )
        
        @self.router.post("/auth/register", summary="用户注册", response_model=dict)
        @skip_auth
        async def register(
            data: RegisterRequest,
            db: AsyncSession = Depends(get_db),
        ):
            """用户注册接口
            
            创建新用户账号，注册成功后返回用户信息。
            此接口在 SKIP_AUTH_ROUTES 中配置为免验证，无需任何装饰器。
            """
            # 检查用户名是否已存在
            stmt = select(User).where(User.username == data.username)
            result = await db.execute(stmt)
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                return self.error(message="用户名已存在", code=400)
            
            # 创建新用户
            auth_service = AuthService(db)
            new_user = User(
                username=data.username,
                password=auth_service.hash_password(data.password),
                email=data.email,
                status=1,
            )
            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)
            
            return self.success(
                data={
                    "user_id": new_user.id,
                    "username": new_user.username,
                },
                message="注册成功",
            )
        
        # ==============================
        # 免验证接口（方式3：装饰器标记）
        # ==============================
        
        @self.router.post("/auth/forgot-password", summary="忘记密码", response_model=dict)
        @skip_auth
        async def forgot_password(
            data: ForgotPasswordRequest,
            db: AsyncSession = Depends(get_db),
        ):
            """忘记密码接口
            
            验证用户名和邮箱，发送重置密码邮件。
            此接口使用 @skip_auth 装饰器标记为免验证。
            """
            # 检查用户是否存在且邮箱匹配
            stmt = select(User).where(
                User.username == data.username,
                User.email == data.email,
            )
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                return self.error(message="用户名或邮箱不正确", code=400)
            
            # TODO: 发送重置密码邮件
            # await send_reset_password_email(user.email, user.id)
            
            return self.success(message="重置密码邮件已发送，请查收")
        
        # ==============================
        # 需要认证的接口（自动拦截，无需装饰器）
        # ==============================
        
        @self.router.get("/auth/profile", summary="获取个人信息", response_model=dict)
        async def get_profile(
            request: Request,
            db: AsyncSession = Depends(get_db),
        ):
            """获取当前登录用户的个人信息
            
            此接口需要登录才能访问，认证中间件自动拦截未登录请求。
            通过 self.get_current_user(request) 获取当前用户信息。
            """
            from app.common.controller.base_auth_controller import BaseAuthController
            
            # 获取当前登录用户（由中间件自动注入）
            user = self.get_current_user(request)
            if not user:
                return self.error(message="未登录", code=401)
            
            # 从数据库查询用户详细信息
            stmt = select(User).where(User.id == user.user_id)
            result = await db.execute(stmt)
            db_user = result.scalar_one_or_none()
            
            if not db_user:
                return self.error(message="用户不存在", code=404)
            
            return self.success(data={
                "user_id": db_user.id,
                "username": db_user.username,
                "email": db_user.email,
                "nickname": db_user.nickname,
                "status": db_user.status,
                "created_at": db_user.created_at.isoformat() if db_user.created_at else None,
            })
        
        @self.router.put("/auth/profile", summary="修改个人信息", response_model=dict)
        async def update_profile(
            data: UpdateProfileRequest,
            request: Request,
            db: AsyncSession = Depends(get_db),
        ):
            """修改当前登录用户的个人信息
            
            此接口需要登录才能访问，通过中间件自动获取当前用户。
            只允许修改自己的信息，无需额外判断权限。
            """
            # 获取当前登录用户
            user = self.get_current_user(request)
            if not user:
                return self.error(message="未登录", code=401)
            
            # 查询当前用户
            stmt = select(User).where(User.id == user.user_id)
            result = await db.execute(stmt)
            db_user = result.scalar_one_or_none()
            
            if not db_user:
                return self.error(message="用户不存在", code=404)
            
            # 更新允许的字段
            if data.email is not None:
                db_user.email = data.email
            if data.nickname is not None:
                db_user.nickname = data.nickname
            
            await db.commit()
            await db.refresh(db_user)
            
            return self.success(
                data={
                    "user_id": db_user.id,
                    "username": db_user.username,
                    "email": db_user.email,
                    "nickname": db_user.nickname,
                },
                message="修改成功",
            )
        
        @self.router.post("/auth/change-password", summary="修改密码", response_model=dict)
        async def change_password(
            data: ChangePasswordRequest,
            request: Request,
            db: AsyncSession = Depends(get_db),
        ):
            """修改当前登录用户的密码
            
            需要验证原密码是否正确，验证通过后更新为新密码。
            此接口需要登录才能访问。
            """
            # 获取当前登录用户
            user = self.get_current_user(request)
            if not user:
                return self.error(message="未登录", code=401)
            
            # 查询当前用户
            stmt = select(User).where(User.id == user.user_id)
            result = await db.execute(stmt)
            db_user = result.scalar_one_or_none()
            
            if not db_user:
                return self.error(message="用户不存在", code=404)
            
            # 验证原密码
            auth_service = AuthService(db)
            if not auth_service._verify_password(data.old_password, db_user.password):
                return self.error(message="原密码不正确", code=400)
            
            # 更新密码
            db_user.password = auth_service.hash_password(data.new_password)
            await db.commit()
            
            return self.success(message="密码修改成功")
