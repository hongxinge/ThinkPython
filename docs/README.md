# ThinkPython 文档中心

欢迎使用 ThinkPython！这里提供了完整的教程和使用指南。

## 快速入门

| 文档 | 说明 |
|------|------|
| [5 分钟创建第一个 API](getting-started.md) | 从零开始，使用 CLI 创建完整的 CRUD 接口（Model → Service → Controller → 迁移 → 测试） |

## 核心功能

| 文档 | 说明 |
|------|------|
| [客户端 API 契约](api-contract.md) | **客户端团队必读**：响应结构、错误码表、双 Token 流程、请求追踪、限流退避、接入清单 |
| [数据库配置](database.md) | MySQL、PostgreSQL、SQLite、MSSQL 配置方法及驱动安装 |
| [缓存使用](cache.md) | Redis / Memory 配置方法，使用 `get_cache`/`set_cache`/`delete_cache` 操作缓存 |
| [多模块模式](modules.md) | 单模块与多模块模式切换，创建新模块，URL 路由前缀规则 |
| [公共模块](common.md) | 跨模块共享的 Model/Service，`BaseAuthController` 使用方法 |
| [认证机制](auth.md) | JWT 认证、三种免验证方式、登录/注册/忘记密码完整示例、安全最佳实践 |
| [权限控制](rbac.md) | 接口级 RBAC：角色定义、`@require_permission`、角色变更后 Token 失效、与数据级权限的分界 |
| [make-crud](make-crud.md) | 根据数据库表结构一键生成 Model/Controller/Service 三层完整代码 |

## 工具类

| 文档 | 说明 |
|------|------|
| [Excel 工具](excel.md) | `ExcelUtil`：读取 Excel、导出 Excel、列名映射、创建下载响应 |
| [文件工具](file.md) | `FileUtil`：上传文件、批量上传、下载响应、删除文件、获取文件信息 |

## 进阶参考

| 文档 | 说明 |
|------|------|
| [CLI 工具指南](cli.md) | 所有 think.py 命令的详细说明和用法 |
| [配置说明](config.md) | 所有配置项的完整说明和默认值 |
| [部署指南](deploy.md) | 生产环境部署步骤和注意事项 |
| [API 使用示例](api.md) | 完整的 CRUD API 开发示例 |
| [架构决策记录](architecture-decisions.md) | 分层边界、响应契约、D1-D6 关键取舍、企业级能力分期 |

## 推荐阅读顺序

1. 先阅读 **[5 分钟创建第一个 API](getting-started.md)** 了解基本开发流程
2. 根据需要阅读 **数据库配置** 和 **缓存使用** 了解基础设施配置
3. 如果项目需要快速搭建 CRUD，阅读 **[make-crud](make-crud.md)** 了解如何一键生成代码
4. 如果项目需要用户系统，阅读 **认证机制** 了解 JWT 认证
5. 根据项目规模选择 **单模块** 或 **多模块** 模式，阅读对应文档
6. 需要导入导出或文件处理时，参考 **Excel 工具** 和 **文件工具** 文档
7. 部署前阅读 **[部署指南](deploy.md)** 了解生产环境配置

## CLI 命令速查

```bash
python think.py run                  # 启动服务器
python think.py make-crud user       # 根据数据库表生成 CRUD 代码
python think.py make-controller User # 创建控制器
python think.py make-model User      # 创建数据模型
python think.py make-service User    # 创建服务层
python think.py make-module order    # 创建新模块
python think.py db-migrate           # 数据库迁移
python think.py list-routes          # 列出所有路由
```

## 统一响应格式

所有接口返回统一结构，**HTTP 状态码表达传输层结果，`code` 表达业务结果**（过渡期可用
`ERROR_HTTP_MODE=legacy` 恢复旧的「一律 200」行为，详见
[架构决策记录](architecture-decisions.md)）：

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

分页响应：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [],
    "total": 50,
    "page": 1,
    "page_size": 10,
    "total_pages": 5
  }
}
```
