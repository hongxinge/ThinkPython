# 配置说明

所有配置项通过 `.env` 文件管理，修改后**必须重启进程**才生效（配置在模块导入时一次性求值）。

仓库提供两套模板，按场景选用，不要混用：

| 模板 | 场景 | 形态 |
|---|---|---|
| `.env.example` | 本地开发 | `single` + SQLite + 内存缓存 + 不限流 |
| `deploy/.env.example` | 生产部署 | `multi` + MySQL + Redis + 限流 |

---

## 应用配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `APP_NAME` | 应用名称 | `ThinkPython` |
| `APP_VERSION` | 应用版本 | `1.0.0` |
| `APP_DEBUG` | 调试模式 | `True` |
| `TIMEZONE` | 时区（日志时间戳） | `Asia/Shanghai` |
| `LANGUAGE` | 语言 | `zh-CN` |
| `ERROR_HTTP_MODE` | 错误响应契约 | `standard` |
| `TRUST_PROXY` | 是否采信代理传来的真实 IP | `false` |

`TRUST_PROXY` 说明：

- 直连部署（客户端直接访问应用）保持 `false`，防止伪造 `X-Forwarded-For` 绕过限流；
- 部署在 Nginx / 云负载均衡之后设为 `true`，否则 `request.client.host` 拿到的
  是代理地址，**所有用户会共用一个限流桶**。

`ERROR_HTTP_MODE` 说明：

- `standard`（推荐）：`self.error(code=401)` 返回真实 HTTP 401；
- `legacy`：一律返回 HTTP 200，前端只读 `body.code`（兼容旧前端）。

`APP_DEBUG=False` 时会同时：关闭 `/docs` 与 `/redoc`、隐藏异常堆栈、
在检测到默认 `JWT_SECRET` 时**拒绝启动**。

---

## 模块模式

| 变量 | 说明 | 可选值 | 默认值 |
|------|------|--------|--------|
| `MODULE_MODE` | 模块模式 | `single` / `multi` | `single` |
| `ENABLED_MODULES` | 启用模块列表 | 逗号分隔 | `admin,api` |
| `DEFAULT_MODULE` | 默认模块 | 模块名 | `api` |
| `ROUTE_PREFIX` | 全局路由前缀 | 字符串 | 空 |

`ROUTE_PREFIX` 会加在**所有业务路由**之前，实现版本化命名空间：

```env
ROUTE_PREFIX=/api/v1
```

此时 `/api/auth/login` 变为 `/api/v1/api/auth/login`。`/health`、`/docs` 等
应用级路由不受影响。

### 单模块模式

```env
MODULE_MODE=single
```

所有代码放在 `app/single/` 目录下，访问路径无前缀。

### 多模块模式

```env
MODULE_MODE=multi
ENABLED_MODULES=admin,api
DEFAULT_MODULE=api
```

代码按模块分布在 `app/admin/`、`app/api/` 等目录。
访问路径带模块前缀：`/admin/xxx`、`/api/xxx`。

---

## CORS配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `CORS_ORIGINS` | 允许的跨域来源 | `*` |

多个来源用逗号分隔：`http://localhost:3000,https://example.com`

---

## 日志配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `TIMEZONE` | 日志时间戳时区 | `Asia/Shanghai` |
| `LOG_SLOW_REQUEST_MS` | 慢请求阈值（毫秒） | `500` |

`LOG_SLOW_REQUEST_MS`：超过该耗时的请求以 WARNING 级别记录，便于直接按
日志级别筛出慢接口，无需额外接入 APM。

可选级别：`DEBUG` < `INFO` < `WARNING` < `ERROR` < `CRITICAL`

日志行为（由 `core/logger.py` 统一配置）：

- **控制台**：输出到 stdout，容器环境由平台采集；
- **文件**：`logs/app.log`，按 10MB 轮转，保留 5 份，异步写入不阻塞事件循环；
- **时区**：按 `TIMEZONE` 渲染，与数据库时间口径一致；
- **降级**：日志目录不可写时自动仅用控制台，不影响服务启动。

生产环境建议 `LOG_LEVEL=INFO`；排查问题时临时改 `DEBUG` 并重启。

---

## 数据库配置

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
| `DB_POOL_SIZE` | 连接池大小 | `10` |
| `DB_MAX_OVERFLOW` | 最大溢出连接数 | `20` |
| `DB_POOL_RECYCLE` | 连接回收时间(秒) | `3600` |
| `DB_POOL_PRE_PING` | 连接前检测 | `True` |
| `DB_ECHO` | 打印SQL语句 | `False` |

### MySQL配置示例

```env
DB_TYPE=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=thinkpython
DB_USER=root
DB_PASSWORD=123456
```

### PostgreSQL配置示例

```env
DB_TYPE=postgresql
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=thinkpython
DB_USER=postgres
DB_PASSWORD=123456
```

### SQLite配置示例

```env
DB_TYPE=sqlite
DB_SQLITE_PATH=./data/database.db
```

---

## 缓存配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `CACHE_ENABLED` | 是否启用缓存 | `True` |
| `CACHE_TYPE` | 缓存类型 | `memory` |
| `CACHE_DEFAULT_TTL` | 默认过期时间(秒) | `3600` |
| `CACHE_PREFIX` | 缓存键前缀 | `thinkpython:` |

### Redis配置

```env
CACHE_TYPE=redis
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_MAX_CONNECTIONS=20
```

### Memory配置（开发环境）

```env
CACHE_TYPE=memory
MEMORY_CACHE_MAX_SIZE=1000
MEMORY_CACHE_TTL=300
```

> 框架只支持 `memory` 与 `redis` 两种后端。Memcached 未实现，
> 设置 `CACHE_TYPE=memcached` 会在启动时直接报错并提示可选值。

---

## 认证与 Token 生命周期

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `AUTH_ENABLED` | 是否启用全局认证中间件 | `true` |
| `JWT_SECRET` | 签名密钥（生产必填，默认值会被拒绝启动） | — |
| `JWT_ACCESS_TOKEN_EXPIRE_HOURS` | access_token 有效期（小时） | `2` |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | refresh_token 有效期（天） | `7` |
| `JWT_REFRESH_TOKEN_ROTATE` | 刷新时轮换 refresh_token | `true` |
| `TOKEN_BLACKLIST_ENABLED` | 登出后 Token 是否立即失效 | `false` |
| `TOKEN_VERSION_CHECK` | 改密/禁用后旧 Token 是否立即失效 | `true` |
| `TOKEN_VERSION_CACHE_TTL` | 版本号缓存秒数，0 表示每次查库 | `60` |
| `LOGIN_MAX_ATTEMPTS` | 登录失败锁定阈值 | `5` |
| `LOGIN_LOCK_DURATION` | 锁定时长（分钟） | `30` |

**Token 失效矩阵**（客户端据此决定动作，详见 [客户端 API 契约](api-contract.md)）：

| 触发条件 | 失效对象 | 依赖配置 |
|---|---|---|
| access_token 过期 | 自身 | — |
| 调 `/auth/refresh` 轮换 | 旧 refresh_token | `JWT_REFRESH_TOKEN_ROTATE=true` |
| 调 `/auth/logout` | 当前 access_token | `TOKEN_BLACKLIST_ENABLED=true` |
| 改密码 / 禁用账号 | 该用户全部 Token | `TOKEN_VERSION_CHECK=true` |

`TOKEN_VERSION_CHECK` 的性能取舍：

- 开启（推荐）：每次请求比对版本号，默认走缓存 60 秒，命中时零数据库开销；
- 关闭：纯无状态 JWT，零额外查询，但改密后旧 Token 会一直有效到自然过期。

---

## 限流

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `RATE_LIMIT_ENABLED` | 是否启用限流 | `false` |
| `RATE_LIMIT_BACKEND` | `memory` / `redis` | `memory` |
| `RATE_LIMIT_IP_REQUESTS` / `_PERIOD` | 单 IP 窗口内请求数 / 窗口秒数 | `100` / `60` |
| `RATE_LIMIT_LOGIN_REQUESTS` / `_PERIOD` | 登录接口限流 | `5` / `60` |
| `RATE_LIMIT_REGISTER_REQUESTS` / `_PERIOD` | 注册接口限流 | `3` / `60` |

路由规则的 `paths` 支持忽略模块前缀的路径段匹配：配置 `/auth/login`
即可命中真实路径 `/api/auth/login` 或带版本前缀的 `/api/v1/api/auth/login`。

多 worker / 多实例部署必须用 `RATE_LIMIT_BACKEND=redis`，否则每个进程各算各的。

---

## 权限（RBAC）

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DEFAULT_ROLE` | 新用户与未携带角色 Token 的默认角色 | `user` |

角色到权限的映射**不在环境变量里**，而是代码配置（`config/permissions.py`）。
修改后需重启进程。详见 [权限控制](rbac.md)。

---

## 幂等键

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `IDEMPOTENCY_ENABLED` | 是否启用幂等键处理 | `true` |
| `IDEMPOTENCY_TTL` | 幂等结果缓存时长（秒） | `86400` |

启用后，客户端在写请求（POST/PUT/PATCH/DELETE）带 `Idempotency-Key` 头即可安全重试：

- 首次请求正常执行并缓存 2xx JSON 响应；
- 相同 key 再次到达时回放缓存响应，并带 `Idempotent-Replay: true`；
- 未带该头、key 非法、非 2xx 响应均按普通请求处理。

局限：未实现并发锁，同一 key 的请求**同时**到达仍可能都执行一次；
支付/扣库存等强一致场景需在数据库层加唯一约束兜底。
