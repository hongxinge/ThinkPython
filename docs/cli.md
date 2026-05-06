# CLI命令行工具使用指南

ThinkPython 提供类似 ThinkPHP 的 CLI 工具，让开发更高效。

## 基础用法

```bash
python think.py <command> [arguments]
```

## 可用命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `run` | 启动开发服务器 | `python think.py run` |
| `make-controller` | 创建控制器 | `python think.py make-controller User` |
| `make-model` | 创建数据模型 | `python think.py make-model User` |
| `make-service` | 创建服务层 | `python think.py make-service User` |
| `make-module` | 创建新模块 | `python think.py make-module order` |
| `db-migrate` | 数据库迁移 | `python think.py db-migrate` |
| `list-routes` | 列出所有路由 | `python think.py list-routes` |

---

## run - 启动服务器

```bash
# 默认启动（端口8000，开启热重载）
python think.py run

# 指定端口
python think.py run --port 8080

# 指定监听地址
python think.py run --host 127.0.0.1

# 关闭热重载（生产环境）
python think.py run --no-reload
```

---

## make-controller - 创建控制器

```bash
# 在默认模块创建控制器
python think.py make-controller User

# 指定模块创建控制器
python think.py make-controller User --module admin

# 创建后会在对应模块的 controller 目录生成文件
# app/single/controller/user_controller.py (单模块)
# app/admin/controller/user_controller.py (多模块)
```

生成示例：

```python
"""
User 控制器
"""
from pydantic import BaseModel
from core.base_controller import BaseController
from helpers.response import success_response, error_response


class UserRequest(BaseModel):
    """User请求模型"""
    pass


class UserController(BaseController):
    """User控制器"""
    
    def __init__(self):
        super().__init__()
        self._setup_routes()
    
    def _setup_routes(self):
        @self.router.get("/user/list", summary="User列表")
        async def get_list(page: int = 1, page_size: int = 10):
            return self.success(data={"items": [], "total": 0})
        
        @self.router.get("/user/{item_id}", summary="User详情")
        async def get_detail(item_id: int):
            return self.success(data={"id": item_id})
        
        @self.router.post("/user", summary="创建User")
        async def create(request: UserRequest):
            return self.success(data=request.dict(), message="创建成功")
```

---

## make-model - 创建数据模型

```bash
# 创建模型
python think.py make-model User

# 指定模块
python think.py make-model User --module admin
```

生成示例：

```python
"""
User 模型
"""
from sqlalchemy import Column, String, Integer, Text
from core.base_model import BaseModel


class User(BaseModel):
    """User模型"""
    
    __tablename__ = "users"
    
    # TODO: 添加字段
    # name = Column(String(100), nullable=False, comment="名称")
    # status = Column(Integer, default=1, comment="状态")
```

---

## make-service - 创建服务

```bash
# 创建服务
python think.py make-service User

# 指定模块
python think.py make-service User --module admin
```

生成示例：

```python
"""
User 服务
"""
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from core.base_service import BaseService


class UserService(BaseService):
    """User服务"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db)
        # self.model_class = User  # 关联到User模型
    
    async def get_list(self, page: int = 1, page_size: int = 10) -> tuple:
        """获取列表"""
        return [], 0
    
    async def get_detail(self, item_id: int) -> Optional[Dict[str, Any]]:
        """获取详情"""
        return None
```

---

## make-module - 创建新模块

```bash
# 创建新模块
python think.py make-module order

# 会创建以下目录结构：
# app/order/
# ├── __init__.py
# ├── controller/
# │   └── __init__.py
# ├── service/
# │   └── __init__.py
# └── model/
#     └── __init__.py
```

创建后自动更新 `.env` 中的 `ENABLED_MODULES` 配置。

---

## db-migrate - 数据库迁移

```bash
# 执行数据库迁移（创建表）
python think.py db-migrate
```

---

## list-routes - 列出路由

```bash
# 查看当前已注册的所有路由
python think.py list-routes
```

输出示例：

```
方法         路径                                       描述                            
--------------------------------------------------------------------------------
GET          /                                          首页                            
GET          /info                                      系统信息                        
GET          /user/list                                 用户列表                        
GET          /user/{user_id}                            获取用户详情                    
POST         /user                                      创建用户                        
```
