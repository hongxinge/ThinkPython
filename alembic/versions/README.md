# Alembic 迁移脚本目录

此目录存放数据库迁移脚本，由 Alembic 自动管理。

## 目录结构

```
alembic/
├── env.py              # Alembic 环境配置（自动加载模型）
├── script.py.mako      # 迁移脚本模板
└── versions/           # 迁移脚本存储目录
    └── (迁移脚本文件)
```

## 迁移脚本命名规则

迁移脚本文件名格式：
```
YYYY_MM_DD_<版本号>_<描述>.py
```

例如：
```
2026_05_10_0001_create_user_table.py
```

## 如何生成迁移脚本

```bash
# 方式1: 使用 CLI 工具（推荐）
python think.py db-migrate --auto -m "添加用户表"

# 方式2: 直接使用 Alembic
alembic revision --autogenerate -m "添加用户表"
```

## 如何执行迁移

```bash
# 升级到最新版本
python think.py db-migrate

# 回滚到上一个版本
python think.py db-migrate --downgrade

# 查看迁移历史
python think.py db-migrate --history
```

## 注意事项

1. 修改模型后**必须**生成迁移脚本
2. **不要**手动修改迁移脚本（除非特殊情况）
3. 生产环境执行迁移前**建议备份数据库**
4. 迁移脚本**应该提交到版本库**中
