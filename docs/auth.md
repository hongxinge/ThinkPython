# 认证机制

ThinkPython 采用 **"默认认证 + 白名单跳过"** 的安全策略。即：默认所有接口都需要 JWT Token 认证，只有明确标记为免验证的接口才可以被匿名访问。

## 三种免验证方式

框架提供三种方式跳过认证，从粗到细粒度：

| 方式 | 适用场景 | 配置位置 |
|------|----------|----------|
| 1. 全局白名单 | 系统级公开接口（健康检查、文档） | `config/auth.py` |
| 2. 控制器级白名单 | 模块级公开接口（登录、注册） | 控制器 `SKIP_AUTH_ROUTES` 属性 |
| 3. `@skip_auth` 装饰器 | 单个接口的细粒度控制 | 路由函数上 |

### 方式 1：全局白名单

在 `config/auth.py` 中配置：

```python
SKIP_AUTH_PATHS = [
    "/health",            # 健康检查
    "/docs",              # Swagger API 文档
    "/redoc",             # ReDoc API 文档
    "/openapi.json",      # OpenAPI Schema
    "/favicon.ico",       # 网站图标
]
```

适用于不需要认证的系统级路径。

### 方式 2：控制器级白名单（推荐）

在控制器类中定义 `SKIP_AUTH_ROUTES` 属性，继承 `BaseAuthController`：

```python
from app.common.controller.base_auth_controller import BaseAuthController

class AuthController(BaseAuthController):
    # 配置一次，声明哪些路由免验证
    SKIP_AUTH_ROUTES = [
        "POST /auth/login",           # 登录接口
        "POST /auth/register",        # 注册接口
        "POST /auth/forgot-password", # 忘记密码
    ]
    
    def _setup_routes(self):
        # 免验证接口 - 无需装饰器
        @self.router.post("/auth/login")
        async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
            auth_service = AuthService(db)
            result = await auth_service.login(data.username, data.password)
            if not result:
                return self.error(message="用户名或密码错误", code=401)
            return self.success(data={
                "token": result["token"],
                "user_id": result["user"].id,
                "username": result["user"].username,
            })
        
        # 需要认证的接口 - 自动拦截
        @self.router.get("/auth/profile")
        async def get_profile(request: Request):
            user = self.get_current_user(request)
            if not user:
                return self.error(message="未登录", code=401)
            return self.success(data={"user_id": user.user_id})
```

**格式规则：**

- 精确匹配：`"POST /login"`
- 通配符：`"GET /api/*"`（匹配该路径所有子路由）
- 方法可选：`"/health"`（匹配所有 HTTP 方法）

### 方式 3：`@skip_auth` 装饰器

在路由函数上直接标记：

```python
from helpers.auth import skip_auth

@self.router.post("/auth/forgot-password", summary="忘记密码")
@skip_auth
async def forgot_password(data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    # 无需 Token，任何人可访问
    return self.success(message="重置密码邮件已发送")
```

## 完整示例：登录/注册/忘记密码/个人资料

```python
from app.common.controller.base_auth_controller import BaseAuthController
from helpers.auth import skip_auth
from app.common.service.auth_service import AuthService
from core.database import get_db
from fastapi import Depends, Request

class AuthController(BaseAuthController):
    SKIP_AUTH_ROUTES = [
        "POST /auth/login",
        "POST /auth/register",
    ]
    
    def _setup_routes(self):
        # === 免验证接口 ===
        
        @self.router.post("/auth/login", summary="用户登录")
        async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
            auth_service = AuthService(db)
            result = await auth_service.login(data.username, data.password)
            if not result:
                return self.error(message="用户名或密码错误", code=401)
            return self.success(data={
                "token": result["token"],
                "user_id": result["user"].id,
            })
        
        @self.router.post("/auth/register", summary="用户注册")
        async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
            auth_service = AuthService(db)
            new_user = User(
                username=data.username,
                password=auth_service.hash_password(data.password),
            )
            db.add(new_user)
            await db.commit()
            return self.success(data={"user_id": new_user.id})
        
        # 忘记密码使用 @skip_auth 装饰器
        @self.router.post("/auth/forgot-password", summary="忘记密码")
        @skip_auth
        async def forgot_password(data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
            # 验证用户邮箱并发送重置邮件
            return self.success(message="重置邮件已发送")
        
        # === 需要认证的接口 ===
        
        @self.router.get("/auth/profile", summary="获取个人信息")
        async def get_profile(request: Request):
            user = self.get_current_user(request)
            if not user:
                return self.error(message="未登录", code=401)
            return self.success(data={"user_id": user.user_id})
```

## 请求示例

```bash
# 登录（无需 Token）
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "123456"}'

# 注册（无需 Token）
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "newuser", "password": "123456", "email": "user@example.com"}'

# 获取个人信息（需要 Token）
curl -X GET http://localhost:8000/api/auth/profile \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."

# 修改密码（需要 Token）
curl -X POST http://localhost:8000/api/auth/change-password \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  -d '{"old_password": "123456", "new_password": "654321"}'
```

## 认证流程图

```
请求进入
    │
    ▼
[全局白名单检查] ── 匹配 ──→ 放行
    │ 不匹配
    ▼
[控制器白名单检查] ── 匹配 ──→ 放行
    │ 不匹配
    ▼
[@skip_auth 装饰器检查] ── 有 ──→ 放行
    │ 没有
    ▼
[JWT Token 验证] ── 有效 ──→ 放行（注入 current_user）
    │ 无效
    ▼
返回 401 Unauthorized
```

## 配置项

在 `config/auth.py` 和 `.env` 中配置：

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `AUTH_ENABLED` | 是否启用认证中间件 | `true` |
| `JWT_SECRET` | JWT 签名密钥 | `your-secret-key...` |
| `JWT_ALGORITHM` | 签名算法 | `HS256` |
| `JWT_EXPIRE_HOURS` | Token 过期时间（小时） | `24` |
| `JWT_REFRESH_HOURS` | Token 刷新窗口期（小时） | `2` |
| `LOGIN_MAX_ATTEMPTS` | 登录失败最大尝试次数 | `5` |
| `LOGIN_LOCK_DURATION` | 账号锁定时长（分钟） | `30` |

## 安全最佳实践

1. **生产环境必须修改 `JWT_SECRET`**：使用强随机密钥（建议 32 位以上）
   ```env
   JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
   ```

2. **设置合理的 Token 过期时间**：根据业务需求调整，不宜过长
   ```env
   JWT_EXPIRE_HOURS=2
   ```

3. **关闭调试模式**：生产环境设置 `APP_DEBUG=False`，避免暴露敏感信息

4. **限制 CORS 来源**：不要使用 `*`，指定允许的域名
   ```env
   CORS_ORIGINS=https://yourdomain.com
   ```

5. **使用 HTTPS**：确保 Token 在传输过程中不被窃取

6. **敏感操作二次验证**：修改密码、删除账号等操作可以要求输入原密码

---

[← 返回首页](../README.md)
