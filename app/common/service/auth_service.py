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
import hashlib
import hmac
import secrets
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.base_service import BaseService
from core.exception import AccountLockedException
from app.common.model.user_model import User
from helpers.auth import create_refresh_token, create_token, decode_token
from helpers.common import md5
from config.auth import (
    JWT_ACCESS_TOKEN_EXPIRE_HOURS,
    LOGIN_LOCK_DURATION,
    LOGIN_MAX_ATTEMPTS,
)
from config.permissions import DEFAULT_ROLE

# 登录失败计数在缓存中的键前缀
_LOGIN_FAIL_PREFIX = "login_fail:"


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
        # 1. 检查账号是否处于失败锁定期（防止密码暴力破解）
        await self._ensure_not_locked(username)

        # 2. 通过用户名查询用户
        stmt = select(User).where(User.username == username)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        
        # 3. 用户不存在或密码不匹配：累计失败次数，达到阈值直接抛锁定异常
        if not user or not self._verify_password(password, user.password):
            await self._record_login_failure(username)
            return None
        
        # 检查用户状态是否为启用
        if user.status != 1:
            return None

        # 4. 登录成功：清除失败计数，避免历史失败影响后续登录
        await self._clear_login_failures(username)

        # 存量 MD5 哈希在登录成功后自动升级为 PBKDF2
        if self.needs_rehash(user.password):
            user.password = self.hash_password(password)
            await self.db.flush()

        # 生成双 Token：access 用于业务接口，refresh 用于免登录续期
        # role 写入 payload，供认证中间件做接口级权限校验（见 config/permissions.py）
        token_version = getattr(user, "token_version", 0) or 0
        role = getattr(user, "role", None) or DEFAULT_ROLE
        extra = {"username": user.username, "role": role}
        access_token = create_token(
            user_id=user.id,
            extra_data=extra,
            token_version=token_version,
        )
        refresh_token = create_refresh_token(
            user_id=user.id,
            extra_data=extra,
            token_version=token_version,
        )

        return {
            "user": user,
            "token": access_token,          # 兼容旧字段名
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": JWT_ACCESS_TOKEN_EXPIRE_HOURS * 3600,
        }

    # ==============================
    # 登录失败锁定
    # ==============================
    # 设计要点：
    #   - 计数放在缓存（Memory 单机 / Redis 分布式），不落库，避免登录路径产生写压力；
    #   - 每次失败刷新 TTL，形成"滑动窗口"：持续攻击会一直锁定，停止后自动解锁；
    #   - 缓存不可用时**放行**而不是拒绝，可用性优先于该辅助防护
    #     （主防护仍由 RATE_LIMIT_LOGIN_* 的 IP 限流承担）。

    async def _ensure_not_locked(self, username: str) -> None:
        """检查账号是否处于锁定期，是则抛出 423"""
        try:
            from core.cache import get_cache

            fails = await get_cache(f"{_LOGIN_FAIL_PREFIX}{username}")
        except Exception:  # noqa: BLE001 - 缓存故障不阻断登录
            return

        if fails is None:
            return

        try:
            fail_count = int(fails)
        except (TypeError, ValueError):
            return

        if fail_count >= LOGIN_MAX_ATTEMPTS:
            raise AccountLockedException(
                f"登录失败次数过多，账号已锁定 {LOGIN_LOCK_DURATION} 分钟",
                retry_after=LOGIN_LOCK_DURATION * 60,
            )

    async def _record_login_failure(self, username: str) -> None:
        """记录一次登录失败；达到阈值时抛出 423"""
        try:
            from core.cache import get_cache, set_cache

            key = f"{_LOGIN_FAIL_PREFIX}{username}"
            current = await get_cache(key)
            fail_count = (int(current) if current is not None else 0) + 1

            # TTL 每次刷新，形成滑动窗口
            await set_cache(key, fail_count, ttl=LOGIN_LOCK_DURATION * 60)
        except Exception:  # noqa: BLE001 - 缓存故障不阻断登录
            return

        if fail_count >= LOGIN_MAX_ATTEMPTS:
            raise AccountLockedException(
                f"登录失败次数过多，账号已锁定 {LOGIN_LOCK_DURATION} 分钟",
                retry_after=LOGIN_LOCK_DURATION * 60,
            )

    async def _clear_login_failures(self, username: str) -> None:
        """登录成功后清除失败计数"""
        try:
            from core.cache import delete_cache

            await delete_cache(f"{_LOGIN_FAIL_PREFIX}{username}")
        except Exception:  # noqa: BLE001
            pass

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
    
    # PBKDF2-HMAC-SHA256 迭代次数；参数固化在哈希串中，调整后旧哈希仍可校验
    PBKDF2_ITERATIONS = 260_000
    PASSWORD_ALGORITHM = "pbkdf2_sha256"

    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """校验密码，兼容历史 MD5 哈希。
        
        Args:
            plain_password: 用户输入的明文密码
            hashed_password: 数据库中存储的哈希密码
            
        Returns:
            bool: 密码匹配返回 True，不匹配返回 False
        """
        if not hashed_password:
            return False

        if hashed_password.startswith(f"{self.PASSWORD_ALGORITHM}$"):
            try:
                _, iterations, salt, digest = hashed_password.split("$", 3)
                expected = hashlib.pbkdf2_hmac(
                    "sha256",
                    plain_password.encode("utf-8"),
                    salt.encode("ascii"),
                    int(iterations),
                )
            except (ValueError, TypeError):
                return False
            return hmac.compare_digest(expected.hex(), digest)

        # 兼容历史数据：32 位十六进制 MD5
        return hmac.compare_digest(md5(plain_password), hashed_password)
    
    def hash_password(self, password: str) -> str:
        """使用 PBKDF2-HMAC-SHA256 对密码加盐哈希。
        
        格式：pbkdf2_sha256$迭代次数$盐$摘要
        
        Args:
            password: 明文密码
            
        Returns:
            str: 加密后的密码哈希值
        """
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("ascii"),
            self.PBKDF2_ITERATIONS,
        )
        return f"{self.PASSWORD_ALGORITHM}${self.PBKDF2_ITERATIONS}${salt}${digest.hex()}"

    def needs_rehash(self, hashed_password: str) -> bool:
        """判断存量哈希是否需要升级为当前算法。"""
        return not (hashed_password or "").startswith(f"{self.PASSWORD_ALGORITHM}$")
