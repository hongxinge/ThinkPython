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
| `db-migrate` | 数据库迁移 | `python think.py db-migrate --upgrade` |
| `list-routes` | 列出所有路由 | `python think.py list-routes` |
| `openapi` | 导出契约并体检 | `python think.py openapi` |
| `make-client` | 生成客户端 SDK | `python think.py make-client --lang ts` |

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

依赖 Alembic 实现版本化迁移。迁移在同步驱动下执行，`alembic/env.py`
会自动把应用配置里的异步 URL（如 `mysql+aiomysql`）转换成同步驱动，
无需手工维护两套连接串。

```bash
# 生成迁移脚本（根据模型变更自动对比）
python think.py db-migrate --auto -m "添加订单表"

# 应用迁移到最新版本
python think.py db-migrate --upgrade

# 回滚最近一次迁移
python think.py db-migrate --downgrade

# 查看历史 / 当前版本
python think.py db-migrate --history
python think.py db-migrate --current
```

| 参数 | 作用 |
|---|---|
| `--auto` / `-m` | `--auto` 配合 `-m "描述"` 生成迁移脚本 |
| `--upgrade` | 执行所有未应用的迁移（常用） |
| `--downgrade` | 回滚一步 |
| `--history` | 列出迁移历史 |
| `--current` | 显示数据库当前版本 |
| 无参数 | 简单模式：`create_all` 补建缺失表，不记录版本、不可回滚 |

行为保证：

- **失败即非零退出码**：迁移出错时命令返回 1，发布脚本与 CI 不会把失败当成功；
- **模型导入失败即中止**：避免静默漏表（确需忽略时设 `ALEMBIC_ALLOW_MODEL_IMPORT_ERRORS=true`）；
- **SQLite batch 模式**：改字段时自动重建表，解决 SQLite 不支持 `ALTER COLUMN` 的限制。

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

---

## openapi - 导出契约并体检

```bash
# 导出到 openapi.json（默认），同时打印契约体检报告
python think.py openapi

# 指定输出路径
python think.py openapi --out docs/openapi.json

# 输出到标准输出（体检信息走 stderr，便于管道处理）
python think.py openapi --stdout > openapi.json
```

| 参数 | 作用 |
|---|---|
| `--out` / `-o` | 输出路径，默认 `openapi.json`，父目录会自动创建 |
| `--stdout` | 打印到标准输出；体检信息写到 stderr |

**不依赖 HTTP 端点**：命令直接调用 `app.openapi()`，所以生产环境即使设置
`OPENAPI_ENABLED=false` 关闭了 `/openapi.json`，依然可以导出契约。

体检报告会指出三类会拖累客户端的问题：

| 问题 | 影响 | 修复方式 |
|---|---|---|
| 响应类型是「任意对象」 | 生成的 SDK 里 `data` 是 `unknown` | 路由加 `response_model=ApiResponse[你的模型]` |
| 缺少 summary | SDK 方法没有注释 | 装饰器补 `summary="动作描述"` |
| 写操作缺请求体 | 客户端不知道传什么 | 为 POST/PUT/PATCH 声明 Pydantic 模型 |

---

## make-client - 生成客户端 SDK

```bash
# 生成 TypeScript 客户端到 ./client
python think.py make-client

# 指定目录与服务端地址（写进 README 示例）
python think.py make-client --lang ts --out apps/mobile/sdk --base-url https://api.example.com
```

| 参数 | 作用 |
|---|---|
| `--lang` / `-l` | 目标语言，当前支持 `ts` |
| `--out` / `-o` | 输出目录，默认 `client` |
| `--base-url` | README 示例里的服务端地址 |

生成物：

```
client/
├── README.md        用法、错误处理约定、接口清单
├── package.json     含 build / typecheck 脚本
├── tsconfig.json    严格模式
└── src/
    ├── types.ts     Schema 接口 + ApiResponse<T>
    ├── client.ts    HttpClient（双 Token 自动刷新、幂等键、请求追踪）
    ├── api.ts       按路径生成的类型化方法
    └── index.ts     统一导出
```

```bash
cd client && npm install && npm run typecheck
```

客户端内置的能力（不需要业务代码再实现一遍）：

- access token 过期（业务码 `1004`）自动刷新并重放原请求；
- 并发请求同时过期时只发一次刷新，避免轮换机制互踢；
- 写请求传 `idempotencyKey` 即可弱网安全重试；
- 自动生成 `X-Request-ID`，`ApiError.requestId` 可直接报给后端；
- `NetworkError` 与 `ApiError` 分离，前者可重试、后者是业务拒绝。

类型完整度取决于服务端契约：没声明 `response_model` 的接口，生成的类型是
`unknown`（并在命令行提示数量），不会假装类型完整。
