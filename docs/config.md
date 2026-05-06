# 配置说明

所有配置项通过 `.env` 文件管理，复制 `.env.example` 为 `.env` 后修改。

---

## 应用配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `APP_NAME` | 应用名称 | `ThinkPython` |
| `APP_VERSION` | 应用版本 | `1.0.0` |
| `APP_DEBUG` | 调试模式 | `True` |
| `TIMEZONE` | 时区 | `Asia/Shanghai` |
| `LANGUAGE` | 语言 | `zh-CN` |

---

## 模块模式

| 变量 | 说明 | 可选值 | 默认值 |
|------|------|--------|--------|
| `MODULE_MODE` | 模块模式 | `single` / `multi` | `single` |
| `ENABLED_MODULES` | 启用模块列表 | 逗号分隔 | `admin,api` |
| `DEFAULT_MODULE` | 默认模块 | 模块名 | `api` |
| `ROUTE_PREFIX` | 路由前缀 | 字符串 | `` |

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

可选级别：`DEBUG` < `INFO` < `WARNING` < `ERROR` < `CRITICAL`

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

### Memcached配置

```env
CACHE_TYPE=memcached
MEMCACHED_SERVERS=127.0.0.1:11211
```
