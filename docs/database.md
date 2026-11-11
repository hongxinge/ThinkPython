# 数据库配置

ThinkPython 通过 `.env` 切换数据库方言。下表是 **2026-11-11 代码核查 + 本机实测**得到的真实支持等级，
「能写出连接串」与「能直接上生产」不是一回事。

## 支持矩阵

| 数据库 | 等级 | 应用驱动（异步） | 迁移驱动（同步） | 默认安装 | 关键前提 |
|---|---|---|---|---|---|
| SQLite | **一等**：默认形态，单机生产可用 | `aiosqlite` | 标准库 `pysqlite` | ✅ | 框架已开启 WAL / `synchronous=NORMAL` / 外键 / `busy_timeout`（`core/database.py`）；单写者模型 |
| MySQL 8 | **一等**：推荐生产库 | `aiomysql` | `pymysql`（aiomysql 传递依赖） | ✅ | `utf8mb4`；用 `deploy/mysql-init.sql` 初始化字符集与账号 |
| PostgreSQL | **二等**：可跑通，需两步手工配置 | `asyncpg` | `psycopg2` | 异步已装 / **同步未装** | 必须改 `DB_PORT=5432`；迁移前 `pip install psycopg2-binary` |
| SQL Server | **三等**：条件支持，未实机验证 | `aioodbc` | `pyodbc` | **均未装** | 需系统安装 ODBC Driver 17/18；Linux 额外装微软驱动；`requirements.txt` 中仍是注释 |
| MariaDB | 未正式支持 | — | `mariadb+pymysql`（仅有映射） | — | `DB_TYPE` 不识别 `mariadb`；只能用 `DATABASE_URL`，且无实测 |

判定依据：

- 方言与驱动映射：`config/database.py` 的 `_SYNC_DRIVER_MAP` / `get_sync_database_url()` / `get_database_url()`；
- 依赖声明：`requirements.txt`（`aiomysql`/`asyncpg`/`aiosqlite` 为必需，`aioodbc`/`pyodbc` 为注释）、`requirements-prod.txt`；
- 迁移链路：`alembic/env.py` 用 `get_sync_database_url()` 转同步驱动，仅 SQLite 启用 `render_as_batch`；
- 本机 `.venv` 实测：`aiosqlite` / `aiomysql` / `pymysql` / `asyncpg` 已装，`psycopg2` / `aioodbc` / `pyodbc` / `asyncmy` 未装；
- 测试覆盖：336 项测试中，与数据库相关的断言集中在 URL 字符串生成与内存 SQLite，**没有**对 MySQL / PostgreSQL / MSSQL 的真实连接集成测试。

## 已知缺口与规避方式

| 缺口 | 证据 | 规避方式 |
|---|---|---|
| 默认端口恒为 `3306` | `config/database.py` 的 `DB_PORT` | 切 PG 显式写 `DB_PORT=5432`，MSSQL 写 `1433` |
| 密码含 `@` 会被截断（实测 `P@ss/2026` → `P`） | `config/database.py:get_database_url()` 用 f-string 拼接，未做 percent-encode | 改用 `DATABASE_URL` 并手工转义特殊字符，或密码只用字母数字 |
| `DATABASE_URL` 会覆盖 `get_database_url(config)` 的自定义参数 | `config/database.py:get_database_url()` 开头的 `DATABASE_URL` 分支 | 需要多套配置时不要设置该环境变量 |
| 表 / 字段注释反射仅 MySQL | `core/inspector.py` 的 `_get_table_comment()` / `get_column_comments_mysql()` | 其他库下 `make-crud` 生成的注释为空（降级，不影响建表） |
| `DB_CHARSET` 仅 MySQL 生效 | `config/database.py:get_database_url()` 的 mysql 分支 | PG / MSSQL 下为死配置，可忽略 |
| `is_sqlite = "sqlite" in db_url` 按子串判断 | `core/database.py:init_database()` 中的 `is_sqlite` 判断 | 密码、库名中不要出现 `sqlite` 字样，否则会误跳过连接池 |

> 按 ADR D0 的定位判据，新增数据库支持只有在服务客户端 API 请求链路时才进入核心路线；
> Oracle / 达梦 / 人大金仓等政企库属于管理端与合规场景，不作为框架的演进方向。

## 配置文件

所有数据库配置在 `config/database.py` 中管理，通过 `.env` 环境变量覆盖。

## SQLite（默认）

零配置即可使用，适合开发和测试。

**.env 配置：**

```env
DB_TYPE=sqlite
```

SQLite 使用 `aiosqlite` 异步驱动，数据库文件默认在 `./data/database.db`，可自定义路径：

```env
DB_TYPE=sqlite
DB_SQLITE_PATH=./mydata.db
```

无需额外安装依赖。

## MySQL

**.env 配置：**

```env
DB_TYPE=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=thinkpython
DB_USER=root
DB_PASSWORD=your_password
```

**安装驱动：**

```bash
pip install aiomysql
```

**连接池配置（可选）：**

```env
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_RECYCLE=3600
DB_POOL_PRE_PING=True
DB_CHARSET=utf8mb4
```

## PostgreSQL

**.env 配置：**

```env
DB_TYPE=postgresql
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=thinkpython
DB_USER=postgres
DB_PASSWORD=your_password
```

**安装驱动：**

```bash
pip install asyncpg
```

## SQL Server (MSSQL)

**.env 配置：**

```env
DB_TYPE=mssql
DB_HOST=127.0.0.1
DB_PORT=1433
DB_NAME=thinkpython
DB_USER=sa
DB_PASSWORD=your_password
```

**安装驱动：**

```bash
pip install aioodbc pyodbc
```

> 注意：MSSQL 需要系统安装 ODBC Driver。Windows 上通常自带，Linux 需要额外安装 [Microsoft ODBC Driver](https://docs.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server)。

## 调试：查看 SQL 语句

开发时可以开启 SQL 日志：

```env
DB_ECHO=True
```

开启后所有执行的 SQL 语句会打印到控制台。

### 慢 SQL 日志（生产可用）

生产建议关闭 `DB_ECHO`（全量 SQL 会显著增加 I/O），改用按阈值告警：

```env
DB_SLOW_QUERY_MS=500
```

超过阈值的 SQL 以 WARNING 级别记录，格式：

```
slow_sql | 812.4ms | request_id=8f3c... | SELECT ... FROM user WHERE ...
```

要点：

- 监听由 `core/database.py:install_slow_query_logging()` 通过 SQLAlchemy 事件注册，
  对所有方言（SQLite / MySQL / PostgreSQL / MSSQL）一致生效；
- 记录耗时、`request_id` 与**截断到 300 字符**的 SQL，方便把慢接口与慢 SQL 串起来；
- **不记录参数值**，避免密码、手机号、Token 进入日志；
- 设为 `0` 即完全关闭监听，无额外开销。

## 数据库迁移

配置好数据库后，按版本化方式建表：

```bash
# 首次：根据模型生成初始迁移脚本并应用
python think.py db-migrate --auto -m "初始表结构"
python think.py db-migrate --upgrade

# 之后每次改模型：生成脚本 → 应用
python think.py db-migrate --auto -m "添加订单表"
python think.py db-migrate --upgrade
```

迁移在同步驱动下执行，`alembic/env.py` 会自动把 `mysql+aiomysql` 这类
异步 URL 转换为 `mysql+pymysql`，无需单独维护连接串。

---

[← 返回首页](../README.md)
