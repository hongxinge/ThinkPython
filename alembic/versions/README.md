# Alembic 迁移脚本目录

此目录存放数据库迁移脚本，由 Alembic 管理。**所有脚本必须提交到版本库**，
以便其他开发者与生产环境按相同顺序演进表结构。

## 目录结构

```
alembic/
├── env.py              # 迁移环境：解析同步 URL、导入全部模型
├── script.py.mako      # 新脚本模板
└── versions/           # 迁移脚本
    ├── <rev>_initial_schema.py
    └── README.md
```

## 常用命令

```bash
# 1. 修改模型后，自动生成迁移脚本
python think.py db-migrate --auto -m "添加订单表"

# 2. 应用迁移到最新版本（这才是真正的"执行迁移"）
python think.py db-migrate --upgrade

# 3. 回滚最近一次迁移
python think.py db-migrate --downgrade

# 4. 查看历史 / 当前版本
python think.py db-migrate --history
python think.py db-migrate --current
```

> 注意：**不带任何参数**的 `python think.py db-migrate` 是"简单模式"，
> 等价于 `Base.metadata.create_all`，只补建缺失的表，不记录版本、不能回滚。
> 需要版本化演进时一律使用 `--upgrade`。

## 脚本命名规则

```
YYYY_MM_DD_<revision>_<slug>.py
```

例如 `2026_11_07_5ff445245067_initial_schema.py`。模板由 `alembic.ini` 的
`file_template` 控制，`%(rev)s` 必须保持字符串占位符（revision 是十六进制串）。

## 驱动说明

迁移在同步上下文运行，`alembic/env.py` 会把应用配置里的异步 URL 转成同步驱动：

| 应用运行时驱动 | 迁移时驱动 | 额外依赖 |
|---|---|---|
| `sqlite+aiosqlite` | `sqlite` | 无（标准库） |
| `mysql+aiomysql` | `mysql+pymysql` | 随 aiomysql 安装 |
| `postgresql+asyncpg` | `postgresql+psycopg2` | `pip install psycopg2-binary` |
| `mssql+aioodbc` | `mssql+pyodbc` | `pip install pyodbc` |

## 注意事项

1. 修改模型后**必须**生成并提交迁移脚本，否则其他环境不会同步表结构。
2. 生成脚本后**人工复核**：Alembic 可能把重命名识别成"删表 + 建表"。
3. 生产环境执行迁移前先备份数据库；迁移命令失败会返回非零退出码。
4. SQLite 已启用 batch 模式（`render_as_batch`），改字段时会重建表，注意数据量。
