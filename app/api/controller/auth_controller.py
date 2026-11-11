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
from typing import List, Optional
from pydantic import BaseModel, Field

from fastapi import Depends, Request

from core.base_controller import BaseController
from core.schema import ApiResponse, EmptyData
from app.common.controller.base_auth_controller import BaseAuthController
from helpers.auth import (
    CurrentUser,
    blacklist_token,
    get_token_from_header,
    refresh_access_token,
    require_auth,
    skip_auth,
)
from config.auth import TOKEN_BLACKLIST_ENABLED
from config.permissions import DEFAULT_ROLE, get_role_permissions
from helpers.validate import is_email
from app.common.service.auth_service import AuthService
from core.database import get_db
from core.error_codes import ErrorCode
from core.token_state import bump_token_version
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
    email: str = Field(..., description="邮箱地址", min_length=5, max_length=100)


class ChangePasswordRequest(BaseModel):
    """修改密码请求体"""
    old_password: str = Field(..., description="原密码", min_length=1)
    new_password: str = Field(..., description="新密码", min_length=6, max_length=100)


class RefreshTokenRequest(BaseModel):
    """刷新 Token 请求体"""
    refresh_token: str = Field(..., description="登录时下发的 refresh_token", min_length=10)


class UpdateProfileRequest(BaseModel):
    """修改个人信息请求体"""
    email: Optional[str] = Field(None, description="邮箱地址")
    nickname: Optional[str] = Field(None, description="昵称", max_length=50)


class ForgotPasswordRequest(BaseModel):
    """忘记密码请求体"""
    username: str = Field(..., description="用户名", min_length=1)
    email: str = Field(..., description="注册邮箱")


# ==============================
# 响应模型定义
# ==============================
# 声明 response_model 后，OpenAPI 会生成精确的 data 结构，
# 客户端 SDK 才能拿到强类型而不是 unknown。

class LoginData(BaseModel):
    """登录成功的业务数据"""
    token: str = Field(..., description="access_token 的兼容字段，新客户端请用 access_token")
    access_token: str = Field(..., description="访问令牌，放入 Authorization: Bearer <token>")
    refresh_token: str = Field(..., description="刷新令牌，access_token 过期时换取新令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="access_token 有效期（秒）")
    user_id: int = Field(..., description="用户 ID")
    username: str = Field(..., description="用户名")


class RefreshData(BaseModel):
    """刷新令牌返回的业务数据"""
    access_token: str = Field(..., description="新的访问令牌")
    refresh_token: Optional[str] = Field(
        None, description="新的刷新令牌；开启轮换时必有，旧值随即失效"
    )
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="access_token 有效期（秒）")


class LogoutData(BaseModel):
    """退出登录返回的业务数据"""
    blacklisted: bool = Field(
        ..., description="服务端是否已将当前 Token 加入黑名单（取决于 TOKEN_BLACKLIST_ENABLED）"
    )


class PermissionsData(BaseModel):
    """当前用户权限"""
    role: str = Field(..., description="角色标识")
    permissions: List[str] = Field(default_factory=list, description="该角色拥有的权限清单")


class RegisterData(BaseModel):
    """注册成功的业务数据"""
    user_id: int = Field(..., description="新用户 ID")
    username: str = Field(..., description="用户名")


class ProfileData(BaseModel):
    """个人信息（GET /auth/profile）"""
    user_id: int = Field(..., description="用户 ID")
    username: str = Field(..., description="用户名")
    email: str = Field(..., description="邮箱")
    nickname: Optional[str] = Field(None, description="昵称")
    status: Optional[int] = Field(None, description="状态：0 禁用 / 1 启用")
    created_at: Optional[str] = Field(None, description="创建时间，ISO 8601")


class UpdateProfileData(BaseModel):
    """修改个人信息的结果（PUT /auth/profile）"""
    user_id: int = Field(..., description="用户 ID")
    username: str = Field(..., description="用户名")
    email: str = Field(..., description="邮箱")
    nickname: Optional[str] = Field(None, description="昵称")


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
        
        @self.router.post("/auth/login", summary="用户登录", response_model=ApiResponse[LoginData])
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
                # 1006 表示凭证错误；连续失败被锁定时由服务层抛出 423
                return self.error(message="用户名或密码错误", code=ErrorCode.INVALID_CREDENTIALS)
            
            return self.success(
                data={
                    # access_token 用于业务接口；refresh_token 用于免登录续期
                    "token": result["token"],              # 兼容旧字段名
                    "access_token": result["access_token"],
                    "refresh_token": result["refresh_token"],
                    "token_type": result["token_type"],
                    "expires_in": result["expires_in"],
                    "user_id": result["user"].id,
                    "username": result["user"].username,
                },
                message="登录成功",
            )
        
        @self.router.post("/auth/refresh", summary="刷新访问令牌", response_model=ApiResponse[RefreshData])
        @skip_auth
        async def refresh_token(data: RefreshTokenRequest):
            """用 refresh_token 换取新的 access_token

            客户端在 access_token 过期（错误码 1004）时调用，用户无需重新登录。
            启用轮换（JWT_REFRESH_TOKEN_ROTATE=true）时，旧的 refresh_token
            会立即失效，客户端必须用响应里的新值替换本地存储。
            """
            try:
                tokens = await refresh_access_token(data.refresh_token)
            except ValueError as exc:
                return self.error(
                    message=str(exc) or "Refresh Token 无效，请重新登录",
                    code=ErrorCode.REFRESH_TOKEN_INVALID,
                )

            return self.success(data=tokens, message="刷新成功")

        @self.router.post("/auth/logout", summary="退出登录", response_model=ApiResponse[LogoutData])
        async def logout(request: Request):
            """退出登录

            启用 TOKEN_BLACKLIST_ENABLED 时，当前 access_token 会进入黑名单，
            在自然过期前无法再次使用；未启用时客户端只需删除本地 Token。
            无论是否启用，接口都返回成功，客户端可据此清理本地状态。
            """
            token = get_token_from_header(request.headers.get("Authorization"))
            if token and TOKEN_BLACKLIST_ENABLED:
                await blacklist_token(token)

            return self.success(
                message="已退出登录",
                data={"blacklisted": bool(token and TOKEN_BLACKLIST_ENABLED)},
            )

        @self.router.get("/auth/permissions", summary="获取当前用户权限", response_model=ApiResponse[PermissionsData])
        async def get_my_permissions(request: Request):
            """返回当前登录用户的角色与权限清单

            客户端可据此控制按钮/菜单的可见性，避免"点了才报 403"。
            权限映射的权威定义在 `config/permissions.py`。
            """
            user = self.get_current_user(request)
            if not user:
                return self.error(message="未登录", code=ErrorCode.TOKEN_MISSING)

            role = (user.payload or {}).get("role") or DEFAULT_ROLE
            return self.success(
                data={
                    "role": role,
                    "permissions": sorted(get_role_permissions(role)),
                }
            )

        @self.router.post("/auth/register", summary="用户注册", response_model=ApiResponse[RegisterData])
        @skip_auth
        async def register(
            data: RegisterRequest,
            db: AsyncSession = Depends(get_db),
        ):
            """用户注册接口
            
            创建新用户账号，注册成功后返回用户信息。
            此接口在 SKIP_AUTH_ROUTES 中配置为免验证，无需任何装饰器。
            """
            # 邮箱格式校验：注册契约要求 email 必填且格式合法
            if not is_email(data.email):
                return self.error(message="邮箱格式不正确", code=400)

            # 用户名与邮箱都需唯一，一次查询同时判断
            stmt = select(User).where(
                (User.username == data.username) | (User.email == data.email)
            )
            result = await db.execute(stmt)
            if result.scalars().first():
                return self.error(message="用户名或邮箱已被注册", code=409)
            
            # 创建新用户
            auth_service = AuthService(db)
            new_user = User(
                username=data.username,
                password=auth_service.hash_password(data.password),
                email=data.email,
                status=1,
            )
            db.add(new_user)
            # 事务由 get_db 统一提交；此处仅 flush 以获得自增主键
            await db.flush()
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
        
        @self.router.post("/auth/forgot-password", summary="忘记密码", response_model=ApiResponse[EmptyData])
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
        
        @self.router.get("/auth/profile", summary="获取个人信息", response_model=ApiResponse[ProfileData])
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
        
        @self.router.put("/auth/profile", summary="修改个人信息", response_model=ApiResponse[UpdateProfileData])
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
            
            # 事务由 get_db 统一提交
            await db.flush()
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
        
        @self.router.post("/auth/change-password", summary="修改密码", response_model=ApiResponse[EmptyData])
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
                return self.error(message="原密码不正确", code=ErrorCode.PASSWORD_MISMATCH)
            
            # 更新密码（事务由 get_db 统一提交）
            db_user.password = auth_service.hash_password(data.new_password)

            # 递增 token 版本：该用户所有已签发 Token 立即失效（包括当前这个），
            # 防止密码泄露后旧 Token 在有效期内继续被使用
            await bump_token_version(db, db_user.id)
            await db.flush()
            
            return self.success(message="密码修改成功，请重新登录")
