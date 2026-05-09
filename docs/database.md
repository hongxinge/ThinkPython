# 数据库配置

ThinkPython 支持 MySQL、PostgreSQL、SQLite、MSSQL 四种数据库，通过 `.env` 文件切换。

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

## 数据库迁移

配置好数据库后，执行迁移命令创建表：

```bash
python think.py db-migrate
```

---

[← 返回首页](../README.md)
