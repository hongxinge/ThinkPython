# API 使用示例

本文档演示如何使用 ThinkPython 开发完整的 CRUD API。

> 💡 如果你还没安装 ThinkPython，请先查看 [README.md](../README.md) 中的快速开始指南。

---

## 完整教程：创建用户管理 API

本教程将带你从零开始，创建一个完整的「用户管理」CRUD API，包含增、删、改、查、分页等功能。

---

## 1. 创建用户模块

### 方式一：使用 CLI 工具（推荐）

```bash
python think.py make-controller User
python think.py make-model User
python think.py make-service User
```

### 方式二：手动创建

在 `app/single/` 目录下分别创建：
- `controller/user_controller.py`
- `model/user_model.py`
- `service/user_service.py`

---

## 2. 定义数据模型

打开 `app/single/model/user_model.py`，定义数据库表结构：

```python
"""
用户模型
"""
from sqlalchemy import Column, String, Integer
from core.base_model import BaseModel


class User(BaseModel):
    """用户模型"""
    
    __tablename__ = "user"
    
    username = Column(String(50), unique=True, nullable=False, comment="用户名")
    email = Column(String(100), unique=True, nullable=False, comment="邮箱")
    mobile = Column(String(20), comment="手机号")
    password = Column(String(255), nullable=False, comment="密码")
    status = Column(Integer, default=1, comment="状态: 0禁用 1启用")
```

### BaseModel 自带字段

继承 `BaseModel` 后，你的模型自动拥有以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Integer | 主键，自增 |
| `created_at` | DateTime | 创建时间，自动填充 |
| `updated_at` | DateTime | 更新时间，自动更新 |

### 常用字段类型

| 类型 | SQLAlchemy | 说明 |
|------|-----------|------|
| 整数 | `Integer` | 普通整数 |
| 大整数 | `BigInteger` | 大整数 |
| 字符串 | `String(长度)` | 定长字符串 |
| 文本 | `Text` | 长文本 |
| 布尔 | `Boolean` | 布尔值 |
| 日期时间 | `DateTime` | 日期时间 |
| 浮点数 | `Float` | 浮点数 |
| JSON | `JSON` | JSON数据 |

---

## 3. 编写服务层

打开 `app/single/service/user_service.py`，编写业务逻辑：

```python
"""
用户服务
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.base_service import BaseService
from app.single.model.user_model import User


class UserService(BaseService):
    """用户服务"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db)
        self.model_class = User  # 关联到User模型
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        stmt = select(User).where(User.username == username)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def check_username_exists(self, username: str) -> bool:
        """检查用户名是否存在"""
        user = await self.get_by_username(username)
        return user is not None
```

### BaseService 提供的基础方法

继承 `BaseService` 后，你的服务自动拥有以下方法：

| 方法 | 说明 | 示例 |
|------|------|------|
| `get_by_id(id)` | 根据ID获取记录 | `await self.get_by_id(1)` |
| `get_all(page, page_size)` | 分页获取所有记录 | `await self.get_all(1, 10)` |
| `create(data)` | 创建记录 | `await self.create({"name": "张三"})` |
| `update(id, data)` | 更新记录 | `await self.update(1, {"name": "李四"})` |
| `delete(id)` | 删除记录 | `await self.delete(1)` |

---

## 4. 编写控制器

打开 `app/single/controller/user_controller.py`，实现路由：

```python
"""
用户控制器
"""
from typing import Optional
from pydantic import BaseModel
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.base_controller import BaseController
from core.database import get_db
from core.exception import NotFoundException
from app.single.service.user_service import UserService


class UserCreateRequest(BaseModel):
    """创建用户请求模型"""
    username: str
    email: str
    mobile: Optional[str] = None
    password: str


class UserUpdateRequest(BaseModel):
    """更新用户请求模型"""
    email: Optional[str] = None
    mobile: Optional[str] = None


class UserController(BaseController):
    """用户控制器"""
    
    def __init__(self):
        super().__init__()
        self._setup_routes()
    
    def _setup_routes(self):
        @self.router.get("/user/list", summary="用户列表")
        async def get_list(page: int = 1, page_size: int = 10, db: AsyncSession = Depends(get_db)):
            """获取用户列表（分页）"""
            service = UserService(db)
            items, total = await service.get_all(page, page_size)
            return self.paginate(items, total, page, page_size)
        
        @self.router.get("/user/{user_id}", summary="用户详情")
        async def get_detail(user_id: int, db: AsyncSession = Depends(get_db)):
            """获取用户详情"""
            service = UserService(db)
            user = await service.get_by_id(user_id)
            if not user:
                raise NotFoundException(f"用户 {user_id} 不存在")
            return self.success(data=user)
        
        @self.router.post("/user", summary="创建用户")
        async def create(request: UserCreateRequest, db: AsyncSession = Depends(get_db)):
            """创建用户"""
            service = UserService(db)
            
            # 检查用户名是否已存在
            if await service.check_username_exists(request.username):
                return self.error("用户名已存在", 400)
            
            user = await service.create(request.model_dump())
            return self.success(data=user, message="创建成功")
        
        @self.router.put("/user/{user_id}", summary="更新用户")
        async def update(user_id: int, request: UserUpdateRequest, db: AsyncSession = Depends(get_db)):
            """更新用户"""
            service = UserService(db)
            user = await service.update(user_id, request.model_dump(exclude_unset=True))
            if not user:
                raise NotFoundException(f"用户 {user_id} 不存在")
            return self.success(data=user, message="更新成功")
        
        @self.router.delete("/user/{user_id}", summary="删除用户")
        async def delete(user_id: int, db: AsyncSession = Depends(get_db)):
            """删除用户"""
            service = UserService(db)
            success = await service.delete(user_id)
            if not success:
                raise NotFoundException(f"用户 {user_id} 不存在")
            return self.success(message="删除成功")
```

### BaseController 提供的响应方法

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `self.success(data, message, code)` | 成功响应 | `{"code": 200, "message": "...", "data": {...}}` |
| `self.error(message, code, data)` | 错误响应 | `{"code": 400, "message": "...", "data": null}` |
| `self.paginate(items, total, page, page_size)` | 分页响应 | 包含分页信息的JSON |

---

## 5. 执行数据库迁移

```bash
python think.py db-migrate
```

这会自动扫描所有模型并创建对应的数据库表。

---

## 6. 启动并测试

### 启动服务

```bash
python think.py run
```

### API 测试

#### 获取用户列表

```bash
curl http://localhost:8000/user/list
```

响应：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [],
    "total": 0,
    "page": 1,
    "page_size": 10,
    "total_pages": 0
  }
}
```

#### 创建用户

```bash
curl -X POST http://localhost:8000/user \
  -H "Content-Type: application/json" \
  -d '{"username":"zhangsan","email":"zhangsan@example.com","password":"123456"}'
```

响应：
```json
{
  "code": 200,
  "message": "创建成功",
  "data": {
    "id": 1,
    "username": "zhangsan",
    "email": "zhangsan@example.com",
    "mobile": null,
    "password": "123456",
    "status": 1,
    "created_at": "2024-01-01T10:00:00",
    "updated_at": "2024-01-01T10:00:00"
  }
}
```

#### 获取用户详情

```bash
curl http://localhost:8000/user/1
```

响应：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "username": "zhangsan",
    "email": "zhangsan@example.com",
    ...
  }
}
```

#### 更新用户

```bash
curl -X PUT http://localhost:8000/user/1 \
  -H "Content-Type: application/json" \
  -d '{"email":"new@example.com"}'
```

#### 删除用户

```bash
curl -X DELETE http://localhost:8000/user/1
```

#### 错误响应示例

当用户不存在时：
```json
{
  "code": 404,
  "message": "用户 999 不存在",
  "data": null
}
```

---

## 7. 使用 API 文档（Swagger UI）

启动服务后，打开浏览器访问：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

在这里你可以：
- 📖 查看所有 API 接口
- 🧪 直接在浏览器中测试接口
- 📝 查看请求/响应示例

---

## 统一响应格式说明

所有接口返回统一的 JSON 格式：

### 成功响应

```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

### 分页响应

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {"id": 1, "username": "zhangsan"},
      {"id": 2, "username": "lisi"}
    ],
    "total": 100,
    "page": 1,
    "page_size": 10,
    "total_pages": 10
  }
}
```

### 错误响应

```json
{
  "code": 400,
  "message": "用户名已存在",
  "data": null
}
```

---

## 高级技巧

### 1. 添加查询条件

在 Service 中添加自定义查询方法：

```python
async def search_users(self, keyword: str, page: int = 1, page_size: int = 10) -> tuple:
    """搜索用户"""
    offset = (page - 1) * page_size
    stmt = (
        select(User)
        .where(User.username.contains(keyword))
        .offset(offset)
        .limit(page_size)
    )
    result = await self.db.execute(stmt)
    items = result.scalars().all()
    
    # 统计总数
    count_stmt = select(func.count()).select_from(User).where(User.username.contains(keyword))
    total_result = await self.db.execute(count_stmt)
    total = total_result.scalar() or 0
    
    return items, total
```

### 2. 使用事务

```python
@self.router.post("/user/batch", summary="批量创建用户")
async def batch_create(users: List[UserCreateRequest], db: AsyncSession = Depends(get_db)):
    """批量创建用户"""
    service = UserService(db)
    created_users = []
    for user_data in users:
        user = await service.create(user_data.model_dump())
        created_users.append(user)
    return self.success(data=created_users, message=f"成功创建{len(created_users)}个用户")
```

### 3. 添加缓存

```python
from core.cache import get_cache, set_cache

@self.router.get("/user/{user_id}", summary="用户详情")
async def get_detail(user_id: int, db: AsyncSession = Depends(get_db)):
    """获取用户详情（带缓存）"""
    # 先查缓存
    cache_key = f"user:{user_id}"
    cached = await get_cache(cache_key)
    if cached:
        return self.success(data=cached)
    
    # 缓存未命中，查数据库
    service = UserService(db)
    user = await service.get_by_id(user_id)
    if not user:
        raise NotFoundException(f"用户 {user_id} 不存在")
    
    # 写入缓存（60秒过期）
    await set_cache(cache_key, user, ttl=60)
    
    return self.success(data=user)
```

---

## 下一步

- 📖 查看 [CLI 工具文档](cli.md) 了解更多命令
- ⚙️ 查看 [配置说明](config.md) 了解所有配置项
- 🗄️ 查看 [数据库文档](database.md) 了解数据库配置与迁移
