# 数据库配置与迁移

## 数据库连接

ThinkPython 支持多种数据库，通过 `.env` 文件配置。

### SQLite（开发环境推荐）

```env
DB_TYPE=sqlite
DB_SQLITE_PATH=./data/database.db
```

零配置，无需安装额外数据库服务。

### MySQL（生产环境推荐）

```env
DB_TYPE=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=thinkpython
DB_USER=root
DB_PASSWORD=your_password
```

需要安装 MySQL 并创建数据库：

```sql
CREATE DATABASE thinkpython DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### PostgreSQL

```env
DB_TYPE=postgresql
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=thinkpython
DB_USER=postgres
DB_PASSWORD=your_password
```

---

## 数据迁移

### 方式一：使用 CLI 命令

```bash
# 执行迁移（创建表）
python think.py db-migrate
```

### 方式二：使用 Alembic

```bash
# 安装 Alembic
pip install alembic

# 初始化迁移
alembic init alembic

# 创建迁移脚本
alembic revision --autogenerate -m "initial migration"

# 执行迁移
alembic upgrade head
```

---

## 定义模型

模型继承自 `BaseModel`，位于 `app/{module}/model/` 目录。

```python
from sqlalchemy import Column, String, Integer
from core.base_model import BaseModel


class User(BaseModel):
    __tablename__ = "user"
    
    username = Column(String(50), unique=True, nullable=False, comment="用户名")
    email = Column(String(100), unique=True, nullable=False, comment="邮箱")
    status = Column(Integer, default=1, comment="状态")
```

### 常用字段类型

| 类型 | SQLAlchemy | 说明 |
|------|-----------|------|
| 整数 | `Integer` | 普通整数 |
| 大整数 | `BigInteger` | 大整数 |
| 字符串 | `String(长度)` | 定长字符串 |
| 文本 | `Text` | 长文本 |
| 布尔 | `Boolean` | 布尔值 |
| 日期时间 | `DateTime` | 日期时间 |
| 浮点数 | `Float` | 浮点数 |
| JSON | `JSON` | JSON数据 |

---

## 连接池配置

生产环境建议调整连接池参数：

```env
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
DB_POOL_RECYCLE=3600
DB_POOL_PRE_PING=True
```

| 参数 | 说明 |
|------|------|
| `DB_POOL_SIZE` | 连接池大小 |
| `DB_MAX_OVERFLOW` | 最大溢出连接数 |
| `DB_POOL_RECYCLE` | 连接回收时间（秒） |
| `DB_POOL_PRE_PING` | 使用前检测连接有效性 |
