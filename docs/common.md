# 公共模块（Common）

`common` 模块是 ThinkPython 中的共享代码目录，用于存放跨模块复用的 Model、Service 和 Controller。

## 为什么需要 Common 模块

在多模块模式下，如果多个模块需要使用相同的模型或服务，将这些代码放在 `common` 模块可以避免重复：

```
app/
├── api/          # API 模块 - 需要用户模型
├── admin/        # 管理模块 - 也需要用户模型
└── common/       # 公共模块 - 用户模型放在这里
```

`api` 和 `admin` 都可以从 `common` 导入：

```python
from app.common.model.user_model import User
from app.common.service.auth_service import AuthService
```

## 目录结构

```
app/common/
├── controller/
│   └── base_auth_controller.py   # 需要认证的控制器基类
├── model/
│   └── user_model.py             # 共享的用户模型
└── service/
    └── auth_service.py           # 共享的认证服务
```

## 使用示例

### 共享 Model

```python
# app/common/model/user_model.py
from core.base_model import Base

class User(Base):
    __tablename__ = "users"
```

在其他模块中使用：

```python
# app/api/controller/auth_controller.py
from app.common.model.user_model import User
```

### 共享 Service

```python
# app/common/service/auth_service.py
from core.base_service import BaseService

class AuthService(BaseService):
    async def login(self, username, password):
        # 登录逻辑
        pass
```

在其他模块中使用：

```python
from app.common.service.auth_service import AuthService

auth_service = AuthService(db)
result = await auth_service.login(username, password)
```

## BaseAuthController

`BaseAuthController` 是 `common` 模块提供的核心基类，继承自 `BaseController`，增加了认证辅助功能。

### 使用方式

需要登录认证的控制器继承 `BaseAuthController`，不需要认证的继承 `BaseController`：

```python
# 需要认证的控制器
from app.common.controller.base_auth_controller import BaseAuthController

class UserController(BaseAuthController):
    SKIP_AUTH_ROUTES = []  # 配置免验证路由
    
    def _setup_routes(self):
        @self.router.get("/profile")
        async def get_profile(request: Request):
            user = self.get_current_user(request)
            return self.success(data={"user_id": user.user_id})

# 不需要认证的控制器
from core.base_controller import BaseController

class HealthController(BaseController):
    def _setup_routes(self):
        @self.router.get("/health")
        async def health():
            return self.success(data={"status": "ok"})
```

### get_current_user()

从请求上下文中获取当前登录用户：

```python
@self.router.get("/profile")
async def get_profile(request: Request):
    user = self.get_current_user(request)
    if not user:
        return self.error(message="未登录", code=401)
    
    return self.success(data={"user_id": user.user_id})
```

## 何时放入 Common 模块

- 多个模块都需要使用的 Model（如 `User`、`Role`）
- 共享的业务逻辑 Service（如 `AuthService`）
- 控制器基类（如 `BaseAuthController`）

如果某个 Model/Service 只被一个模块使用，应该放在该模块自己的目录中。

---

[← 返回首页](../README.md)
