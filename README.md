# ThinkPython

<p align="center">
  <b>基于 FastAPI 的企业级 Python Web 框架</b><br>
  <small>像 ThinkPHP 一样简单易用，享受 FastAPI 的高性能</small>
</p>

<p align="center">
  <a href="#-一键开始"><strong>一键开始</strong></a> •
  <a href="#-功能特性"><strong>功能特性</strong></a> •
  <a href="#-完整教程"><strong>完整教程</strong></a> •
  <a href="#-项目结构"><strong>项目结构</strong></a> •
  <a href="#-cli工具"><strong>CLI工具</strong></a> •
  <a href="#-常见问题"><strong>常见问题</strong></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/FastAPI-0.104%2B-green" alt="FastAPI 0.104+">
  <img src="https://img.shields.io/badge/License-MIT-orange" alt="MIT License">
</p>

---

## 🎯 为什么选择 ThinkPython？

ThinkPython 是一套**开箱即用**的企业级 Python Web 框架。它的目标是：

✅ **零学习成本** - 如果你用过 ThinkPHP、Spring Boot，你会感觉非常熟悉  
✅ **快速开发** - 一条命令生成 CRUD 三层代码，专注业务逻辑  
✅ **生产就绪** - 内置日志、异常处理、缓存、JWT 认证等企业级功能  
✅ **灵活扩展** - 支持多种数据库、多种缓存，小项目大项目都能胜任  

---

## 🚀 一键开始

### 第1步：下载框架

```bash
# 方式1：使用 Git 克隆
git clone https://gitee.com/hongxinge/think-python.git
cd ThinkPython

# 方式2：直接下载 ZIP 并解压
# 访问 https://gitee.com/hongxinge/think-python 下载
```

### 第2步：安装依赖

```bash
pip install -r requirements.txt
```

> 💡 **提示**：推荐使用 Python 虚拟环境
> ```bash
> # Windows
> python -m venv venv
> venv\Scripts\activate
> 
> # macOS/Linux
> python3 -m venv venv
> source venv/bin/activate
> ```

### 第3步：配置环境

```bash
# 复制示例配置文件
cp .env.example .env   # Linux/macOS
copy .env.example .env # Windows
```

> 🎉 **好消息**：默认配置使用 SQLite + 内存缓存，**无需修改任何配置即可运行**！

### 第4步：启动服务

```bash
python think.py run
```

启动成功后你会看到类似输出：
```
2024-01-01 10:00:00 | INFO | 🚀 ThinkPython v1.0.0 启动中...
2024-01-01 10:00:00 | INFO | 📦 模块模式: single
2024-01-01 10:00:00 | INFO | ✅ 数据库和缓存初始化完成
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 第5步：访问应用

打开浏览器访问：

| 地址 | 说明 |
|------|------|
| http://localhost:8000/docs | 📘 API 文档（Swagger UI） |
| http://localhost:8000/redoc | 📖 API 文档（ReDoc） |
| http://localhost:8000/health | 💚 健康检查 |

**恭喜！你已经成功运行了 ThinkPython 框架！** 🎊

---

## ⚡ 功能特性

| 功能 | 说明 |
|------|------|
| 🔄 **单/多模块切换** | 通过配置自由切换，小项目用单模块，大项目用多模块 |
| 🗄️ **多数据库支持** | MySQL / PostgreSQL / SQLite / MSSQL 一键配置 |
| 💾 **多缓存支持** | Redis / Memory / Memcached 灵活选择 |
| 🛣️ **自动路由注册** | 控制器自动发现，无需手动注册路由 |
| 🏗️ **三层架构** | Controller / Service / Model 清晰分层 |
| 🖥️ **CLI命令行工具** | 类似 ThinkPHP 的 `think` 命令，快速生成代码 |
| 📦 **统一响应格式** | 标准化的 API 响应结构 |
| ⚠️ **全局异常处理** | 优雅的错误处理机制 |
| 🔐 **JWT认证** | 内置 Token 生成与验证 |
| 🌐 **CORS跨域** | 开箱即用的跨域支持 |
| ⚡ **异步支持** | 基于 FastAPI + SQLAlchemy 2.0 全异步 |
| 📝 **日志系统** | 使用 loguru，请求追踪ID自动记录 |

---

## 📖 完整教程

### 教程1：5分钟创建你的第一个 API

让我们从零开始，创建一个完整的「用户管理」CRUD API。

#### 1️⃣ 生成代码文件

使用 CLI 工具一键生成三层代码：

```bash
python think.py make-controller User
python think.py make-model User
python think.py make-service User
```

这会在 `app/single/` 目录下自动生成：
- `controller/user_controller.py` - 控制器（处理HTTP请求）
- `model/user_model.py` - 数据模型（定义数据库表结构）
- `service/user_service.py` - 服务层（编写业务逻辑）

#### 2️⃣ 定义数据模型

打开 `app/single/model/user_model.py`，添加字段：

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

> 💡 `BaseModel` 已自带 `id`（主键）、`created_at`（创建时间）、`updated_at`（更新时间）字段

#### 3️⃣ 编写服务层

打开 `app/single/service/user_service.py`，添加业务方法：

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

#### 4️⃣ 编写控制器

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

#### 5️⃣ 执行数据库迁移

```bash
python think.py db-migrate
```

这会自动创建数据库表。

#### 6️⃣ 启动并测试

```bash
python think.py run
```

使用 curl 测试 API：

```bash
# 创建用户
curl -X POST http://localhost:8000/user \
  -H "Content-Type: application/json" \
  -d '{"username":"zhangsan","email":"zhangsan@example.com","password":"123456"}'

# 返回示例：
# {"code": 200, "message": "创建成功", "data": {"id": 1, "username": "zhangsan", ...}}

# 获取用户列表
curl http://localhost:8000/user/list

# 获取用户详情
curl http://localhost:8000/user/1

# 更新用户
curl -X PUT http://localhost:8000/user/1 \
  -H "Content-Type: application/json" \
  -d '{"email":"new@example.com"}'

# 删除用户
curl -X DELETE http://localhost:8000/user/1
```

> 💡 你也可以直接在浏览器打开 http://localhost:8000/docs 进行可视化测试！

---

### 教程2：使用 MySQL 数据库

#### 1️⃣ 安装 MySQL 驱动

```bash
pip install aiomysql
```

#### 2️⃣ 创建数据库

```sql
CREATE DATABASE thinkpython DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

#### 3️⃣ 修改 `.env` 配置

```env
DB_TYPE=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=thinkpython
DB_USER=root
DB_PASSWORD=你的密码
```

#### 4️⃣ 执行迁移

```bash
python think.py db-migrate
```

完成！现在你的应用已经连接到 MySQL 了。

---

### 教程3：使用 Redis 缓存

#### 1️⃣ 安装 Redis 驱动

```bash
pip install redis
```

#### 2️⃣ 修改 `.env` 配置

```env
CACHE_TYPE=redis
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
```

#### 3️⃣ 在代码中使用缓存

```python
from core.cache import get_cache, set_cache, delete_cache

# 设置缓存（默认过期时间3600秒）
await set_cache("user:1", {"name": "张三"})

# 设置缓存（自定义过期时间60秒）
await set_cache("user:1", {"name": "张三"}, ttl=60)

# 获取缓存
user = await get_cache("user:1")

# 删除缓存
await delete_cache("user:1")
```

---

### 教程4：切换到多模块模式

当项目变大时，可以切换到多模块模式，将代码按业务拆分。

#### 1️⃣ 修改 `.env` 配置

```env
MODULE_MODE=multi
ENABLED_MODULES=admin,api
```

#### 2️⃣ 理解模块结构

```
app/
├── admin/              # 后台管理模块
│   ├── controller/     #   控制器
│   ├── service/        #   服务
│   └── model/          #   模型
└── api/                # API模块
    ├── controller/
    ├── service/
    └── model/
```

#### 3️⃣ 创建新模块

```bash
# 创建订单模块
python think.py make-module order
```

这会自动创建 `app/order/` 目录及子目录。

#### 4️⃣ 访问路径

多模块模式下，访问路径自动带模块前缀：

| 路由 | 访问路径 |
|------|---------|
| admin 模块的 UserController | `/admin/user/list` |
| api 模块的 ProductController | `/api/product/list` |
| order 模块的 OrderController | `/order/order/list` |

### 教程5：使用公共模块（common）

在多模块项目中，多个模块可能需要共用相同的代码。`app/common/` 就是用来存放这些跨模块共享代码的地方。

#### 为什么要用 common 模块？

假设你有一个后台管理系统（admin）和一个对外API（api），它们都需要操作用户数据：

```
❌ 不用 common（错误做法）：
app/admin/model/user_model.py    ← admin 定义了一个 User 模型
app/api/model/user_model.py      ← api 又定义了一个相同的 User 模型（重复代码！）

✅ 使用 common（正确做法）：
app/common/model/user_model.py   ← 所有模块共用的 User 模型
app/admin/service/user_service.py ← admin 引入: from app.common.model.user_model import User
app/api/service/user_service.py   ← api 引入: from app.common.model.user_model import User
```

#### common 模块内置示例

| 文件 | 说明 |
|------|------|
| `common/model/user_model.py` | 公共用户模型，所有模块共用 |
| `common/service/auth_service.py` | 公共认证服务，处理登录验证 |
| `common/controller/base_auth_controller.py` | 需要登录的控制器基类 |

#### 使用示例：创建一个需要登录的接口

```python
# 在你的控制器中继承 BaseAuthController
from app.common.controller.base_auth_controller import BaseAuthController
from fastapi import Depends

class ProfileController(BaseAuthController):
    """用户个人中心控制器"""
    
    def __init__(self):
        super().__init__()
        self._setup_routes()
    
    def _setup_routes(self):
        @self.router.get("/profile", summary="获取个人信息")
        async def get_profile(user_id: int = Depends(self.get_current_user_id)):
            # user_id 已自动从 Token 中解析出来
            return self.success(data={"user_id": user_id})
```

请求时需要在 Header 中携带 Token：
```bash
curl http://localhost:8000/profile \
  -H "Authorization: Bearer eyJhbGciOi..."
```

---

## 🏗️ 项目结构

```
ThinkPython/
├── app/                          # 📁 应用目录（你主要在这里写代码）
│   ├── common/                   #   📌 公共模块（跨模块共享代码）
│   │   ├── controller/           #     公共控制器（如：BaseAuthController）
│   │   ├── service/              #     公共服务（如：AuthService、SmsService）
│   │   └── model/                #     公共模型（如：User 模型，多模块共用）
│   ├── single/                   #   单模块模式（默认）
│   │   ├── controller/           #     控制器层：处理HTTP请求
│   │   ├── service/              #     服务层：业务逻辑
│   │   └── model/                #     数据层：数据库表结构
│   ├── admin/                    #   后台管理模块（多模块模式）
│   └── api/                      #   API模块（多模块模式）
│
├── config/                       # 📁 配置目录
│   ├── app.py                    #   应用配置
│   ├── database.py               #   数据库配置
│   └── cache.py                  #   缓存配置
│
├── core/                         # 📁 核心框架层（一般不需要修改）
│   ├── base_controller.py        #   基础控制器
│   ├── base_service.py           #   基础服务
│   ├── base_model.py             #   基础模型
│   ├── database.py               #   数据库连接管理
│   ├── cache.py                  #   缓存连接管理
│   └── exception.py              #   异常处理
│
├── helpers/                      # 📁 助手函数
│   ├── common.py                 #   常用工具函数
│   ├── response.py               #   响应封装
│   ├── validate.py               #   验证工具
│   └── auth.py                   #   认证工具
│
├── router/                       # 📁 路由管理（自动注册）
├── middleware/                   # 📁 中间件
├── utils/                        # 📁 工具类
├── docs/                         # 📁 文档
│
├── think.py                      # 🖥️ CLI命令行工具
├── main.py                       # 🚀 应用入口
├── requirements.txt              # 📦 依赖包列表
├── .env.example                  # ⚙️ 配置示例
└── .env                          # ⚙️ 你的配置（从.env.example复制）
```

---

## 🖥️ CLI工具

ThinkPython 提供强大的命令行工具，让开发更高效。

### 常用命令速查

| 命令 | 说明 | 示例 |
|------|------|------|
| `run` | 启动开发服务器 | `python think.py run` |
| `make-controller` | 创建控制器 | `python think.py make-controller User` |
| `make-model` | 创建数据模型 | `python think.py make-model User` |
| `make-service` | 创建服务层 | `python think.py make-service User` |
| `make-module` | 创建新模块 | `python think.py make-module order` |
| `db-migrate` | 数据库迁移 | `python think.py db-migrate` |
| `list-routes` | 列出所有路由 | `python think.py list-routes` |

### run - 启动服务器

```bash
# 默认启动（端口8000，开启热重载）
python think.py run

# 指定端口
python think.py run --port 8080

# 指定监听地址
python think.py run --host 127.0.0.1

# 关闭热重载（生产环境使用）
python think.py run --no-reload
```

### make-controller - 创建控制器

```bash
# 在单模块模式下创建
python think.py make-controller User

# 在多模块模式下指定模块
python think.py make-controller User --module admin
```

生成的文件位置：
- 单模块：`app/single/controller/user_controller.py`
- 多模块：`app/admin/controller/user_controller.py`

### make-model - 创建数据模型

```bash
python think.py make-model User
python think.py make-model User --module admin
```

### make-service - 创建服务

```bash
python think.py make-service User
python think.py make-service User --module admin
```

### make-module - 创建新模块

```bash
python think.py make-module order
```

会创建：
```
app/order/
├── __init__.py
├── controller/
│   └── __init__.py
├── service/
│   └── __init__.py
└── model/
    └── __init__.py
```

### db-migrate - 数据库迁移

```bash
python think.py db-migrate
```

自动扫描所有模型并创建数据库表。

### list-routes - 列出路由

```bash
python think.py list-routes
```

输出示例：
```
方法         路径                              描述                            
--------------------------------------------------------------------------------
GET          /health                           健康检查                        
GET          /user/list                        用户列表                        
GET          /user/{user_id}                   用户详情                        
POST         /user                             创建用户                        
PUT          /user/{user_id}                   更新用户                        
DELETE       /user/{user_id}                   删除用户                        
```

---

## 📦 统一响应格式

所有 API 接口返回统一的 JSON 格式，方便前端处理。

### 成功响应

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "username": "zhangsan",
    "email": "zhangsan@example.com"
  }
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
  "code": 404,
  "message": "用户 1 不存在",
  "data": null
}
```

### 参数验证失败响应

```json
{
  "code": 422,
  "message": "参数验证失败",
  "data": [
    {
      "field": "body.username",
      "message": "field required"
    }
  ]
}
```

---

## ⚙️ 配置说明

所有配置通过 `.env` 文件管理。复制 `.env.example` 为 `.env` 后修改。

### 应用配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `APP_NAME` | 应用名称 | `ThinkPython` |
| `APP_VERSION` | 应用版本 | `1.0.0` |
| `APP_DEBUG` | 调试模式（生产环境设为False） | `True` |
| `TIMEZONE` | 时区 | `Asia/Shanghai` |
| `LANGUAGE` | 语言 | `zh-CN` |

### 模块模式

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `MODULE_MODE` | 模块模式 | `single` |
| `ENABLED_MODULES` | 启用模块列表 | `admin,api` |
| `DEFAULT_MODULE` | 默认模块 | `api` |

### 数据库配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DB_ENABLED` | 是否启用数据库 | `True` |
| `DB_TYPE` | 数据库类型 | `sqlite` |
| `DB_HOST` | 数据库主机 | `127.0.0.1` |
| `DB_PORT` | 数据库端口 | `3306` |
| `DB_NAME` | 数据库名称 | `thinkpython` |
| `DB_USER` | 数据库用户名 | `root` |
| `DB_PASSWORD` | 数据库密码 | `` |
| `DB_SQLITE_PATH` | SQLite文件路径 | `./data/database.db` |

### 缓存配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `CACHE_ENABLED` | 是否启用缓存 | `True` |
| `CACHE_TYPE` | 缓存类型 | `memory` |
| `CACHE_DEFAULT_TTL` | 默认过期时间(秒) | `3600` |

### JWT认证配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `JWT_SECRET` | JWT密钥（⚠️生产环境必须修改） | `your-secret-key...` |
| `JWT_ALGORITHM` | 加密算法 | `HS256` |
| `JWT_EXPIRE_HOURS` | Token过期时间(小时) | `24` |

> ⚠️ **安全提醒**：生产环境务必修改 `JWT_SECRET` 为强密钥！

---

## 📚 核心概念

### 三层架构

ThinkPython 采用经典的三层架构，职责清晰：

```
HTTP请求 → Controller → Service → Model → 数据库
              ↓             ↓           ↓
           参数验证      业务逻辑     表结构定义
           响应返回      数据处理     数据映射
```

| 层级 | 职责 | 位置 |
|------|------|------|
| **Controller** | 接收HTTP请求，参数验证，返回响应 | `app/{module}/controller/` |
| **Service** | 处理业务逻辑，调用Model操作数据 | `app/{module}/service/` |
| **Model** | 定义数据库表结构，数据映射 | `app/{module}/model/` |

### 依赖注入

使用 FastAPI 的 `Depends` 实现数据库会话注入：

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db

@self.router.get("/user/list")
async def get_users(db: AsyncSession = Depends(get_db)):
    # db 是自动管理的数据库会话
    # 请求结束时自动提交/回滚并关闭连接
    service = UserService(db)
    return await service.get_all()
```

### 异常处理

框架内置多种异常类，可抛出异常自动返回统一格式：

```python
from core.exception import NotFoundException, UnauthorizedException

@self.router.get("/user/{user_id}")
async def get_user(user_id: int):
    user = await service.get_by_id(user_id)
    if not user:
        raise NotFoundException(f"用户 {user_id} 不存在")
    # 自动返回: {"code": 404, "message": "用户 1 不存在", "data": null}
```

---

## ❓ 常见问题

### Q1: 启动时提示 "模块未找到" 错误？

**原因**：依赖未安装或安装不完整。

**解决**：
```bash
# 重新安装依赖
pip install -r requirements.txt --upgrade

# 如果使用虚拟环境，确保已激活
```

### Q2: SQLite 数据库文件在哪里？

默认在 `./data/database.db`。如果没有 `data` 目录，会自动创建。

你也可以修改路径：
```env
DB_SQLITE_PATH=D:/my_project/data/mydb.db
```

### Q3: 如何查看执行的 SQL 语句？

开发时可以开启 SQL 打印：
```env
DB_ECHO=True
```

### Q4: 热重载不生效？

确保在调试模式下：
```env
APP_DEBUG=True
```

或者使用命令：
```bash
python think.py run
```

### Q5: 跨域问题如何解决？

框架默认允许所有跨域请求（`CORS_ORIGINS=*`）。生产环境建议指定域名：
```env
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
```

### Q6: 如何自定义响应格式？

在控制器中使用 `self.success()` 和 `self.error()` 方法：
```python
# 成功响应
return self.success(data={"key": "value"}, message="自定义消息")

# 错误响应
return self.error("错误消息", code=400)

# 分页响应
return self.paginate(items, total, page, page_size)
```

### Q7: 如何添加中间件？

在 `middleware/__init__.py` 中定义，然后在 `main.py` 的 `create_app()` 函数中注册：
```python
from middleware import your_middleware

app.middleware("http")(your_middleware)
```

### Q8: 生产部署需要注意什么？

1. 设置 `APP_DEBUG=False`
2. 修改 `JWT_SECRET` 为强密钥
3. 设置正确的 `CORS_ORIGINS`
4. 使用 Gunicorn 或 Uvicorn workers 运行
5. 配置 Nginx 反向代理
6. 使用 MySQL/PostgreSQL 替代 SQLite

---

## 📄 许可证

ThinkPython 采用 [MIT License](LICENSE) 开源协议，完全免费，可商用。

---

## 🤝 贡献

欢迎参与项目贡献！

1. Fork 本仓库
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的改动 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

---

## 💬 支持与反馈

- 📖 详细文档：[docs/](docs/)
- 🐛 问题反馈：[gitee Issues](https://gitee.com/hongxinge/think-python/issues)
- ⭐ 觉得好用请 Star 支持，让更多人看到！

---

<p align="center">
  <b>ThinkPython</b> - 让 Python Web 开发更简单 🐍
</p>
