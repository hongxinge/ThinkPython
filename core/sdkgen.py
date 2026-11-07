"""TypeScript 客户端 SDK 生成器

从 OpenAPI schema 生成零依赖的 TypeScript 客户端，客户端团队拿到即可用，
不需要再装 openapi-generator（省掉 Java 运行时），也不需要手写请求封装。

生成物结构::

    <out>/
      README.md          用法与注意事项
      package.json       包描述（可直接 npm link 或发布）
      tsconfig.json      严格模式配置
      src/types.ts       Schema 接口 + 统一响应类型
      src/client.ts      HttpClient（双 Token 自动刷新、幂等键、请求追踪）
      src/api.ts         按路径生成的类型化方法
      src/index.ts       统一导出

三条设计约束：

1. **必须能编译**。生成的代码走 TypeScript 严格模式，不用 any 逃逸（必要时用 unknown）。
2. **只依赖 fetch**。不引入 axios，浏览器 / Node 18+ / 小程序（需替换 fetchImpl）都能跑。
3. **类型退化要可见**。接口没声明 ``response_model`` 时类型只能是 ``unknown``，
   生成器会在 README 与命令行提示里明确指出，而不是假装类型很完整。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

# ---------------------------------------------------------------------------
# 命名与类型映射
# ---------------------------------------------------------------------------

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")
_HTTP_METHOD_ORDER = ("get", "post", "put", "patch", "delete", "head", "options")


def _pascal(text: str) -> str:
    """把任意片段转为 PascalCase，非字母数字视为分隔符"""
    parts = [p for p in re.split(r"[^A-Za-z0-9]+", text) if p]
    return "".join(p[:1].upper() + p[1:] for p in parts) or "X"


def _method_name(method: str, path: str) -> str:
    """按 ``方法 + 路径`` 生成方法名

    为什么不用 operationId：FastAPI 默认生成 ``login_api_auth_login_post``
    这类把函数名和路径拼在一起的串，客户端读起来噪音很大。
    """
    segments = [_pascal(s.strip("{}")) for s in path.split("/") if s]
    return method.lower() + "".join(segments)


def _safe_prop(name: str) -> str:
    """属性名合法则原样输出，否则加引号"""
    return name if _IDENTIFIER_RE.match(name) else json.dumps(name, ensure_ascii=False)


def _safe_param(name: str) -> str:
    """参数名若不是合法标识符，做保守替换"""
    if _IDENTIFIER_RE.match(name):
        return name
    cleaned = re.sub(r"[^A-Za-z0-9_$]", "_", name)
    if not cleaned or cleaned[0].isdigit():
        cleaned = "_" + cleaned
    return cleaned


# OpenAPI 基础类型 → TS
_PRIMITIVES = {
    "string": "string",
    "integer": "number",
    "number": "number",
    "boolean": "boolean",
    "null": "null",
}


def ts_type(schema: Optional[Dict[str, Any]], depth: int = 0) -> str:
    """把 JSON Schema 转为 TypeScript 类型表达式

    Args:
        schema: JSON Schema 片段
        depth: 嵌套深度，超过 4 层不再展开内联对象，避免生成巨大字面量类型

    Returns:
        str: TS 类型表达式
    """
    if not schema or not isinstance(schema, dict):
        return "unknown"

    # $ref 一律引用名字，不展开——既避免循环引用，也让类型可读
    ref = schema.get("$ref")
    if isinstance(ref, str):
        return ref.rsplit("/", 1)[-1]

    # 枚举
    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and enum_values:
        literals = [json.dumps(v, ensure_ascii=False) for v in enum_values]
        base = " | ".join(literals)
        return f"({base})" if schema.get("nullable") else base

    const = schema.get("const")
    if const is not None:
        return json.dumps(const, ensure_ascii=False)

    # 组合类型
    for key, joiner in (("oneOf", " | "), ("anyOf", " | "), ("allOf", " & ")):
        variants = schema.get(key)
        if isinstance(variants, list) and variants:
            rendered = [ts_type(v, depth) for v in variants]
            # 去掉重复项，anyOf 里常见 [T, {type: null}]
            unique: List[str] = []
            for item in rendered:
                if item not in unique:
                    unique.append(item)
            return joiner.join(unique)

    stype = schema.get("type")

    # type 可能是数组，如 ["string", "null"]
    if isinstance(stype, list):
        parts = [ts_type({**schema, "type": t, "nullable": False}, depth) for t in stype]
        unique = []
        for item in parts:
            if item not in unique:
                unique.append(item)
        result = " | ".join(unique)
        return result

    if stype in _PRIMITIVES:
        base = _PRIMITIVES[stype]
        return f"{base} | null" if schema.get("nullable") else base

    if stype == "array":
        items = schema.get("items")
        inner = ts_type(items, depth + 1) if isinstance(items, dict) else "unknown"
        # 联合类型作为数组元素时加括号，避免 A | B[] 被误读
        if " | " in inner:
            inner = f"({inner})"
        base = f"{inner}[]"
        return f"{base} | null" if schema.get("nullable") else base

    if stype == "object" or "properties" in schema or "additionalProperties" in schema:
        props = schema.get("properties")
        if isinstance(props, dict) and props:
            if depth >= 4:
                return "Record<string, unknown>"
            required = set(schema.get("required") or [])
            lines = ["{"]
            for prop_name, prop_schema in props.items():
                optional = "" if prop_name in required else "?"
                prop_type = ts_type(prop_schema, depth + 1)
                desc = ""
                if isinstance(prop_schema, dict):
                    desc = (prop_schema.get("description") or "").strip().replace("\n", " ")
                    if prop_schema.get("title") and not desc:
                        desc = str(prop_schema["title"])
                comment = f"  /** {desc} */\n" if desc else ""
                lines.append(f"{comment}  {_safe_prop(prop_name)}{optional}: {prop_type}")
            lines.append("}")
            base = "\n".join(lines)
            return f"({base}) | null" if schema.get("nullable") else base

        extra = schema.get("additionalProperties")
        if isinstance(extra, dict):
            base = f"Record<string, {ts_type(extra, depth + 1)}>"
        else:
            base = "Record<string, unknown>"
        return f"{base} | null" if schema.get("nullable") else base

    return "unknown"


def _render_schema_block(name: str, schema: Dict[str, Any]) -> str:
    """把一个顶级 schema 渲染为接口或类型别名"""
    description = (schema.get("description") or "").strip()

    doc = ""
    if description:
        doc = f"/** {description.replace(chr(10), ' ')} */\n"

    props = schema.get("properties")
    stype = schema.get("type")

    # 纯枚举 / 联合 → 类型别名，不用 interface
    if not isinstance(props, dict) or not props:
        return f"{doc}export type {name} = {ts_type(schema)}"

    required = set(schema.get("required") or [])
    lines = [f"{doc}export interface {name} {{"]
    for prop_name, prop_schema in props.items():
        optional = "" if prop_name in required else "?"
        prop_type = ts_type(prop_schema)
        comment = ""
        if isinstance(prop_schema, dict):
            desc = (prop_schema.get("description") or "").strip().replace("\n", " ")
            if desc:
                comment = f"  /** {desc} */\n"
        lines.append(f"{comment}  {_safe_prop(prop_name)}{optional}: {prop_type}")
    lines.append("}")

    # 额外字段：Pydantic 允许 model_config = ConfigDict(extra="allow")
    if stype == "object" and schema.get("additionalProperties") is True:
        lines.append(f"export interface {name} extends Record<string, unknown> {{}}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 操作解析
# ---------------------------------------------------------------------------

class Operation:
    """一个 HTTP 操作的生成模型"""

    __slots__ = (
        "method",
        "path",
        "name",
        "summary",
        "description",
        "path_params",
        "query_params",
        "body_type",
        "body_required",
        "result_type",
    )

    def __init__(
        self,
        method: str,
        path: str,
        raw: Dict[str, Any],
        components: Optional[Dict[str, Any]] = None,
    ):
        self.method = method.upper()
        self.path = path
        self.name = _method_name(method, path)
        self.summary = (raw.get("summary") or "").strip()
        self.description = (raw.get("description") or "").strip()
        self.path_params: List[Dict[str, Any]] = []
        self.query_params: List[Dict[str, Any]] = []
        self.body_type: Optional[str] = None
        self.body_required = False
        self.result_type = "unknown"

        for param in raw.get("parameters") or []:
            if not isinstance(param, dict) or "$ref" in param:
                continue
            location = param.get("in")
            entry = {
                "name": param.get("name") or "param",
                "type": ts_type(param.get("schema")),
                "required": bool(param.get("required")),
                "description": (param.get("description") or "").strip(),
            }
            if location == "path":
                # path 参数在 OpenAPI 中恒为必填
                entry["required"] = True
                self.path_params.append(entry)
            elif location == "query":
                self.query_params.append(entry)

        body = raw.get("requestBody")
        if isinstance(body, dict):
            self.body_required = bool(body.get("required"))
            content = body.get("content") or {}
            for media in ("application/json", "application/x-www-form-urlencoded", "multipart/form-data"):
                if media in content:
                    schema = (content[media] or {}).get("schema")
                    self.body_type = ts_type(schema)
                    break

        # 成功响应类型
        responses = raw.get("responses") or {}
        for code in ("200", "201", "202", "2XX"):
            if code not in responses:
                continue
            content = (responses[code] or {}).get("content") or {}
            for media in ("application/json", "*/*"):
                if media in content:
                    schema = (content[media] or {}).get("schema")
                    self.result_type = _normalize_result_type(schema, components)
                    break
            break

    @property
    def signature_params(self) -> List[str]:
        """生成函数形参列表（不含 http 与 options）"""
        parts: List[str] = []
        for param in self.path_params:
            parts.append(f"{_safe_param(param['name'])}: {param['type']}")
        if self.body_type:
            optional = "" if self.body_required else "?"
            parts.append(f"body{optional}: {self.body_type}")
        return parts

    @property
    def query_type(self) -> Optional[str]:
        if not self.query_params:
            return None
        fields = []
        for param in self.query_params:
            optional = "" if param["required"] else "?"
            fields.append(f"{_safe_prop(param['name'])}{optional}: {param['type']}")
        return "{ " + "; ".join(fields) + " }"

    def render(self) -> str:
        """渲染为 TS 函数"""
        doc_lines: List[str] = []
        title = self.summary or f"{self.method} {self.path}"
        doc_lines.append(f"/**\n * {title}")
        if self.summary:
            doc_lines.append(f" * {self.method} {self.path}")
        if self.description and not self.summary:
            brief = self.description.split("\n")[0].strip()
            if brief:
                doc_lines.append(f" * {brief}")
        doc_lines.append(" */")

        params = ["http: HttpClient", *self.signature_params]
        query_type = self.query_type
        has_query = query_type is not None
        if has_query:
            params.append(f"query?: {query_type}")
        params.append("options?: RequestOptions")

        # 组装传给 http.request 的 options
        # 注意：query 在客户端统一走 RequestOptions.params（fetch 的查询串）
        fields: List[str] = []
        if self.body_type:
            fields.append("body")

        merged_params: List[str] = []
        if has_query:
            merged_params.append("...query")
        for param in self.path_params:
            merged_params.append(f"{_safe_prop(param['name'])}: {_safe_param(param['name'])}")

        if merged_params:
            fields.append(f"params: {{ ...options?.params, {', '.join(merged_params)} }}")

        options_expr = "{ ...options, " + ", ".join(fields) + " }" if fields else "options"
        method_literal = json.dumps(self.method)
        path_literal = json.dumps(self.path)

        return (
            "\n".join(doc_lines)
            + "\n"
            + f"export function {self.name}({', '.join(params)}): Promise<ApiResponse<{self.result_type}>> {{\n"
            + f"  return http.request<{self.result_type}>({method_literal}, {path_literal}, {options_expr})\n"
            + "}"
        )


def _lookup_ref(name: str, components: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """按 schema 名查 components"""
    if not components:
        return None
    target = components.get(name)
    return target if isinstance(target, dict) else None


def is_response_wrapper(schema: Dict[str, Any], components: Optional[Dict[str, Any]]) -> bool:
    """判断某个 schema 是否为统一响应包装（{code, message, data}）

    服务端用 ``ApiResponse[T]`` 声明后，FastAPI 会生成 ``ApiResponse_LoginData_``
    这类扁平化模型。客户端已经有自己的 ``ApiResponse<T>`` 泛型，
    必须把这一层剥掉，否则会生成 ``ApiResponse<ApiResponse<LoginData>>``。
    """
    props = schema.get("properties")
    if not isinstance(props, dict):
        return False
    return {"code", "message", "data"}.issubset(set(props.keys()))


def _strip_optional_null(type_expr: str) -> str:
    """剥掉尾部的 ``| null``

    服务端 ``ApiResponse.data`` 声明为 ``Optional[T]``（错误响应里确实是 null），
    因此成功响应的 schema 是 ``anyOf: [T, null]``。但走到客户端 ``data`` 分支时
    请求已经成功，``data`` 一定有值。保留 ``| null`` 只会让业务代码到处判空，
    反而掩盖真正该检查的地方。

    若某个接口业务上确实可能返回 null，请在服务端为它单独声明模型或使用
    ``Optional`` 字段，而不是依赖包装层的 null。
    """
    suffix = " | null"
    return type_expr[: -len(suffix)] if type_expr.endswith(suffix) else type_expr


def _normalize_result_type(
    schema: Optional[Dict[str, Any]],
    components: Optional[Dict[str, Any]] = None,
) -> str:
    """成功响应类型归一化

    三种情况：

    1. ``$ref`` 指向响应包装 → 取出 ``data`` 的类型，客户端泛型只包一层
    2. ``additionalProperties: true``（``response_model=dict``）→ ``unknown``，
       并让调用方必须显式断言，这是有意为之的"不假装类型完整"
    3. 其他 → 直接映射
    """
    if not schema or not isinstance(schema, dict):
        return "unknown"

    ref = schema.get("$ref")
    if isinstance(ref, str):
        ref_name = ref.rsplit("/", 1)[-1]
        target = _lookup_ref(ref_name, components)
        if target and is_response_wrapper(target, components):
            data_schema = (target.get("properties") or {}).get("data")
            if isinstance(data_schema, dict):
                # data 可能是 $ref，也可能是 anyOf[T, null]
                return _strip_optional_null(ts_type(data_schema))
            return "unknown"
        return ref_name

    if schema.get("additionalProperties") is True and not schema.get("properties"):
        return "unknown"

    return _strip_optional_null(ts_type(schema))


def wrapper_schema_names(schema: Dict[str, Any]) -> set:
    """收集所有"响应包装" schema 名，生成 types.ts 时跳过它们

    客户端用泛型 ``ApiResponse<T>`` 表达同一结构，再生成一份扁平接口纯属噪音。
    """
    components = (schema.get("components") or {}).get("schemas") or {}
    names = set()
    for name, item in components.items():
        if isinstance(item, dict) and is_response_wrapper(item, components):
            names.add(name)
    return names


# ---------------------------------------------------------------------------
# 代码模板
# ---------------------------------------------------------------------------

_CLIENT_TS = '''/**
 * ThinkPython 生成的 HTTP 客户端
 *
 * 只依赖 fetch，浏览器 / Node 18+ / 小程序（传 fetchImpl）均可用。
 * 内置能力：
 *   - 双 Token：access 过期（错误码 1004）自动刷新并重放一次请求
 *   - 并发串行：多个请求同时触发刷新时只发一次刷新请求
 *   - 幂等键：写请求传 idempotencyKey，服务端回放首次成功响应
 *   - 请求追踪：自动生成 X-Request-ID，错误对象里带 requestId
 */

import type { ApiResponse, TokenPair } from './types'

/** 业务错误码（与服务端 core/error_codes.py 对应） */
export const ErrorCode = {
  UNAUTHORIZED: 1001,
  TOKEN_MALFORMED: 1002,
  TOKEN_INVALID: 1003,
  TOKEN_EXPIRED: 1004,
  TOKEN_REVOKED: 1005,
  BAD_CREDENTIALS: 1006,
  FORBIDDEN: 1010,
  ACCOUNT_LOCKED: 1008,
  REFRESH_TOKEN_INVALID: 1009,
} as const

export interface RequestOptions {
  /** 追加或覆盖请求头 */
  headers?: Record<string, string>
  /** URL 查询参数，值为 undefined / null 时自动跳过 */
  params?: Record<string, string | number | boolean | undefined | null>
  /** 请求体，通常是对象；传 FormData 时不设置 Content-Type（浏览器自动加 boundary） */
  body?: unknown
  /** 写请求的幂等键，服务端会用相同 key 回放首次成功响应 */
  idempotencyKey?: string
  /** 单次请求超时（毫秒），默认取客户端配置 */
  timeoutMs?: number
  /** 该请求跳过自动刷新（用于登录、刷新等自身可能返回 1004 的场景） */
  skipAuthRefresh?: boolean
  /** 该请求不附带 Authorization */
  anonymous?: boolean
  /** 透传 AbortSignal */
  signal?: AbortSignal
}

export interface ClientOptions {
  /** 服务端根地址，如 https://api.example.com（末尾斜杠会被去掉） */
  baseUrl: string
  /** 读取当前 access token */
  getAccessToken?: () => string | null | undefined
  /** 读取当前 refresh token */
  getRefreshToken?: () => string | null | undefined
  /** 刷新成功后的回调，请在这里持久化新的 Token 对 */
  onTokenRefreshed?: (tokens: TokenPair) => void
  /** 需要重新登录时回调（1005 / 刷新失败等），请在这里清理本地登录态 */
  onUnauthorized?: (error: ApiError) => void
  /** 默认请求头 */
  headers?: Record<string, string>
  /** 默认超时（毫秒），默认 20000 */
  timeoutMs?: number
  /** 自定义 fetch 实现（小程序、Node 旧版本、测试注入） */
  fetchImpl?: typeof fetch
  /** 自定义请求 ID 生成器，默认用 crypto.randomUUID 或时间戳随机串 */
  requestIdFactory?: () => string
}

/** 服务端返回的业务错误 */
export class ApiError extends Error {
  /** HTTP 状态码 */
  readonly status: number
  /** 业务错误码（1001/1004/1010…） */
  readonly code: number
  /** 服务端附加的错误数据 */
  readonly data: unknown
  /** 服务端请求 ID，反馈问题时提供给后端可精确定位 */
  readonly requestId?: string

  constructor(message: string, status: number, code: number, data: unknown, requestId?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.data = data
    this.requestId = requestId
  }

  /** access token 过期：调用方一般不需要手动处理，客户端会自动刷新重试 */
  get isTokenExpired(): boolean {
    return this.code === ErrorCode.TOKEN_EXPIRED
  }

  /** 凭证已失效：必须重新登录 */
  get needsRelogin(): boolean {
    return (
      this.code === ErrorCode.TOKEN_REVOKED ||
      this.code === ErrorCode.TOKEN_INVALID ||
      this.code === ErrorCode.REFRESH_TOKEN_INVALID
    )
  }
}

/** 网络层失败（断网、超时、DNS 失败），区别于服务端返回的业务错误 */
export class NetworkError extends Error {
  readonly cause?: unknown
  constructor(message: string, cause?: unknown) {
    super(message)
    this.name = 'NetworkError'
    this.cause = cause
  }
}

function defaultRequestId(): string {
  const globalCrypto = (globalThis as { crypto?: Crypto }).crypto
  if (globalCrypto && typeof globalCrypto.randomUUID === 'function') {
    return globalCrypto.randomUUID()
  }
  return `req-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
}

export class HttpClient {
  private readonly options: ClientOptions
  private readonly baseUrl: string
  /** 进行中的刷新请求：用于并发串行化，避免同时发多个 refresh */
  private refreshing: Promise<TokenPair> | null = null

  constructor(options: ClientOptions) {
    this.options = options
    this.baseUrl = options.baseUrl.replace(/\\/+$/, '')
  }

  /** 发起请求并返回统一响应体 */
  async request<T>(
    method: string,
    path: string,
    options: RequestOptions = {},
  ): Promise<ApiResponse<T>> {
    return this.execute<T>(method, path, options, true)
  }

  /** 用 refresh token 换取新的 Token 对 */
  async refreshTokens(): Promise<TokenPair> {
    const refreshToken = this.options.getRefreshToken?.()
    if (!refreshToken) {
      throw new ApiError('缺少 refresh token，请重新登录', 401, ErrorCode.REFRESH_TOKEN_INVALID, null)
    }

    const response = await this.execute<{
      access_token: string
      refresh_token?: string
      expires_in?: number
    }>(
      'POST',
      '/api/auth/refresh',
      { body: { refresh_token: refreshToken }, anonymous: true, skipAuthRefresh: true },
      false,
    )

    const tokens: TokenPair = {
      accessToken: response.data.access_token,
      // 服务端开启轮换时一定会返回新的 refresh_token
      refreshToken: response.data.refresh_token ?? refreshToken,
      expiresIn: response.data.expires_in ?? 0,
    }
    this.options.onTokenRefreshed?.(tokens)
    return tokens
  }

  private async execute<T>(
    method: string,
    path: string,
    options: RequestOptions,
    allowRetry: boolean,
  ): Promise<ApiResponse<T>> {
    const url = this.buildUrl(path, options.params)
    const headers: Record<string, string> = {
      Accept: 'application/json',
      ...this.options.headers,
      ...options.headers,
    }

    const isFormData =
      typeof FormData !== 'undefined' && options.body instanceof FormData
    if (options.body !== undefined && !isFormData) {
      headers['Content-Type'] = headers['Content-Type'] ?? 'application/json'
    }

    if (!options.anonymous) {
      const token = this.options.getAccessToken?.()
      if (token) {
        headers.Authorization = `Bearer ${token}`
      }
    }

    headers['X-Request-ID'] = (this.options.requestIdFactory ?? defaultRequestId)()

    if (options.idempotencyKey) {
      headers['Idempotency-Key'] = options.idempotencyKey
    }

    const controller = new AbortController()
    const timeoutMs = options.timeoutMs ?? this.options.timeoutMs ?? 20000
    const timer = setTimeout(() => controller.abort(), timeoutMs)
    if (options.signal) {
      options.signal.addEventListener('abort', () => controller.abort(), { once: true })
    }

    const fetcher = this.options.fetchImpl ?? fetch
    let raw: Response
    try {
      raw = await fetcher(url, {
        method,
        headers,
        body:
          options.body === undefined
            ? undefined
            : isFormData
              ? (options.body as FormData)
              : JSON.stringify(options.body),
        signal: controller.signal,
      })
    } catch (error) {
      // 超时与断网都归为网络层错误，调用方可据此做重试
      const aborted = (error as { name?: string })?.name === 'AbortError'
      throw new NetworkError(aborted ? `请求超时（${timeoutMs}ms）` : '网络请求失败', error)
    } finally {
      clearTimeout(timer)
    }

    const requestId = raw.headers.get('X-Request-ID') ?? headers['X-Request-ID']
    const contentType = raw.headers.get('content-type') ?? ''

    if (!contentType.includes('application/json')) {
      // 文件下载等非 JSON 响应：这里不做处理，需要时请用 httpRaw
      if (!raw.ok) {
        throw new ApiError(`请求失败（HTTP ${raw.status}）`, raw.status, raw.status, null, requestId)
      }
      throw new ApiError('响应不是 JSON，二进制响应请使用 httpRaw', raw.status, 0, null, requestId)
    }

    const payload = (await raw.json()) as ApiResponse<T>

    if (raw.ok && (payload.code === 200 || payload.code === 0)) {
      return payload
    }

    const error = new ApiError(
      payload.message || `请求失败（HTTP ${raw.status}）`,
      raw.status,
      typeof payload.code === 'number' ? payload.code : raw.status,
      payload.data,
      payload.request_id ?? requestId,
    )

    // access token 过期：自动刷新后重放一次，业务代码完全无感
    if (
      allowRetry &&
      !options.skipAuthRefresh &&
      error.code === ErrorCode.TOKEN_EXPIRED &&
      this.options.getRefreshToken?.()
    ) {
      await this.ensureRefreshed()
      return this.execute<T>(method, path, { ...options, idempotencyKey: options.idempotencyKey }, false)
    }

    if (error.needsRelogin) {
      this.options.onUnauthorized?.(error)
    }

    throw error
  }

  /** 保证同一时刻只有一个刷新在进行 */
  private async ensureRefreshed(): Promise<TokenPair> {
    if (!this.refreshing) {
      this.refreshing = this.refreshTokens().finally(() => {
        this.refreshing = null
      })
    }
    try {
      return await this.refreshing
    } catch (error) {
      this.options.onUnauthorized?.(
        error instanceof ApiError
          ? error
          : new ApiError('刷新 Token 失败，请重新登录', 401, ErrorCode.REFRESH_TOKEN_INVALID, null),
      )
      throw error
    }
  }

  private buildUrl(path: string, params?: RequestOptions['params']): string {
    const url = `${this.baseUrl}${path.startsWith('/') ? path : `/${path}`}`
    if (!params) {
      return url
    }
    const search = new URLSearchParams()
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined || value === null) {
        continue
      }
      search.append(key, String(value))
    }
    const qs = search.toString()
    return qs ? `${url}?${qs}` : url
  }
}
'''

_INDEX_TS = '''export { HttpClient, ApiError, NetworkError, ErrorCode } from './client'
export type { ClientOptions, RequestOptions } from './client'
export * from './types'
export * from './api'
'''

_TSCONFIG = '''{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "lib": ["ES2020", "DOM"],
    "declaration": true,
    "strict": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src/**/*.ts"]
}
'''


def _render_types(schema: Dict[str, Any]) -> str:
    """生成 types.ts"""
    schemas = (schema.get("components") or {}).get("schemas") or {}

    header = (
        "/**\n"
        " * 由 think.py make-client 自动生成，请勿手工修改。\n"
        " * 服务端契约变更后重新生成即可。\n"
        " */\n\n"
        "/** 服务端统一响应包装 */\n"
        "export interface ApiResponse<T = unknown> {\n"
        "  /** 业务状态码，200 表示成功 */\n"
        "  code: number\n"
        "  /** 提示信息 */\n"
        "  message: string\n"
        "  /** 业务数据 */\n"
        "  data: T\n"
        "  /** 请求追踪 ID，反馈问题时提供给后端 */\n"
        "  request_id?: string\n"
        "}\n\n"
        "/** Token 对 */\n"
        "export interface TokenPair {\n"
        "  accessToken: string\n"
        "  refreshToken: string\n"
        "  /** access token 有效期（秒） */\n"
        "  expiresIn: number\n"
        "}\n"
    )

    blocks: List[str] = []
    skip_names = wrapper_schema_names(schema)
    for name in sorted(schemas):
        if name in skip_names:
            continue
        block = _render_schema_block(name, schemas[name] or {})
        if block.strip():
            blocks.append(block)

    if not blocks:
        return header

    return header + "\n\n" + "\n\n".join(blocks) + "\n"


def _render_api(operations: Sequence[Operation]) -> str:
    """生成 api.ts"""
    header = (
        "/**\n"
        " * 由 think.py make-client 自动生成，请勿手工修改。\n"
        " *\n"
        " * 每个方法对应一个 HTTP 接口，返回统一响应体 ApiResponse<T>。\n"
        " * 非 2xx 或业务码非成功时会抛 ApiError，请用 try/catch 或 .catch 处理。\n"
        " */\n\n"
        "import type { ApiResponse } from './types'\n"
        "import type { HttpClient, RequestOptions } from './client'\n"
    )

    # 引用到的 schema 类型需要 import（值类型 + 仅类型导入）
    used_refs: List[str] = []
    for op in operations:
        for candidate in (op.body_type, op.result_type):
            if not candidate:
                continue
            for token in re.findall(r"\b[A-Z][A-Za-z0-9_]*\b", candidate):
                if token not in used_refs:
                    used_refs.append(token)

    if used_refs:
        header += "import type { " + ", ".join(sorted(used_refs)) + " } from './types'\n"

    body = "\n\n".join(op.render() for op in operations)
    return header + "\n\n" + body + "\n"


def _render_readme(
    operations: Sequence[Operation],
    report: Optional[Dict[str, Any]],
    base_url_hint: str,
) -> str:
    lines: List[str] = [
        "# ThinkPython 客户端 SDK",
        "",
        "由 `python think.py make-client` 从服务端 OpenAPI 契约生成，**请勿手工修改**。",
        "接口变更后重新生成即可。",
        "",
        "## 安装",
        "",
        "```bash",
        "npm install",
        "npm run build",
        "```",
        "",
        "## 快速开始",
        "",
        "```ts",
        "import { HttpClient, api, ApiError } from './src'",
        "",
        "const http = new HttpClient({",
        f"  baseUrl: '{base_url_hint}',",
        "  getAccessToken: () => localStorage.getItem('access_token'),",
        "  getRefreshToken: () => localStorage.getItem('refresh_token'),",
        "  onTokenRefreshed: (tokens) => {",
        "    localStorage.setItem('access_token', tokens.accessToken)",
        "    localStorage.setItem('refresh_token', tokens.refreshToken)",
        "  },",
        "  onUnauthorized: () => {",
        "    // 1005 / 刷新失败：清理登录态并跳登录页",
        "    localStorage.clear()",
        "    location.href = '/login'",
        "  },",
        "})",
        "",
        "async function login() {",
        "  const res = await api.postApiAuthLogin(http, { username: 'alice', password: 'Passw0rd!' })",
        "  // res.data 含 access_token / refresh_token / expires_in",
        "}",
        "```",
        "",
        "## 已内置的客户端必备能力",
        "",
        "| 能力 | 说明 |",
        "|---|---|",
        "| Token 自动刷新 | 收到业务码 1004 时自动调 `/auth/refresh` 并重放原请求，业务代码无感 |",
        "| 并发刷新串行化 | 多个请求同时过期时只发一次刷新请求，避免轮换把彼此顶掉 |",
        "| 幂等重试 | `api.xxx(http, body, { idempotencyKey: 'order-1' })`，弱网重试不会重复下单 |",
        "| 请求追踪 | 自动生成 `X-Request-ID`，`ApiError.requestId` 可直接报给后端 |",
        "| 错误分类 | `ApiError.isTokenExpired` / `needsRelogin` 区分「刷新」与「重新登录」 |",
        "| 网络与业务分离 | 断网超时抛 `NetworkError`，服务端拒绝抛 `ApiError` |",
        "",
        "## 错误处理约定",
        "",
        "```ts",
        "try {",
        "  await api.getApiAuthProfile(http)",
        "} catch (e) {",
        "  if (e instanceof NetworkError) {",
        "    // 提示检查网络，可安全重试",
        "  } else if (e instanceof ApiError) {",
        "    if (e.needsRelogin) return toLoginPage()",
        "    toast(e.message)  // 业务错误，message 可直接展示",
        "  }",
        "}",
        "```",
        "",
        f"## 接口清单（{len(operations)} 个）",
        "",
        "| 方法 | 路径 | 生成函数 |",
        "|---|---|---|",
    ]

    for op in operations:
        lines.append(f"| {op.method} | `{op.path}` | `{op.name}` |")

    if report:
        counts = report.get("counts") or {}
        loose = counts.get("loose_response", 0)
        if loose:
            lines += [
                "",
                "## 类型完整度提示",
                "",
                f"有 **{loose}** 个接口未声明 `response_model`，其返回类型只能是 `unknown`。",
                "这不是生成器的缺陷——服务端契约里确实没有字段信息。",
                "要拿到精确类型，请在控制器路由上声明 `response_model`，然后重新生成。",
            ]

    lines += [
        "",
        "## 小程序 / Node 环境",
        "",
        "- Node 18+ 自带 fetch，可直接用；",
        "- 小程序没有 fetch，注入 `fetchImpl`：",
        "",
        "```ts",
        "new HttpClient({ baseUrl, fetchImpl: (url, init) => wxRequest(url, init) })",
        "```",
        "",
    ]

    return "\n".join(lines)


def generate(
    out_dir: Path | str,
    schema: Optional[Dict[str, Any]] = None,
    base_url_hint: str = "http://localhost:8000",
    report: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """生成完整的 TS SDK 到指定目录

    Args:
        out_dir: 输出目录，不存在会自动创建
        schema: OpenAPI 文档；为 None 时从 app 现场构建
        base_url_hint: README 示例中的服务端地址
        report: 契约体检结果，用于在 README 中提示类型完整度

    Returns:
        Dict: 生成统计（文件列表、接口数、是否存在类型退化）
    """
    if schema is None:
        from core.openapi_export import build_schema

        schema = build_schema()

    root = Path(out_dir)
    src = root / "src"
    src.mkdir(parents=True, exist_ok=True)

    operations: List[Operation] = []
    components = (schema.get("components") or {}).get("schemas") or {}
    for path, item in (schema.get("paths") or {}).items():
        for method in _HTTP_METHOD_ORDER:
            raw = item.get(method)
            if isinstance(raw, dict):
                operations.append(Operation(method, path, raw, components))

    # 同名方法去重（不同路径可能生成相同名字，例如 /a/{id} 与 /a/id）
    seen: Dict[str, int] = {}
    for op in operations:
        if op.name in seen:
            seen[op.name] += 1
            op.name = f"{op.name}{seen[op.name]}"
        else:
            seen[op.name] = 1

    written: List[str] = []

    (src / "types.ts").write_text(_render_types(schema), encoding="utf-8")
    written.append("src/types.ts")

    (src / "client.ts").write_text(_CLIENT_TS, encoding="utf-8")
    written.append("src/client.ts")

    (src / "api.ts").write_text(_render_api(operations), encoding="utf-8")
    written.append("src/api.ts")

    (src / "index.ts").write_text(_INDEX_TS, encoding="utf-8")
    written.append("src/index.ts")

    (root / "tsconfig.json").write_text(_TSCONFIG, encoding="utf-8")
    written.append("tsconfig.json")

    package = {
        "name": "thinkpython-client",
        "version": "1.0.0",
        "description": "由 ThinkPython 从 OpenAPI 契约生成的 TypeScript 客户端",
        "type": "module",
        "main": "dist/index.js",
        "types": "dist/index.d.ts",
        "files": ["dist", "README.md"],
        "scripts": {
            "build": "tsc -p tsconfig.json",
            "typecheck": "tsc -p tsconfig.json --noEmit",
        },
        "devDependencies": {"typescript": "^5.4.0"},
    }
    (root / "package.json").write_text(
        json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    written.append("package.json")

    (root / "README.md").write_text(
        _render_readme(operations, report, base_url_hint), encoding="utf-8"
    )
    written.append("README.md")

    type_degraded = sum(1 for op in operations if op.result_type == "unknown")

    return {
        "out_dir": str(root.resolve()),
        "files": written,
        "operations": len(operations),
        "type_degraded": type_degraded,
    }
