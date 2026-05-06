# ThinkPython

<p align="center">
  <b>基于 FastAPI 的企业级 Python Web 框架</b><br>
  <small>像 ThinkPHP 一样简单易用，享受 FastAPI 的高性能</small>
</p>

<p align="center">
  <a href="#功能特性">功能特性</a> •
  <a href="#快速开始">快速开始</a> •
  <a href="#文档">文档</a> •
  <a href="#项目结构">项目结构</a> •
  <a href="#cli工具">CLI工具</a>
</p>

---

## 功能特性

- **单/多模块切换** - 通过配置自由切换，小项目用单模块，大项目用多模块
- **多数据库支持** - MySQL / PostgreSQL / SQLite / MSSQL 一键配置
- **多缓存支持** - Redis / Memory / Memcached 灵活选择
- **自动路由注册** - 控制器自动发现，无需手动注册路由
- **三层架构** - Controller / Service / Model 清晰分层
- **CLI命令行工具** - 类似 ThinkPHP 的 `think` 命令，快速生成代码
- **统一响应格式** - 标准化的 API 响应结构
- **全局异常处理** - 优雅的错误处理机制
- **JWT认证** - 内置 Token 生成与验证
- **CORS跨域** - 开箱即用的跨域支持
- **异步支持** - 基于 FastAPI + SQLAlchemy 2.0 全异步

---

## 快速开始

### 1. 环境要求

- Python 3.8+
- pip 包管理器

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境

复制 `.env.example` 为 `.env` 并修改配置：

```bash
cp .env.example .env
```

默认使用 **SQLite** 数据库和 **内存缓存**，零配置即可运行。

### 4. 启动服务

```bash
# 方式一：使用 CLI 工具（推荐）
python think.py run

# 方式二：直接运行
python main.py

# 指定端口
python think.py run --port 8080
```

### 5. 访问应用

- 首页：http://localhost:8000/
- API文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

---

## 文档

| 文档 | 说明 |
|------|------|
| [快速开始](#快速开始) | 5分钟上手指南 |
| [配置说明](docs/config.md) | 所有配置项详细说明 |
| [CLI工具](docs/cli.md) | 命令行工具使用指南 |
| [数据库](docs/database.md) | 数据库配置与迁移 |
| [缓存](docs/cache.md) | 缓存配置与使用 |
| [API示例](docs/api.md) | 完整CRUD示例 |
| [部署指南](docs/deploy.md) | Docker与生产部署 |

---

## 项目结构

```
ThinkPython/
├── app/                          # 应用目录
│   ├── single/                   # 单模块模式（默认）
│   │   ├── controller/           #   控制器层
│   │   ├── service/              #   服务层
│   │   └── model/                #   数据层
│   ├── admin/                    # 后台管理模块
│   └── api/                      # API模块
├── config/                       # 配置目录
│   ├── app.py                    # 应用配置
│   ├── database.py               # 数据库配置
│   └── cache.py                  # 缓存配置
├── core/                         # 核心框架层
│   ├── base_controller.py        # 基础控制器
│   ├── base_service.py           # 基础服务
│   ├── base_model.py             # 基础模型
│   ├── database.py               # 数据库连接管理
│   ├── cache.py                  # 缓存连接管理
│   └── exception.py              # 异常处理
├── helpers/                      # 助手函数
│   ├── common.py                 # 常用工具函数
│   ├── response.py               # 响应封装
│   ├── validate.py               # 验证工具
│   └── auth.py                   # 认证工具
├── router/                       # 路由管理
├── middleware/                   # 中间件
├── utils/                        # 工具类
├── think.py                      # CLI命令行工具
├── main.py                       # 应用入口
├── requirements.txt              # 依赖
└── .env                          # 环境配置
```

---

## CLI工具

ThinkPython 提供类似 ThinkPHP 的 CLI 工具，位于 `think.py`。

### 常用命令

```bash
# 启动开发服务器
python think.py run

# 创建控制器
python think.py make-controller User

# 创建模型
python think.py make-model User

# 创建服务
python think.py make-service User

# 一键创建CRUD三层
python think.py make-controller Product
python think.py make-model Product
python think.py make-service Product

# 创建新模块
python think.py make-module order

# 数据库迁移
python think.py db-migrate

# 列出所有路由
python think.py list-routes
```

---

## 单模块 vs 多模块

### 单模块模式（默认）

适合小型项目、API服务、快速开发。

```env
MODULE_MODE=single
```

所有代码在 `app/single/` 目录下。

### 多模块模式

适合中大型项目、团队协作。

```env
MODULE_MODE=multi
ENABLED_MODULES=admin,api
```

代码按模块分布在 `app/admin/`、`app/api/` 等目录下。

访问路径：
- `/admin/xxx` - 后台管理接口
- `/api/xxx` - API接口

---

## 数据库配置

### 使用 SQLite（开发环境推荐）

```env
DB_TYPE=sqlite
DB_SQLITE_PATH=./data/database.db
```

### 使用 MySQL（生产环境推荐）

```env
DB_TYPE=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=thinkpython
DB_USER=root
DB_PASSWORD=your_password
```

### 数据库迁移

```bash
python think.py db-migrate
```

---

## 许可证

ThinkPython 采用 [MIT License](LICENSE) 开源协议，免费使用。

---

## 贡献

欢迎提交 Issue 和 Pull Request！

---

## 支持

- 📖 文档：[查看完整文档](docs/)
- 💬 问题反馈：[提交Issue](https://github.com/yourusername/ThinkPython/issues)
- ⭐ 觉得好用请 Star 支持
