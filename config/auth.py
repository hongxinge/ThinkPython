"""
ThinkPython 认证配置模块

集中管理全局认证相关配置，包括：
- 免验证路径白名单（无需 Token 即可访问的接口）
- Token 刷新策略
- 登录失败锁定策略

设计原则：
- 默认所有接口都需要认证（安全优先）
- 通过白名单明确标记免验证接口
- 支持三种免验证配置方式（从粗到细粒度）：
  1. 全局白名单（SKIP_AUTH_PATHS）：适用于系统级公开接口（如健康检查）
  2. 控制器级白名单（SKIP_AUTH_ROUTES）：适用于模块级公开接口（如登录/注册）
  3. 装饰器标记（@skip_auth）：适用于单个接口的细粒度控制

使用方式：
    # 方式1: 在全局白名单中添加路径
    SKIP_AUTH_PATHS = ["/health", "/docs", "/openapi.json"]
    
    # 方式2: 在控制器中定义 SKIP_AUTH_ROUTES 属性
    class AuthController(BaseController):
        SKIP_AUTH_ROUTES = ["POST /login", "POST /register"]
    
    # 方式3: 使用装饰器标记单个接口
    @self.router.post("/login")
    @skip_auth
    async def login():
        pass
"""
import os

# ==============================
# 全局免验证路径白名单
# ==============================

# 不需要认证的接口路径列表（支持精确匹配和前缀匹配）
# 适用于系统级的公开接口，如健康检查、API 文档等
SKIP_AUTH_PATHS = [
    "/health",            # 健康检查
    "/docs",              # Swagger API 文档
    "/redoc",             # ReDoc API 文档
    "/openapi.json",      # OpenAPI Schema
    "/favicon.ico",       # 网站图标
]

# 是否启用全局认证中间件
# True: 所有接口默认需要认证，除非在白名单中
# False: 所有接口默认公开，除非明确要求认证
AUTH_ENABLED = os.getenv("AUTH_ENABLED", "true").lower() == "true"

# ==============================
# JWT 配置（双 Token 机制）
# ==============================

# JWT 密钥（建议通过环境变量配置，生产环境使用强随机密钥）
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-this-in-production")

# JWT 签名算法
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# Access Token 过期时间（小时），用于日常接口访问
# 建议设置较短时间（1-2小时），提高安全性
JWT_ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_HOURS", "2"))

# Refresh Token 过期时间（天），用于刷新 Access Token
# 建议设置较长时间（7-30天），减少用户登录频率
JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Refresh Token 是否可轮换（True = 每次刷新生成新的 Refresh Token）
# 开启后更安全，旧 Refresh Token 立即失效
JWT_REFRESH_TOKEN_ROTATE = os.getenv("JWT_REFRESH_TOKEN_ROTATE", "true").lower() == "true"

# ==============================
# Token 黑名单配置（用于主动注销）
# ==============================

# 是否启用 Token 黑名单（需要 Redis 支持）
# True: 用户登出时将 Token 加入黑名单，有效期内无法再次使用
# False: 不启用黑名单，Token 只能等待自然过期
TOKEN_BLACKLIST_ENABLED = os.getenv("TOKEN_BLACKLIST_ENABLED", "false").lower() == "true"

# Token 黑名单 Redis Key 前缀
TOKEN_BLACKLIST_PREFIX = "token:blacklist:"

# ==============================
# 登录安全策略
# ==============================

# 登录失败最大尝试次数（超过后锁定账号）
LOGIN_MAX_ATTEMPTS = int(os.getenv("LOGIN_MAX_ATTEMPTS", "5"))

# 账号锁定时长（分钟）
LOGIN_LOCK_DURATION = int(os.getenv("LOGIN_LOCK_DURATION", "30"))
