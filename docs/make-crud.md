# make-crud 命令

ThinkPython 提供 `make-crud` 命令，可以根据数据库表结构一键生成 Model、Controller、Service 三层完整代码，包含字段类型、注释、Pydantic 验证模型等，开箱即用。

## 使用前提

1. 已在 `.env` 中配置好数据库连接信息
2. 数据库中已存在对应的数据表（命令会读取表结构）
3. 如果是 MySQL/PostgreSQL 等，确保已安装对应的数据库驱动

## 使用方法

```bash
python think.py make-crud <table_name>
```

### 示例

```bash
# 根据 user 表生成代码
python think.py make-crud user

# 根据 order 表生成代码
python think.py make-crud order
```

## 生成内容

执行命令后，会在 `app/single/` 目录下生成三个文件：

| 文件 | 说明 |
|------|------|
| `model/<table_name>_model.py` | SQLAlchemy ORM 模型，包含字段定义、类型、注释 |
| `controller/<table_name>_controller.py` | 控制器，包含完整的 CRUD 路由（list/show/store/update/destroy） |
| `service/<table_name>_service.py` | 服务层，包含完整的增删改查业务逻辑 |

## 生成代码特性

### Model 层

- 自动映射数据库字段类型为 SQLAlchemy Column
- 保留字段注释作为 docstring
- 支持主键、自增、可空、默认值等属性
- 自动生成 `__tablename__`

```python
from sqlalchemy import Column, Integer, String, DateTime, func
from core.database import Base

class UserModel(Base):
    """用户表"""
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    username = Column(String(50), nullable=False, comment="用户名")
    email = Column(String(100), nullable=True, comment="邮箱")
    status = Column(Integer, nullable=False, default=1, comment="状态")
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")
```

### Controller 层

- 包含完整的 5 个 CRUD 路由：list / show / store / update / destroy
- 自动生成 Pydantic 请求模型（CreateRequest / UpdateRequest）
- 根据字段可空性自动生成必填验证
- 保留字段注释

```python
from pydantic import BaseModel, Field
from typing import Optional

class UserCreateRequest(BaseModel):
    """创建用户请求"""
    username: str = Field(..., description="用户名")
    email: Optional[str] = Field(None, description="邮箱")
    status: int = Field(1, description="状态")

class UserUpdateRequest(BaseModel):
    """更新用户请求"""
    username: Optional[str] = Field(None, description="用户名")
    email: Optional[str] = Field(None, description="邮箱")
    status: Optional[int] = Field(None, description="状态")
```

### Service 层

- 包含完整的增删改查方法：list / get_by_id / create / update / delete
- 自动过滤内部字段（如 `_sa_instance_state`）
- 分页查询支持

## 支持的数据库类型

| 数据库 | 支持状态 |
|--------|----------|
| MySQL | ✅ 完整支持（含字段注释） |
| PostgreSQL | ✅ 完整支持 |
| SQLite | ✅ 支持（SQLite 不支持字段注释） |
| MSSQL | ✅ 支持 |

## 注意事项

1. **表必须已存在**：`make-crud` 读取的是已有表结构，不会自动创建表
2. **文件名规则**：生成的文件名与表名一致（如 `user` 表生成 `user_model.py`）
3. **单/多模块**：默认生成到 `app/single/` 目录，多模块模式下需手动移动到对应模块
4. **覆盖风险**：如果文件已存在，命令会覆盖原有文件，请谨慎使用
5. **注释支持**：MySQL 会自动读取字段注释，其他数据库依赖列定义中的描述信息

## 配置示例

`.env` 配置：

```env
DB_TYPE=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=your_database
DB_USER=root
DB_PASSWORD=your_password
```

执行生成：

```bash
python think.py make-crud user
```

查看生成的文件：

```bash
ls app/single/model/       # user_model.py
ls app/single/controller/  # user_controller.py
ls app/single/service/     # user_service.py
```
