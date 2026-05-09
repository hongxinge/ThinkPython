# 多模块模式

ThinkPython 支持单模块和多模块两种模式，可根据项目规模灵活切换。

## 单模块 vs 多模块

| 模式 | 适用场景 | 目录结构 | URL 前缀 |
|------|----------|----------|----------|
| **单模块** (`single`) | 小型项目、快速原型 | `app/single/` | 无 |
| **多模块** (`multi`) | 中大型项目、团队协作 | `app/admin/`、`app/api/` 等 | `/admin`、`/api` |

## 切换模式

修改 `.env` 文件：

```env
# 单模块模式（默认）
MODULE_MODE=single

# 多模块模式
MODULE_MODE=multi
```

## 单模块模式

所有代码放在 `app/single/` 目录下：

```
app/
└── single/
    ├── controller/
    │   ├── user_controller.py
    │   └── product_controller.py
    ├── service/
    │   └── user_service.py
    └── model/
        └── user_model.py
```

URL 直接使用路由定义的路径，无模块前缀：

```
GET  /user/list
POST /user
GET  /user/1
```

## 多模块模式

按业务模块拆分为多个目录：

```
app/
├── admin/
│   ├── controller/
│   │   └── admin_controller.py
│   ├── service/
│   └── model/
├── api/
│   ├── controller/
│   │   ├── auth_controller.py
│   │   └── product_controller.py
│   ├── service/
│   └── model/
└── common/          # 公共模块（所有模块共享）
    ├── controller/
    ├── service/
    └── model/
```

**启用模块配置：**

```env
MODULE_MODE=multi
ENABLED_MODULES=*              # 自动发现所有模块
# 或指定模块名（白名单模式）
ENABLED_MODULES=admin,api
```

## 创建新模块

使用 CLI 命令创建：

```bash
python think.py make-module order
```

这会自动创建以下结构：

```
app/
└── order/
    ├── controller/
    │   └── __init__.py
    ├── service/
    │   └── __init__.py
    └── model/
        └── __init__.py
```

## URL 路由规则

多模块模式下，URL 会自动带上模块前缀：

| 模块 | 控制器路由 | 实际访问 URL |
|------|-----------|-------------|
| `api` | `@router.post("/auth/login")` | `POST /api/auth/login` |
| `api` | `@router.get("/product/list")` | `GET /api/product/list` |
| `admin` | `@router.get("/admin/list")` | `GET /admin/admin/list` |

可以通过 `ROUTE_PREFIX` 添加全局前缀：

```env
ROUTE_PREFIX=/v1
```

此时 URL 变为 `/v1/api/auth/login`。

## 默认模块

当 URL 中不指定模块前缀时，框架使用 `DEFAULT_MODULE` 配置的模块：

```env
DEFAULT_MODULE=api
```

## 最佳实践

- **小项目**：使用单模块模式，快速开发
- **API + 后台**：使用多模块模式，`api` 提供对外接口，`admin` 管理后台
- **公共代码**：放在 `common/` 模块中，避免重复

---

[← 返回首页](../README.md)
