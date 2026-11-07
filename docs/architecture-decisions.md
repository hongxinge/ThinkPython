# ThinkPython 架构决策记录（ADR）

> 本文件记录框架层面的关键取舍，作为后续迭代、代码评审与文档编写的唯一依据。
> 状态说明：**已定**= 可直接实施；**规划中**= 已确定方向但尚未落地。
> 最后更新：2026-11-07

---

## 1. 定位与目标

ThinkPython 的定位是「**ThinkPHP 式的开发体验 + FastAPI 的性能与类型安全**」，服务三类使用者：

| 使用者 | 核心诉求 | 对应设计 |
|---|---|---|
| 独立开发者 / 一人公司 | 零配置起步，半天内上线一个带认证的 CRUD 服务 | 单模块 + SQLite + 内存缓存为默认态 |
| 中小团队 | 清晰的模块边界、可预测的目录结构、可交接 | 多模块 + 三层架构 + 代码生成器 |
| 企业项目 | 安全默认、可观测、可迁移、可审计 | 安全基线 + Alembic + 结构化日志 + 契约规范 |

**非目标**：不做全功能企业平台（多租户、工作流引擎、低代码），这些以插件或扩展包形式提供。

---

## 2. 架构原则

1. **单一契约**：任何接口的响应体恒为 `{code, message, data}`；HTTP 状态码表达传输层语义，`code` 表达业务语义，二者不再互相替代。
2. **边界清晰**：Controller 不写 SQL、不管理事务；Service 只做业务与 `flush`；事务提交由 `get_db` 统一负责。
3. **默认可测**：所有核心能力必须能在「内存 SQLite + 内存缓存」下完成测试，不得强制依赖外部服务。
4. **安全默认**：危险配置必须显式开启；默认值应当是「即使忘记改也不会出事」的一侧。
5. **文档即代码**：文档中的每条命令、每个路径都必须能在仓库当前状态下复现；不一致视为缺陷。

---

## 3. 分层与职责边界

| 层 | 职责 | 禁止事项 |
|---|---|---|
| `router/` | 扫描控制器、拼装 URL 前缀、注册路由 | 不承载业务逻辑，不做参数校验 |
| `Controller` | 解析请求、调用 Service、封装响应 | 不写 SQL、不 `commit`、不捕获所有异常 |
| `Service` | 业务规则、事务内操作、调用 Model | 不返回 ORM 对象给 Controller（应转 dict/DTO） |
| `Model` | 表结构、字段约束、关系 | 不写业务查询逻辑 |
| `core/` | 引擎、会话、缓存、异常、认证中间件 | 不依赖 `app/` 下任何模块（保证可复用） |
| `config/` | 环境变量读取与默认值 | 不在运行时修改配置（除测试显式 reload） |

**依赖方向**：`app → core → config`，禁止反向依赖。`core` 不得 import `app`。

---

## 4. 契约规范

### 4.1 响应结构

```json
{ "code": 200, "message": "success", "data": {} }
```

- 成功：HTTP 200，`code=200`。
- 业务失败：HTTP 4xx/5xx，`code` 为业务码（如 `40101` 表示 Token 过期）。
- 分页：`data = { items, total, page, page_size, total_pages }`，`page_size` 必须落在 `[1, 100]`。

### 4.2 错误码分段（规划中）

| 区间 | 含义 |
|---|---|
| 200 | 成功 |
| 40000-40099 | 参数错误 |
| 40100-40199 | 认证与 Token |
| 40300-40399 | 权限 |
| 40400-40499 | 资源不存在 |
| 40900-40999 | 冲突（唯一键、状态机） |
| 42900-42999 | 限流 |
| 50000-50099 | 服务端错误 |

### 4.3 认证

- Access Token：2 小时，`type=access`，仅用于业务接口。
- Refresh Token：7 天，`type=refresh`，仅用于 `/auth/refresh`。
- 所有受保护接口从 `request.state.current_user` 读取身份，不使用全局变量。

---

## 5. 关键决策（D1-D6）

### D1 错误响应契约：统一为「真实 HTTP 状态码 + 业务 code」· 已定

- **背景**：现状是双轨——`self.error()` 返回 dict 走 HTTP 200，`AppException` 把 `code` 直接当 HTTP 状态码，导致同一个 401 有两种表现，前端需写两套判断。
- **决策**：
  1. `AppException` 增加独立 `status_code` 字段，缺省从 `code` 映射（仅接受 100-599，否则回落 500）；
  2. `self.error()` 在 `ERROR_HTTP_MODE=standard`（默认）下返回带真实状态码的 `JSONResponse`，`legacy` 模式保留旧的 HTTP 200 行为，用于过渡；
  3. 业务码与 HTTP 状态码分离，业务码进入响应体 `code`。
- **影响**：前端改为按 HTTP 状态码分支；需要同步更新文档与示例。
- **回退**：设置 `ERROR_HTTP_MODE=legacy`，无需改代码。

### D2 默认运行形态：开发态 single + SQLite，生产态 multi + MySQL · 已定

- **背景**：本地 `.env` 是 multi + MySQL + Redis，而 `.env.example` 与全部教程是 single + SQLite，导致新手照文档操作必然失败。
- **决策**：仓库默认（`.env.example`、README、getting-started）统一为 `single + sqlite + memory`；生产模板单独放在 `deploy/.env.example`（`multi + mysql + redis`），文档明确区分「开发态」与「生产态」。
- **影响**：教程可直接复现；部署文档需引用生产模板。
- **回退**：无（配置可随时切换）。

### D3 用户模型：单一实体，统一从 common 导入 · 已定

- **背景**：`app/common/model/user_model.py` 与 `app/single/model/user_model.py` 都映射 `user` 表，同一进程导入即崩溃。
- **决策**：只保留 `app/common/model/user_model.py` 作为唯一实体；`app/single/model/user_model.py` 改为 re-export（`from app.common.model.user_model import User`），保持旧导入路径可用。
- **影响**：消除 `Table 'user' is already defined`；后续新增模块统一从 `app.common.model` 导入。
- **回退**：删除 re-export 文件，恢复独立模型（不推荐）。

### D4 注册契约：邮箱必填并校验 · 已定

- **背景**：请求模型声明 `email` 可选，但数据库列为 `NOT NULL + UNIQUE`，不传邮箱必然 500。
- **决策**：`RegisterRequest.email` 改为必填并做格式校验；注册时同时查重用户名与邮箱，冲突返回 `40901`。
- **影响**：API 契约变更，需在 CHANGELOG 标注；前端注册表单需增加邮箱必填。
- **回退**：将数据库列改为 `nullable=True` 并保留唯一索引。

### D5 密码与 Token：bcrypt 为主，兼容旧 MD5 并自动升级 · 已定

- **背景**：当前为无盐 MD5；Token 不校验类型、改密后旧 Token 仍有效。
- **决策**：
  1. 新密码使用 bcrypt（依赖 `bcrypt` 包）；
  2. 校验时若检测到 32 位十六进制 MD5，则用 MD5 验证，成功后**立即重新哈希为 bcrypt**；
  3. `decode_token` 强制校验 `type`；业务接口只接受 `access`；
  4. 用户表增加 `token_version`，改密/禁用时自增，签发与校验均比对。
- **影响**：新增依赖；首次登录产生一次写操作；旧 Token 在改密后失效。
- **回退**：保留 MD5 校验分支即可降级，不改表结构。

### D6 数据库迁移：Alembic 使用同步驱动 · 已定

- **背景**：`alembic/env.py` 用同步 `engine_from_config` 加载异步 URL，连接即抛 `MissingGreenlet`；`alembic.ini` 中文注释在 GBK locale 下解码失败。
- **决策**：
  1. 新增 `get_sync_database_url()`，把 `+aiomysql` / `+aiosqlite` / `+asyncpg` 转为同步驱动；
  2. `env.py` 使用同步 URL，保持同步迁移 API；
  3. `alembic.ini` 改为纯 ASCII 注释；
  4. `think.py db-migrate` 失败时返回非零退出码。
- **影响**：MySQL 迁移需额外安装 `pymysql`；SQLite 迁移零额外依赖。
- **回退**：改回 `async_engine_from_config` 并接受更复杂的异步迁移实现。

---

## 6. 开发者黄金路径

```bash
# 1. 安装（运行 + 测试依赖）
pip install -r requirements-dev.txt

# 2. 零配置启动（默认 single + SQLite + memory）
python think.py run

# 3. 生成一个模块与三层代码
python think.py make-module order
python think.py make-crud order

# 4. 自检：确认路由已注册
python think.py list-routes

# 5. 验证
python -m pytest tests/ -q
```

约定：

- 新增控制器必须放在 `app/{module}/controller/*_controller.py`，类定义在本文件内，`__init__` 无参。
- URL 在多模块模式下自动带 `/{module}` 前缀，路由路径中不要重复模块名。
- Service 必须设置 `model_class`；只 `flush`，不 `commit`。
- 业务异常抛 `AppException` 子类，不要 `return self.error()` 后继续执行。

---

## 7. 企业级能力分期

| 阶段 | 内容 | 状态 |
|---|---|---|
| Phase 1（1.x） | 安全基线、响应契约统一、迁移可用、部署可跑、文档一致 | 进行中 |
| Phase 2（1.x） | 结构化日志与 request_id、健康/就绪探针、统一错误码表、OpenAPI 示例、分页排序过滤规范 | 规划中 |
| Phase 3（2.0） | 多租户、审计日志、幂等键、软删除、RBAC、文件存储抽象（本地 / S3）、任务队列 | 规划中 |
| Phase 4（2.x） | 插件机制、OpenAPI 反向生成代码、CLI 脚手架模板市场 | 规划中 |

**准入标准**：任何进入 Phase 2+ 的能力，必须先具备「内存环境可测 + 文档示例可复现 + 有回退方案」三项条件。

---

## 8. 实施进度（2026-11-07）

| 决策 | 状态 | 说明 |
|---|---|---|
| D1 错误契约 | 已落地 | `AppException` 分离 `status_code`；`self.error()` 默认返回真实状态码；`ERROR_HTTP_MODE=legacy` 可回退 |
| D2 默认运行形态 | 已落地 | `.env.example`（开发态 single+SQLite+memory）与 `deploy/.env.example`（生产态 multi+MySQL+Redis）分离；文档、教程、CLI 说明全部对齐；本地 `.env` 保留用户的多模块配置并加注说明 |
| D3 单一 User 实体 | 已落地 | single 的 User 改为 re-export，全仓库仅一处表映射 |
| D4 注册邮箱必填 | 已落地 | email 必填 + 格式校验 + 用户名/邮箱双查重 |
| D5 密码与 Token | 已落地 | PBKDF2 已上线、兼容 MD5 并自动升级；Token 强制校验 `type`；双 Token（access + refresh）与轮换；`token_version` 已随迁移落地，改密后旧 Token 立即失效 |
| D6 迁移同步驱动 | 已落地 | `get_sync_database_url()` 映射同步驱动；`alembic.ini` 全 ASCII；首个初始化迁移已生成；upgrade/downgrade/check 实测通过；迁移失败返回退出码 1 |

### Wave 3 补充落地（配置一致性）
- `ROUTE_PREFIX` 真实生效：加在主路由器上，支持 `/api/v1` 版本化命名空间；
- `LOG_LEVEL` / `TIMEZONE` 真实生效：`core/logger.py` 统一配置控制台 + 轮转文件日志；
- `MEMCACHED_*` 移除：只支持 `memory` / `redis`，非法值启动即报错并提示可选值；
- `allowed_mime_types` 接入 `FileUtil.upload`；文件大小校验改用 `file.size`，避免整块读入内存；
- 限流路径匹配修正：`/auth/login` 现在能命中 `/api/auth/login`，登录/注册限流真正生效；
- 部署（裸机）：`deploy/` 下的 Gunicorn 配置、systemd 单元、Nginx/SSL 示例、`mysql-init.sql`、`requirements-prod.txt`。

### Wave 4 补充落地（客户端 API 契约）

框架定位明确为「为客户端 App / 小程序 / 前端提供 JSON API」，据此补齐契约层能力：

| 能力 | 实现 | 客户端价值 |
|---|---|---|
| 双 Token | 登录返回 `access_token` + `refresh_token` + `expires_in`；新增 `POST /auth/refresh` | 不再每 2 小时强制重新登录 |
| 刷新轮换 | 轮换时旧 refresh 立即失效（`force=True`，不受黑名单开关影响） | 防止 refresh 被窃取后长期复用 |
| 主动登出 | 新增 `POST /auth/logout`，`data.blacklisted` 表明是否真正吊销 | 客户端可判断服务端状态 |
| 错误码可区分 | 过期 `1004` / 吊销 `1005` / 无效 `1003` / 未携带 `1001` | 区分「刷新续期」与「重新登录」 |
| 请求追踪 | `X-Request-ID` 支持客户端传入；错误体带 `request_id` | 用户反馈可精确定位链路 |
| 慢请求告警 | `LOG_SLOW_REQUEST_MS`（默认 500ms）触发 WARNING | 无需 APM 也能抓慢接口 |
| 探活分层 | `/health`（不查依赖）+ `/health/ready`（DB + 缓存） | 负载均衡摘流更准确 |
| 真实客户端 IP | `TRUST_PROXY` 开关 + `helpers.net.get_client_ip` | 代理后不再全站共用一个限流桶 |
| 契约文档 | `docs/api-contract.md` | 客户端团队可直接照着接入 |

相关新增模块：`core/context.py`（request_id 上下文）、`core/error_codes.py`（业务码表与 HTTP 映射）、
`core/token_state.py`（版本校验，缓存加速）、`helpers/net.py`（可信代理 IP）。

### Wave 6 补充落地（开发者接入体验）

框架的用户是**写业务的人**。本轮的判断标准只有一条：新接入一个客户端要花多久。

| 能力 | 实现 | 解决的问题 |
|---|---|---|
| 契约导出 | `think.py openapi`，直接调用 `app.openapi()` | 生产关闭 schema 端点后仍能生成 SDK，不必为工具放开安全边界 |
| 契约体检 | 识别响应类型退化、缺 summary、写操作缺请求体 | 把「客户端拿不到类型」这类隐性成本显性化，能直接指导修改 |
| SDK 生成 | `think.py make-client --lang ts` | 客户端不必再手写请求封装、刷新重试、错误分支 |
| 泛型响应模型 | `core/schema.py` 的 `ApiResponse[T]` / `PageData[T]` | 统一响应包终于能表达 `data` 的具体类型，SDK 从 `unknown` 变成强类型 |
| 响应压缩 | GZip，注册在**最内层** | 实测超时压缩 81%；小响应与已压缩类型自动跳过 |

#### D7 响应模型：用泛型包装替代 `response_model=dict` · 已定

`self.success()` 返回 `{code, message, data}`，此前所有路由都写 `response_model=dict`，
OpenAPI 里只有 `additionalProperties: true`，客户端类型只能是 `unknown`。

改为 `response_model=ApiResponse[LoginData]` 后，FastAPI 生成 `ApiResponse_LoginData_`，
SDK 生成器识别这一层包装并抽取 `data` 类型（避免 `ApiResponse<ApiResponse<T>>`）。

**渐进式落地**：不强制一次性改完。未声明 `response_model` 的接口照常工作，
体检报告会如实列出数量。`auth` 与 `admin` 控制器已作为示范迁移。

**一个必须知道的副作用**：声明 `response_model` 后 FastAPI 会按模型过滤字段。
若发现「接口明明返回了、客户端收不到」，先检查模型定义是否漏字段。

#### D8 压缩位置：中间件最内层 · 已定

Starlette 的 `GZipMiddleware` 只在收到「单次完整 body」时才比较 `minimum_size`。
一旦外层存在 `BaseHTTPMiddleware`（日志、认证、幂等），响应会被转成流式分块，
此时 GZip **无条件压缩**——实测 87 字节的 `/health` 被压成 106 字节，反向浪费。

因此压缩注册在最内层（紧贴路由），拿到原始响应，门限才真正生效。
代价是中间件自身生成的响应（401/429）不压缩，但它们本来就小，影响可忽略。

如果将来把日志/认证改成纯 ASGI 中间件（可省掉 `BaseHTTPMiddleware` 的流包装开销），
压缩就可以安全地移回外层，届时需重新验证门限行为。

#### D9 SQLite 生产可用性 · 已定

SQLite 的默认配置不适合并发服务：`foreign_keys` 默认 **OFF**（约束形同虚设）、
`journal_mode=delete`（读写互斥）、`busy_timeout=0`（并发写立即报错）。

框架在文件库连接建立时统一下发 `WAL / NORMAL / foreign_keys=ON / busy_timeout=5000`。
内存库（`:memory:`）不支持 WAL，自动跳过。

---

### Wave 7 补充落地（服务端内核与上传能力）

本轮继续收紧服务端：把中间件从框架的过渡层换成原生 ASGI，
并补齐大文件上传。**框架定位明确为纯服务端 JSON API，不含任何前端代码**——
`make-client` 只是服务端 CLI 的可选工具，产物归使用者的客户端团队，不参与服务端运行。

#### D10 中间件全部改为纯 ASGI · 已定

此前日志、认证、幂等三个中间件都用 `app.middleware("http")(fn)`，
底层是 `BaseHTTPMiddleware`。它把响应包进 anyio 内存流逐块转发，带来两个代价：

1. **每请求多一次内存拷贝**。合成基准（本地 ASGI 直调、2000 次、单层包装）：

   | 场景 | 平均 | p50 | p95 |
   |---|---|---|---|
   | 无中间件基线 | 15.0µs | 14.4µs | 16.7µs |
   | 纯 ASGI 中间件 | 15.9µs | 14.8µs | 18.6µs |
   | `BaseHTTPMiddleware` | **125.2µs** | **102.9µs** | **154.0µs** |

   单层就多约 110µs，而我们有三层。

2. **破坏压缩的尺寸判断**。`GZipMiddleware` 只在收到「单次完整 body」时
   比较 `minimum_size`，流式响应会被无条件压缩——87 字节的 `/health`
   被压成 106 字节，越压越大。

改造方式：抽出 `_authenticate(scope)` 作为认证判定的唯一实现，
`AuthMiddleware` 与兼容函数 `auth_middleware` 共用；日志与幂等同理。
幂等中间件改为**边转发边旁路收集** body，请求结束后再决定是否写缓存，
不再需要"读完重建 Response"。

结果：压缩可以安全地回到最外层（覆盖 401/429），小响应恢复不压缩，
大 JSON 仍压缩 81%。`tests/test_wave7.py` 用结构断言钉死
「不允许出现 `BaseHTTPMiddleware`」，防止以后被改回去。

#### D11 分片上传：文件存会话，不用缓存 · 已定

未合并的分片存在 `{UPLOAD_DIR}/.chunks/{upload_id}/`，`meta.json` 与分片同目录。

为什么不用缓存存会话元信息：缓存重启会丢，而磁盘上的分片还在，
两者不一致就留下永远清不掉的残片。同目录存储后，"删会话"就是"删目录"，
不存在孤儿。

几个刻意的约束：

| 约束 | 原因 |
|---|---|
| 分片大小必须精确（除末片） | 弱网下截断的分片若被接受，合并出的文件是静默损坏的 |
| `upload_id` 只接受 32 位十六进制 | 它会参与路径拼接，必须杜绝穿越 |
| 每次 `init` 顺带清理过期会话 | 一人公司场景，少一个定时任务就少一处故障点 |
| 合并先写 `.merging` 再原子替换 | 中途失败不会留下"看起来完整"的半个文件 |

已知限制：同一会话并发 `complete` 未加跨进程锁，
客户端应先查 `status` 再重试。强一致场景需外层加分布式锁。

#### D12 上传 URL 与磁盘位置解耦 · 已定

上传返回的 `url` 由 `UPLOAD_URL_PREFIX` 拼接，不再用磁盘相对路径。

原实现下，当 `UPLOAD_DIR` 指向项目外目录（如 `/data/uploads`）时，
`relative_to(PROJECT_ROOT)` 失败会退回绝对路径，
产出 `/C:/Users/.../uploads/files/...` 或 `/data/uploads/...`——
既泄漏服务器目录结构，客户端也访问不到。

拆成两个配置后：磁盘在哪由 `UPLOAD_DIR` 决定，对外地址由
`UPLOAD_URL_PREFIX` 决定，Nginx 负责映射。

配套安全措施：Nginx 增加 `location ^~ /uploads/.chunks/ { return 404; }`
与隐藏文件统一拒绝，避免未合并分片被直接下载。

---

## 9. 变更纪律

1. **破坏性变更**必须：升次版本号、写 CHANGELOG、提供兼容开关、在本文档记录回退方式。
2. **核心契约**（响应结构、认证头、路由前缀规则）不得在 1.x 内二次变更。
3. **测试门禁**：P0 缺陷为 0、全量测试通过、`tests/test_regressions_p0.py` 无 XPASS 遗留标记。
4. **文档同步**：代码改动涉及命令、路径、配置项时，同一提交内更新对应文档。
