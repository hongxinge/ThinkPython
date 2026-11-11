# 客户端 API 契约

本文档面向 **App / 小程序 / 前端团队**，描述 ThinkPython 对外提供的 API 行为约定。
服务端实现变更时以本文档为准；文中标注「1.x 不变」的部分属于兼容承诺。

---

## 1. 定位

ThinkPython 是**为客户端提供 JSON API 的后端框架**，不是服务端渲染框架。由此决定了几条基本约定：

| 约定 | 说明 |
|---|---|
| 只返回 JSON | 不输出 HTML 页面；唯二的非 JSON 响应是文件下载与静态资源 |
| 无 Cookie / Session | 认证完全依赖 `Authorization: Bearer <token>`，天然适配 App 与多端 |
| 状态码表达传输语义 | 4xx/5xx 是真实 HTTP 状态码，业务语义由 `body.code` 表达 |
| 错误可枚举 | 每个失败场景有稳定业务码，客户端不解析中文文案 |
| 请求可追踪 | 每次请求有 `X-Request-ID`，贯穿日志与错误响应体 |
| 版本可并行 | `ROUTE_PREFIX` 支持 `/api/v1` 这类前缀，新旧版本可同时在线 |

---

## 2. 传输约定

```
Base URL:  https://your_domain.com
版本前缀:  由服务端 ROUTE_PREFIX 决定，例如 /api/v1
编码:      UTF-8
请求体:    application/json（文件上传除外）
响应体:    application/json; charset=utf-8
```

**不要**依赖 URL 中是否含模块名（`/api`、`/admin`）——那是服务端的模块划分，
随时可能调整；客户端应以接口文档给出的完整路径为准。

---

## 3. 认证

### 3.1 登录

```http
POST /api/auth/login
Content-Type: application/json

{"username": "alice", "password": "Passw0rd!"}
```

成功响应：

```json
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi...",
    "token_type": "Bearer",
    "expires_in": 7200,
    "user_id": 1,
    "username": "alice"
  }
}
```

| 字段 | 说明 |
|---|---|
| `access_token` | 访问业务接口，默认 2 小时 |
| `refresh_token` | 仅用于续期，默认 7 天；**不能**访问业务接口 |
| `expires_in` | access_token 剩余秒数，客户端据此提前刷新 |
| `token` | 旧字段，等同 `access_token`，仅为兼容保留 |

### 3.2 携带 Token

```http
GET /api/auth/profile
Authorization: Bearer <access_token>
```

### 3.3 刷新

```http
POST /api/auth/refresh
Content-Type: application/json

{"refresh_token": "..."}
```

返回新的 `access_token` + `refresh_token`。

**轮换语义（重要）**：服务端默认开启 `JWT_REFRESH_TOKEN_ROTATE`，旧的
`refresh_token` 在换新后**立即失效**。客户端必须用响应中的新值覆盖本地存储，
否则下次刷新会拿到 `1009`。

### 3.4 登出

```http
POST /api/auth/logout
Authorization: Bearer <access_token>
```

响应 `data.blacklisted` 表示服务端是否真正吊销了该 Token：

- `true`：Token 已进入黑名单，有效期内不可再用；
- `false`：服务端未启用黑名单（`TOKEN_BLACKLIST_ENABLED=false`），
  客户端删除本地 Token 即可，服务端不会拦截。

### 3.5 Token 失效的四种情况

| 场景 | 业务码 | 客户端动作 |
|---|---|---|
| 未携带 Authorization | `1001` | 跳登录页 |
| 不是 `Bearer` 格式 | `1002` | 检查客户端代码，修复后重试 |
| 签名错误 / 类型不符（如用 refresh 调业务接口） | `1003` | 清空本地凭证，跳登录页 |
| 已过期 | `1004` | **调用刷新接口**，成功后重放原请求 |
| 已吊销（登出、改密、改密后版本号变化） | `1005` | 清空本地凭证，跳登录页 |

`1004` 与 `1005` 必须区分处理：前者能续期，后者只能重新登录。
服务端为此专门返回不同业务码，客户端不应只看 HTTP 401。

### 3.6 查询自己的权限

```http
GET /api/auth/permissions
Authorization: Bearer <access_token>
```

```json
{"code": 200, "message": "success", "data": {"role": "user", "permissions": ["profile:read", "profile:write"]}}
```

客户端可用它控制按钮 / 菜单的可见性，避免「点了才提示无权限」。
注意权限可能随角色调整而变化，建议登录后获取一次并缓存，收到 `1010` 时再刷新。

### 3.7 权限不足

```http
HTTP/1.1 403 Forbidden
```

```json
{
  "code": 1010,
  "message": "当前角色无权访问该接口",
  "data": {"required": ["admin:menu"], "role": "user"},
  "request_id": "..."
}
```

`data.required` 是接口要求的权限，`data.role` 是当前角色，便于联调定位。

---

## 4. 响应结构

### 4.0 OpenAPI 的类型精度（客户端 SDK 相关）

业务接口统一声明 `response_model=ApiResponse[T]`，OpenAPI 会生成 `ApiResponse_LoginData_`
这类具名模型，`data` 的字段能被 SDK 生成器识别为强类型，而不是 `unknown`。

当前 30 个 OpenAPI 操作中 **23 个为精确模型**，其余 7 个刻意不套响应包装：

| 类别 | 接口 | 原因 |
|---|---|---|
| 文件流 | `GET /api/util/file/download`、`/preview` | 返回二进制文件，不是 JSON 契约 |
| 存活探针 | `GET /health`、`/health/ready` | 供负载均衡探活，不是业务接口 |
| 管理端示例 | `POST /api/util/excel/import*`、`/export` | 按 ADR D0，管理端能力不作为核心契约演进方向 |

> **注意**：声明响应模型后 FastAPI 会按模型过滤字段。若出现「服务端返回了、客户端收不到」，
> 先检查该接口的 data 模型定义；新增字段必须同步更新模型，否则会被静默丢弃。

### 4.1 成功

```json
{"code": 200, "message": "success", "data": {}}
```

### 4.2 失败（1.x 不变）

```json
{
  "code": 1006,
  "message": "用户名或密码错误",
  "data": null,
  "request_id": "3f2b8c1e-..."
}
```

| 字段 | 说明 |
|---|---|
| `code` | 业务错误码，见第 5 节。**客户端分支判断以此为准** |
| `message` | 可直接展示的提示，文案可能优化，不要用于逻辑判断 |
| `data` | 附加信息：字段错误列表、`retry_after` 等，失败时可能为 `null` |
| `request_id` | 本次请求追踪 ID，与响应头 `X-Request-ID` 一致 |

### 4.3 参数校验失败

```json
{
  "code": 422,
  "message": "参数验证失败",
  "data": [
    {"field": "body.password", "message": "String should have at least 6 characters"}
  ],
  "request_id": "..."
}
```

### 4.4 分页

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [],
    "total": 128,
    "page": 1,
    "page_size": 10,
    "total_pages": 13
  }
}
```

约定：

- `page` 从 1 开始；
- `page_size` 服务端会做上下限归一化，`0` 或负数按 `1` 处理；
- 空结果返回 `items: []` 而不是 `null`，客户端可直接遍历。

---

## 5. 业务错误码

段划分：`4xx/5xx` 与 HTTP 语义一致；`1xxx` 认证；`2xxx` 用户；`3xxx` 文件；`4xxx` 参数与业务。

| code | HTTP | 含义 |
|---|---|---|
| `400` | 400 | 请求不合法 |
| `401` / `403` / `404` / `405` | 同值 | 未授权 / 无权限 / 不存在 / 方法不允许 |
| `409` | 409 | 资源冲突（如用户名已存在） |
| `413` / `415` | 同值 | 负载过大 / 媒体类型不支持 |
| `422` | 422 | 参数校验失败（`data` 为字段错误数组） |
| `429` | 429 | 触发限流，见第 7 节 |
| `500` / `503` | 同值 | 服务内部错误 / 服务不可用 |
| `1001` | 401 | 未携带认证 Token |
| `1002` | 401 | Token 格式错误（非 Bearer） |
| `1003` | 401 | Token 无效（签名错误、类型不符） |
| `1004` | 401 | Token 已过期 → **应刷新** |
| `1005` | 401 | Token 已吊销（登出/改密）→ **应重新登录** |
| `1006` | 401 | 用户名或密码错误 |
| `1007` | 403 | 账号被禁用 |
| `1008` | 423 | 账号因连续失败被临时锁定，`data.retry_after` 为秒数 |
| `1009` | 401 | Refresh Token 无效或已使用过 |
| `1010` | 403 | 已登录但角色权限不足，`data` 含 `required` 与 `role` |
| `2001` / `2002` | 409 | 用户名已存在 / 邮箱已存在 |
| `2003` | 404 | 用户不存在 |
| `2004` | 400 | 旧密码不正确 |
| `3001` / `3002` | 413 / 415 | 文件过大 / 文件类型不允许 |
| `3003` / `3004` | 404 / 403 | 文件不存在 / 路径不在允许范围 |
| `4000` / `4001` | 422 / 400 | 参数错误 / 业务规则不满足 |

> 兼容承诺：已发布的 code 不复用、不改语义；新增错误只追加新 code。

---

## 6. 请求追踪

每次响应都带：

```http
X-Request-ID: 3f2b8c1e-9a44-4a1c-8f0e-2b7d5c6a1f33
```

客户端也可以**自带**该请求头发起请求，服务端会沿用（仅接受长度 ≤64 的
字母、数字、`-`、`_`、`.`）。用途：

1. **弱网重试**：同一次业务操作的重试共用一个 ID，服务端可据此定位重复请求；
2. **问题上报**：用户反馈时带上 `request_id`，服务端按 ID 检索完整链路日志。

推荐客户端在请求拦截器里生成 ID 并在失败弹窗中展示。

---

## 7. 限流与退避

触发限流时：

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
X-RateLimit-Limit: 100
X-RateLimit-Period: 60
```

```json
{"code": 429, "message": "IP 1.2.3.4 请求过于频繁", "data": {"retry_after": 60}, "request_id": "..."}
```

客户端应：

1. 读取 `Retry-After`（秒），**不要立即重试**；
2. 对同一接口做指数退避（如 2s、4s、8s），并加随机抖动；
3. 登录接口限流更严格（默认 5 次/分钟），连续失败后账号还会被锁定（`1008`）。

---

## 7.1 幂等重试

写操作（`POST` / `PUT` / `PATCH` / `DELETE`）如果可能被重试（弱网、超时、用户连点），
客户端应为**一次业务操作**生成唯一键并放进请求头：

```http
POST /api/orders
Idempotency-Key: 8f14e45f-ceea-467a-9f1b-1a2b3c4d5e6f
Authorization: Bearer <access_token>
```

服务端行为：

| 情况 | 响应 |
|---|---|
| 首次请求 | 正常执行，缓存响应（默认 24 小时） |
| 相同 key 再次到达 | 直接回放首次响应，带 `Idempotent-Replay: true` |
| key 非法（超长 / 含特殊字符） | 忽略该头，按普通请求处理 |
| 首次请求失败（非 2xx） | **不缓存**，客户端可修正后重试 |

约定与限制：

- key 只允许字母、数字、`-`、`_`、`.`，长度 ≤128（UUID / 雪花 ID / 业务单号均可）；
- 幂等作用域为「用户 + key」，不同用户的相同 key 互不干扰；
- 只对 JSON 响应生效，文件下载类接口不参与；
- **未实现并发锁**：同一 key 的两个请求完全同时到达时，仍可能都执行一次。
  支付、扣库存等强一致场景，必须在数据库层加唯一约束兜底。

建议：在「提交订单」「支付」「发券」这类不可重复的接口上使用；
查询类接口不需要，登录/注册通常也不需要（注册本身有唯一约束兜底）。

---

## 7.2 大文件分片上传

单次 `multipart/form-data` 上传大文件，一旦网络抖动就要从头再来。
分片上传把文件切开，断线后只补缺失部分。

### 流程

| 步骤 | 接口 | 说明 |
|---|---|---|
| 1 | `POST /util/file/chunked/init` | 告知文件大小，拿到 `upload_id` 与分片规划 |
| 2 | `POST /util/file/chunked/chunk` | 逐片上传，可乱序、可并发、可重传 |
| 3 | `GET /util/file/chunked/status` | 断线后查询缺哪些分片 |
| 4 | `POST /util/file/chunked/complete` | 合并，返回与普通上传一致的字段 |
| — | `DELETE /util/file/chunked/{upload_id}` | 放弃上传，立即释放磁盘 |

### 示例

```ts
// 1) 初始化
const init = await api.postApiUtilFileChunkedInit(http, {
  filename: 'video.mp4',
  total_size: file.size,
  category: 'videos',
})
const { upload_id, chunk_size, total_chunks } = init.data

// 2) 并发上传（建议 3-4 并发，避免把带宽和文件句柄打满）
const concurrency = 3
let cursor = 0
await Promise.all(
  Array.from({ length: concurrency }, async () => {
    while (cursor < total_chunks) {
      const index = cursor++
      const blob = file.slice(index * chunk_size, (index + 1) * chunk_size)
      await uploadChunk(upload_id, index, blob)   // 失败可按指数退避重试
    }
  }),
)

// 3) 合并
const done = await api.postApiUtilFileChunkedComplete(http, undefined, {
  params: { upload_id },
})
// done.data.url 即最终文件地址
```

### 行为约定

- **分片大小必须精确**：除最后一片外，每片都必须等于 `chunk_size`；
  最后一片是剩余字节数。大小不符会返回 400，不会静默接受。
- **重传幂等**：同一 `index` 重复上传是覆盖写，客户端重试无需特殊处理。
- **乱序安全**：服务端按 `index` 落盘，合并时按序拼接，先传第 3 片再传第 1 片没问题。
- **合并失败可重试**：缺片时返回 400 并在 `detail` 里列出缺口，补传后重试即可；
  合并过程用临时文件，中途失败不会留下"看起来完整"的半个文件。
- **会话会过期**：默认 24 小时，过期后需重新 `init`。
- **`upload_id` 是服务端生成的 32 位十六进制**，客户端不要自己构造或猜测。

### 与普通上传的关系

`complete` 的返回结构与 `POST /util/file/upload` **完全一致**
（`filename` / `file_path` / `url` / `file_size` / `mime_type` …），
客户端处理逻辑不需要分两套。

选择建议：小于 1MB 用普通上传（一次请求更简单），大于 1MB 用分片。

---

## 8. 数据格式

| 类型 | 约定 |
|---|---|
| 时间 | ISO 8601 字符串，如 `2026-11-07T17:45:00`，时区为服务端配置（默认 `Asia/Shanghai`） |
| ID | 整数；超过 JS 安全整数范围时服务端应以字符串返回（当前主键为自增整数，不涉及） |
| 金额 | 以「分」为单位的整数，避免浮点误差 |
| 布尔 | 数据库中的 `0/1` 应转换为 `true/false` 输出 |
| 空值 | 用 `null`，不用空字符串表示 |

> 时间字段目前不带时区后缀。跨时区客户端请按 `TIMEZONE` 配置的时区解析，
> 不要用设备本地时区直接 `new Date(str)`。

---

## 9. 客户端接入清单（可直接照做）

### 9.1 先试自动生成，再考虑手写

框架可以从 OpenAPI 契约直接生成 TypeScript 客户端，上面这些封装逻辑
（刷新串行化、幂等重试、请求追踪、错误分类）都已经内置：

```bash
python think.py make-client --lang ts --out client --base-url https://api.example.com
cd client && npm install && npm run typecheck
```

```ts
import { HttpClient, api, ApiError, NetworkError } from './client/src'

const http = new HttpClient({
  baseUrl: 'https://api.example.com',
  getAccessToken: () => storage.get('access_token'),
  getRefreshToken: () => storage.get('refresh_token'),
  onTokenRefreshed: (t) => {
    storage.set('access_token', t.accessToken)
    storage.set('refresh_token', t.refreshToken)  // 轮换后必须更新，否则下次刷新失败
  },
  onUnauthorized: () => redirectToLogin(),
})

const res = await api.postApiAuthLogin(http, { username, password })
// res.data 的字段与类型由服务端 response_model 决定
```

生成的类型精度取决于服务端契约。可以用体检命令确认：

```bash
python think.py openapi      # 会列出「响应类型是任意对象」的接口
```

### 9.2 手写封装（不使用生成器时）

```ts
// 1) 统一请求封装
async function request(path, options = {}, retried = false) {
  const accessToken = storage.get('access_token');
  const res = await fetch(BASE_URL + path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-Request-ID': uuid(),          // 便于服务端排障
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...options.headers,
    },
  });

  const body = await res.json();

  // 2) 过期 → 刷新一次并重放，避免重复弹登录框
  if (body.code === 1004 && !retried) {
    const ok = await refreshTokens();   // 用 refresh_token 换新，注意覆盖新 refresh_token
    if (ok) return request(path, options, true);
  }

  // 3) 凭证已吊销 → 清空本地态，跳登录
  if (body.code === 1005 || body.code === 1003) {
    storage.clear();
    redirectToLogin();
  }

  // 4) 失败统一抛出，业务层只判断 code
  if (body.code !== 200) throw new ApiError(body.code, body.message, body.request_id);

  return body.data;
}
```

注意事项：

1. **刷新要串行**：多个并发请求同时 401 时，只允许一个去刷新，其余等待结果，
   否则会因轮换导致后到的刷新请求把新 refresh_token 顶掉；
2. **不要在刷新接口上再触发刷新**，需显式排除；
3. Token 存储优先用系统安全存储（iOS Keychain / Android Keystore），不要放明文；
4. 登出时同时调用 `/auth/logout` 与清理本地存储，二者不能只做一件。

---

## 10. 版本演进

- 服务端通过 `ROUTE_PREFIX` 提供版本前缀，如 `/api/v1`；
- 破坏性变更必须升前缀，旧前缀至少保留一个次要版本周期；
- 新增字段不影响旧客户端；删除字段需先标记 deprecated 并保留一个版本；
- 错误码只增不改（见第 5 节兼容承诺）。

---

## 11. 当前边界（明确不支持，避免客户端误用）

| 能力 | 现状 | 说明 |
|---|---|---|
| 服务端推送 | 不支持 | 需另接 WebSocket / 第三方推送 |
| 文件分片上传 | 不支持 | 单次 `multipart/form-data`，受 `UPLOAD_MAX_FILE_SIZE` 限制 |
| 响应压缩 / ETag | 由 Nginx 负责 | 应用层不处理 |
| GraphQL / gRPC | 不支持 | 仅 REST + JSON |
| 多角色（一人多角色） | 不支持 | 当前为单角色模型，见 [权限控制](rbac.md) |

接口级权限与幂等键**已支持**，用法见第 3.7 节与第 7.1 节。

以上任一项若成为客户端的硬需求，属于框架能力扩展，需要单独排期。
