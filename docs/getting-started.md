# 5 分钟创建第一个 API

本教程演示从零开始，使用 ThinkPython 创建一个完整的用户管理 CRUD 接口。

## 前置准备

确保已安装框架并启动服务：

```bash
pip install -r requirements.txt
python think.py run
```

访问 [http://localhost:8000/docs](http://localhost:8000/docs) 确认服务正常。

## 第 1 步：创建数据模型

```bash
python think.py make-model User
```

编辑生成的 `app/single/model/user_model.py`：

```python
from core.base_model import Base

class User(Base):
    __tablename__ = "users"
    
    # id, created_at, updated_at 由 Base 自动提供
```

如需自定义字段：

```python
from sqlalchemy import Column, String, Integer
from sqlalchemy.sql import func
from core.base_model import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(100), nullable=False)
    mobile = Column(String(20), nullable=True)
    status = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

## 第 2 步：创建 Service 层

```bash
python think.py make-service User
```

编辑生成的 `app/single/service/user_service.py`：

```python
from core.base_service import BaseService
from app.single.model.user_model import User

class UserService(BaseService[User]):
    model_class = User
    
    async def get_by_username(self, username: str) -> User | None:
        """根据用户名查询用户"""
        from sqlalchemy import select
        stmt = select(User).where(User.username == username)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
```

`BaseService` 已内置 `get_all`, `get_by_id`, `create`, `update`, `delete` 等通用方法。

## 第 3 步：创建 Controller 层

```bash
python think.py make-controller User
```

编辑生成的 `app/single/controller/user_controller.py`：

```python
from typing import Optional
from pydantic import BaseModel
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from core.base_controller import BaseController
from core.database import get_db
from core.exception import NotFoundException
from app.single.service.user_service import UserService


class UserCreateRequest(BaseModel):
    username: str
    email: str
    mobile: Optional[str] = None


class UserUpdateRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    mobile: Optional[str] = None


class UserController(BaseController):
    
    def __init__(self):
        super().__init__()
        self._setup_routes()
    
    def _setup_routes(self):
        # 获取用户列表（分页）
        @self.router.get("/user/list", summary="用户列表")
        async def get_users(page: int = 1, page_size: int = 10, db: AsyncSession = Depends(get_db)):
            service = UserService(db)
            items, total = await service.get_all(page, page_size)
            return self.paginate(items, total, page, page_size)
        
        # 获取用户详情
        @self.router.get("/user/{user_id}", summary="获取用户详情")
        async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
            service = UserService(db)
            user = await service.get_by_id(user_id)
            if not user:
                raise NotFoundException(f"用户 {user_id} 不存在")
            return self.success(data=user)
        
        # 创建用户
        @self.router.post("/user", summary="创建用户")
        async def create_user(request: UserCreateRequest, db: AsyncSession = Depends(get_db)):
            service = UserService(db)
            user_data = request.model_dump(exclude_none=True)
            user = await service.create(user_data)
            return self.success(data=user, message="创建成功")
        
        # 更新用户
        @self.router.put("/user/{user_id}", summary="更新用户")
        async def update_user(user_id: int, request: UserUpdateRequest, db: AsyncSession = Depends(get_db)):
            service = UserService(db)
            user_data = request.model_dump(exclude_unset=True)
            user = await service.update(user_id, user_data)
            if not user:
                raise NotFoundException(f"用户 {user_id} 不存在")
            return self.success(data=user, message="更新成功")
        
        # 删除用户
        @self.router.delete("/user/{user_id}", summary="删除用户")
        async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
            service = UserService(db)
            success = await service.delete(user_id)
            if not success:
                raise NotFoundException(f"用户 {user_id} 不存在")
            return self.success(message="删除成功")
```

## 第 4 步：数据库迁移

```bash
python think.py db-migrate
```

该命令会自动扫描所有 Model 并在数据库中创建对应的表。

## 第 5 步：测试接口

重启服务后即可测试：

```bash
# 创建用户
curl -X POST http://localhost:8000/user \
  -H "Content-Type: application/json" \
  -d '{"username": "张三", "email": "zhangsan@example.com"}'

# 获取用户列表
curl http://localhost:8000/user/list?page=1&page_size=10

# 获取用户详情
curl http://localhost:8000/user/1

# 更新用户
curl -X PUT http://localhost:8000/user/1 \
  -H "Content-Type: application/json" \
  -d '{"email": "newemail@example.com"}'

# 删除用户
curl -X DELETE http://localhost:8000/user/1
```

也可直接访问 [http://localhost:8000/docs](http://localhost:8000/docs) 在 Swagger UI 中可视化测试。

## 统一响应格式

所有接口返回统一格式：

```json
{
  "code": 200,
  "message": "success",
  "data": { "id": 1, "username": "张三", "email": "zhangsan@example.com" }
}
```

分页响应：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [...],
    "total": 50,
    "page": 1,
    "page_size": 10,
    "total_pages": 5
  }
}
```

---

[← 返回首页](../README.md)
