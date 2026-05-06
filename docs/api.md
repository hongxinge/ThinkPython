# API 使用示例

本文档演示如何使用 ThinkPython 开发完整的 CRUD API。

---

## 1. 创建用户模块

### 方式一：使用CLI工具（推荐）

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

编辑 `app/single/model/user_model.py`：

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

---

## 3. 编写服务层

编辑 `app/single/service/user_service.py`：

```python
"""
用户服务
"""
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.base_service import BaseService
from app.single.model.user_model import User


class UserService(BaseService):
    """用户服务"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db)
        self.model_class = User
    
    async def get_list(self, page: int = 1, page_size: int = 10) -> tuple:
        """获取用户列表"""
        offset = (page - 1) * page_size
        stmt = select(User).offset(offset).limit(page_size)
        result = await self.db.execute(stmt)
        items = result.scalars().all()
        
        count_stmt = select(User)
        count_result = await self.db.execute(count_stmt)
        total = len(count_result.scalars().all())
        
        return items, total
    
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

---

## 4. 编写控制器

编辑 `app/single/controller/user_controller.py`：

```python
"""
用户控制器
"""
from typing import Optional
from pydantic import BaseModel, EmailStr
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.base_controller import BaseController
from core.database import get_db
from helpers.response import success_response, error_response
from app.single.service.user_service import UserService


class UserCreateRequest(BaseModel):
    """创建用户请求"""
    username: str
    email: str
    mobile: Optional[str] = None
    password: str


class UserUpdateRequest(BaseModel):
    """更新用户请求"""
    email: Optional[str] = None
    mobile: Optional[str] = None


class UserController(BaseController):
    """用户控制器"""
    
    def __init__(self):
        super().__init__()
        self._setup_routes()
    
    def _setup_routes(self):
        @self.router.get("/user/list", summary="用户列表")
        async def get_list(
            page: int = 1,
            page_size: int = 10,
            db: AsyncSession = Depends(get_db),
        ):
            service = UserService(db)
            items, total = await service.get_list(page, page_size)
            return self.paginate(
                items=[item.__dict__ for item in items],
                total=total,
                page=page,
                page_size=page_size,
            )
        
        @self.router.get("/user/{user_id}", summary="用户详情")
        async def get_detail(
            user_id: int,
            db: AsyncSession = Depends(get_db),
        ):
            service = UserService(db)
            user = await service.get_by_id(user_id)
            if not user:
                return error_response("用户不存在", 404)
            return success_response(data=user.__dict__)
        
        @self.router.post("/user", summary="创建用户")
        async def create(
            request: UserCreateRequest,
            db: AsyncSession = Depends(get_db),
        ):
            service = UserService(db)
            
            # 检查用户名是否存在
            if await service.check_username_exists(request.username):
                return error_response("用户名已存在", 400)
            
            # 创建用户
            user = await service.create(request.dict())
            return success_response(data=user.__dict__, message="创建成功")
        
        @self.router.put("/user/{user_id}", summary="更新用户")
        async def update(
            user_id: int,
            request: UserUpdateRequest,
            db: AsyncSession = Depends(get_db),
        ):
            service = UserService(db)
            user = await service.update(user_id, request.dict(exclude_unset=True))
            if not user:
                return error_response("用户不存在", 404)
            return success_response(data=user.__dict__, message="更新成功")
        
        @self.router.delete("/user/{user_id}", summary="删除用户")
        async def delete(
            user_id: int,
            db: AsyncSession = Depends(get_db),
        ):
            service = UserService(db)
            success = await service.delete(user_id)
            if not success:
                return error_response("用户不存在", 404)
            return success_response(message="删除成功")
```

---

## 5. 启动并测试

```bash
# 启动服务
python think.py run

# 执行数据库迁移
python think.py db-migrate
```

### API测试

使用 curl 或 Postman 测试：

```bash
# 获取用户列表
curl http://localhost:8000/user/list

# 创建用户
curl -X POST http://localhost:8000/user \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@example.com","password":"123456"}'

# 获取用户详情
curl http://localhost:8000/user/1

# 更新用户
curl -X PUT http://localhost:8000/user/1 \
  -H "Content-Type: application/json" \
  -d '{"email":"new@example.com"}'

# 删除用户
curl -X DELETE http://localhost:8000/user/1
```

---

## 统一响应格式

所有接口返回统一格式：

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
    "items": [...],
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
