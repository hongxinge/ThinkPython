# ThinkPython

<p align="center">
  <b>基于 FastAPI 的企业级 Python Web 框架</b><br>
  <small>像 ThinkPHP 一样简单易用，享受 FastAPI 的高性能</small>
</p>

<p align="center">
  <a href="#-快速开始"><strong>快速开始</strong></a> •
  <a href="#-功能特性"><strong>功能特性</strong></a> •
  <a href="#-项目结构"><strong>项目结构</strong></a> •
  <a href="#-配置说明"><strong>配置说明</strong></a> •
  <a href="#-文档中心"><strong>文档中心</strong></a> •
  <a href="#-常见问题"><strong>常见问题</strong></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/FastAPI-0.115%2B-green" alt="FastAPI 0.115+">
  <img src="https://img.shields.io/badge/License-MIT-orange" alt="MIT License">
</p>

---

## 🎯 为什么选择 ThinkPython？

✅ **零学习成本** - 如果你用过 ThinkPHP、Spring Boot，你会感觉非常熟悉  
✅ **快速开发** - 一条命令生成 CRUD 三层代码，专注业务逻辑  
✅ **生产就绪** - 内置日志、异常处理、缓存、JWT 认证等企业级功能  
✅ **灵活扩展** - 支持多种数据库、多种缓存，小项目大项目都能胜任  

---

## 🚀 快速开始

### 1. 安装

```bash
# GitHub
git clone https://github.com/hongxinge/ThinkPython.git
cd ThinkPython

# 或 Gitee（国内镜像，更快）
git clone https://gitee.com/hongxinge/think-python.git
cd think-python

pip install -r requirements.txt
```

### 2. 启动

```bash
python think.py run
```

> 🎉 **零配置启动**：默认使用 SQLite + 内存缓存，无需修改任何配置！

### 3. 访问

| 地址 | 说明 |
|------|------|
| http://localhost:8000/docs | 📘 API 文档（Swagger UI，仅 debug 模式） |
| http://localhost:8000/openapi.json | 📄 OpenAPI 规范，可导入 Apifox / Postman 生成客户端 SDK |
| http://localhost:8000/health | 💚 存活检查（不查数据库） |
| http://localhost:8000/health/ready | ✅ 就绪检查（校验数据库与缓存） |

---

## ⚡ 功能特性

ThinkPython 是**为客户端 App / 小程序 / 前端提供 JSON API** 的后端框架，
所有能力都围绕这一目标设计。

| 功能 | 说明 |
|------|------|
| 📱 **客户端 API 优先** | 纯 JSON、无 Session/Cookie、Bearer Token、统一错误码，见 [客户端 API 契约](docs/api-contract.md) |
| 🔐 **双 Token 认证** | access + refresh 双令牌，支持轮换、登出吊销、改密后旧 Token 立即失效 |
| 🛡️ **暴力破解防护** | IP 维度限流 + 账号维度失败锁定（423），两级防护 |
| 🎫 **接口级权限** | 角色 + 权限标识，`@require_permission` 一行声明，见 [权限控制](docs/rbac.md) |
| ♻️ **幂等重试** | 客户端带 `Idempotency-Key`，服务端回放首次结果，弱网重试不重复下单 |
| ⚡ **一键生成客户端 SDK** | `make-client` 从契约生成 TypeScript 客户端，内置刷新/幂等/追踪，见 [SDK 生成](docs/cli.md#make-client---生成客户端-sdk) |
| 🚀 **响应压缩** | JSON 接口实测省 80% 流量，小响应与图片/视频自动跳过 |
| 📤 **分片上传** | 大文件切分逐片上传，断线只补缺失分片，见 [分片上传](docs/api-contract.md#72-大文件分片上传) |
| 🧱 **纯 ASGI 中间件** | 日志/认证/幂等零 `BaseHTTPMiddleware` 开销，单层省约 110µs/请求 |
| 🔄 **单/多模块切换** | 配置自由切换，小项目用单模块，大项目用多模块 |
| 🗄️ **多数据库支持** | MySQL / PostgreSQL / SQLite / MSSQL 一键配置 |
| 💾 **多缓存支持** | Redis（生产）/ Memory（开发）零侵入切换 |
| 🛣️ **自动路由注册** | 控制器自动发现，无需手动注册；支持 `/api/v1` 版本前缀 |
| 🏗️ **三层架构** | Controller / Service / Model 清晰分层 |
| 🖥️ **CLI 工具** | 类似 ThinkPHP 的 `think` 命令，快速生成代码 |
| 🔍 **可观测性** | request_id 贯穿日志与错误响应、慢请求告警、`/health` + `/health/ready` |
| 📦 **Excel 工具** | 内置 Excel 导入导出，支持样式、自动列宽 |
| 📁 **文件工具** | 内置文件上传下载，支持格式验证、MIME 校验、路径越界防护 |

---

## 🏗️ 项目结构

```
ThinkPython/
├── app/                          # 应用目录（你主要在这里写代码）
│   ├── common/                   # 公共模块（跨模块共享代码）
│   ├── single/                   # 单模块模式（默认）
│   ├── admin/                    # 后台管理模块（多模块）
│   └── api/                      # API 模块（多模块）
├── config/                       # 配置目录
├── core/                         # 核心框架层
├── helpers/                      # 助手函数
├── router/                       # 路由管理（自动注册）
├── middleware/                   # 中间件
├── utils/                        # 工具类（Excel、文件）
├── uploads/                      # 上传文件目录
├── think.py                      # CLI 命令行工具
├── main.py                       # 应用入口
└── requirements.txt              # 依赖包列表
```

---

## ⚙️ 配置说明

所有配置通过 `.env` 文件管理（从 `.env.example` 复制）：

### 核心配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `APP_DEBUG` | 调试模式 | `True` |
| `MODULE_MODE` | 模块模式 | `single` / `multi` |
| `ENABLED_MODULES` | 启用模块 | `*`（自动发现） |

### 数据库

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DB_TYPE` | 数据库类型 | `sqlite` |
| `DB_HOST` / `DB_PORT` / `DB_NAME` | 数据库连接 | 按需配置 |
| `DB_USER` / `DB_PASSWORD` | 数据库账号 | 按需配置 |

### 缓存

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `CACHE_TYPE` | 缓存类型 | `memory` |
| `REDIS_HOST` / `REDIS_PORT` | Redis 连接 | 按需配置 |

### JWT 认证

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `JWT_SECRET` | JWT 密钥（⚠️ 生产环境必须修改） | `your-secret-key...` |
| `JWT_EXPIRE_HOURS` | Token 过期时间 | `24` |
| `AUTH_ENABLED` | 是否启用认证中间件 | `true` |

> ⚠️ **安全提醒**：生产环境务必修改 `JWT_SECRET` 为强密钥！

### 双 Token 机制

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `JWT_ACCESS_TOKEN_EXPIRE_HOURS` | Access Token 过期时间 | `2` |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | Refresh Token 过期时间 | `7` |
| `JWT_REFRESH_TOKEN_ROTATE` | Refresh Token 轮换机制 | `true` |

### API 限流

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `RATE_LIMIT_ENABLED` | 是否启用限流 | `false` |
| `RATE_LIMIT_BACKEND` | 限流后端 | `memory` |
| `RATE_LIMIT_IP_REQUESTS` | IP 每分钟最大请求数 | `100` |

---

## 🖥️ CLI 工具速查

```bash
python think.py run                  # 启动服务器
python think.py make-crud user       # 根据数据库表结构生成 CRUD 三层代码
python think.py make-controller User # 创建控制器
python think.py make-model User      # 创建数据模型
python think.py make-service User    # 创建服务层
python think.py make-module order    # 创建新模块
python think.py db-migrate --auto -m "描述"  # 生成迁移脚本
python think.py db-migrate --upgrade         # 应用迁移
python think.py list-routes          # 列出所有路由
python think.py openapi              # 导出 OpenAPI 契约 + 契约体检
python think.py make-client --lang ts --out client   # 生成 TypeScript 客户端 SDK
```

> 💡 **make-crud**：配置好数据库后，一条命令 `python think.py make-crud user` 即可根据 `user` 表结构自动生成 Model、Controller、Service 三层完整代码，包含字段类型、注释、Pydantic 验证等，详见 [make-crud 文档](docs/make-crud.md)。

---

## 📖 文档中心

完整教程已移至 `docs/` 目录，按需查阅：

| 文档 | 说明 |
|------|------|
| [客户端 API 契约](docs/api-contract.md) | **客户端团队必读**：错误码、双 Token、追踪、限流退避 |
| [5分钟创建第一个 API](docs/getting-started.md) | 从零开始，创建完整的 CRUD 接口 |
| [数据库配置](docs/database.md) | MySQL / PostgreSQL / MSSQL 配置教程 |
| [缓存使用](docs/cache.md) | Redis / Memory 配置与使用教程 |
| [多模块模式](docs/modules.md) | 项目拆分与模块管理 |
| [公共模块](docs/common.md) | 跨模块共享代码的最佳实践 |
| [认证机制](docs/auth.md) | JWT 认证、免验证路由配置 |
| [权限控制](docs/rbac.md) | 接口级 RBAC：角色、权限、`@require_permission` |
| [Excel 工具](docs/excel.md) | Excel 导入导出使用指南 |
| [文件工具](docs/file.md) | 文件上传下载使用指南 |

---

## 📦 统一响应格式

成功：

```json
{"code": 200, "message": "success", "data": {}}
```

失败（HTTP 状态码为真实语义值，`code` 为业务码，客户端按 `code` 判断）：

```json
{
  "code": 1004,
  "message": "Token 已过期，请刷新或重新登录",
  "data": null,
  "request_id": "3f2b8c1e-..."
}
```

| 方法 | 说明 |
|------|------|
| `self.success(data, message)` | 成功响应 |
| `self.error(message, code, http_status=None)` | 错误响应，业务码自动映射 HTTP 状态码 |
| `self.paginate(items, total, page, page_size)` | 分页响应 |

完整的错误码表与客户端接入方式见 [客户端 API 契约](docs/api-contract.md)。

---

## ❓ 常见问题

### Q: 如何切换多模块模式？

修改 `.env`：
```env
MODULE_MODE=multi
ENABLED_MODULES=admin,api
```

### Q: SQLite 数据库文件在哪？

默认在 `./data/database.db`，会自动创建。

### Q: 如何免验证登录、注册等接口？

在控制器中配置白名单：
```python
class AuthController(BaseController):
    SKIP_AUTH_ROUTES = ["POST /auth/login", "POST /auth/register"]
```
详见 [认证机制文档](docs/auth.md)。

### Q: 如何查看执行的 SQL 语句？

```env
DB_ECHO=True
```

### Q: 生产部署方式有哪些？

ThinkPython 支持多种部署方式，按需选择：

| 部署方式 | 适用场景 | 说明 |
|---------|---------|------|
| Uvicorn | 小型项目 | `uvicorn main:app --host 0.0.0.0 --port 8000` |
| Gunicorn | 中型项目 | `gunicorn -c deploy/gunicorn.conf.py main:app` |
| Gunicorn + systemd | 生产常驻（推荐） | `sudo systemctl enable --now thinkpython` |

完整的部署配置请参考 `deploy/` 目录，包含 Gunicorn 配置、systemd 服务单元、
Nginx 反向代理与 SSL 示例、MySQL 初始化脚本。详见 [部署指南](deploy/README.md)。

---

## 📄 许可证

ThinkPython 采用 [MIT License](LICENSE) 开源协议，完全免费，可商用。

---

## 🤝 贡献

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/your-feature`)
3. 提交改动 (`git commit -m 'Add your feature'`)
4. 推送分支 (`git push origin feature/your-feature`)
5. 提交 Pull Request

提交前请运行测试套件：

```bash
# 在已激活的项目虚拟环境中安装运行依赖 + 测试依赖
pip install -r requirements-dev.txt

# 在项目根目录执行（无需手动设置 PYTHONPATH）
python -m pytest tests/ -q
```

> 使用系统 Python 直接运行会因缺少 fastapi / sqlalchemy / httpx 等包而报
> `errors during collection`，请先创建并激活虚拟环境。

测试约定：

- `requirements.txt` 只含运行依赖，`requirements-dev.txt` 额外包含 pytest / pytest-asyncio / httpx。
- `pytest.ini` + `conftest.py` 统一管理测试路径与共享 fixture，克隆后即可直接运行。
- `tests/test_regressions_p0.py` 中的 `xfail(strict=True)` 用例对应**已确认但尚未修复**的缺陷；修复后会自动转为 XPASS 并导致测试失败，此时请移除对应标记，避免缺陷回归。

---

<p align="center">
  <b>ThinkPython</b> - 让 Python Web 开发更简单 🐍
</p>
