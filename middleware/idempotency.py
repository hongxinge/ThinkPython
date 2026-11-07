"""幂等键中间件

作用：
    让客户端可以安全重试写请求。客户端为一次业务操作生成 ``Idempotency-Key``，
    服务端缓存首次成功的响应；相同 key 再次到达时直接回放，不重复执行。

执行位置（重要）：
    本中间件必须注册在**认证中间件之后**（即更内层），原因：
    1. 需要读取 ``current_user`` 做用户维度隔离；
    2. 认证失败的请求不应写入幂等缓存。

响应约定：
    回放的响应带 ``Idempotent-Replay: true`` 头，客户端可据此判断这是缓存结果。

安全与边界：
    - key 只接受字母、数字、``-``、``_``、``.``，长度 ≤128，非法则忽略（按普通请求处理）；
    - 只缓存 2xx 且 Content-Type 为 JSON 的响应，避免把错误或文件流固化；
    - 响应体超过 ``IDEMPOTENCY_MAX_BODY_BYTES`` 不缓存，防止大响应把缓存打满；
    - 缓存不可用时退化为普通请求，不影响可用性。

实现说明：
    ASGI 版本**边转发边收集**响应体，不再需要"读完再重建 Response"。
    函数式版本（``idempotency_middleware``）保留兼容，但仍受
    ``BaseHTTPMiddleware`` 的流包装影响。
"""

import json
from typing import List, Optional, Tuple

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from loguru import logger

from config.idempotency import (
    IDEMPOTENCY_ENABLED,
    IDEMPOTENCY_HEADER,
    IDEMPOTENCY_MAX_KEY_LENGTH,
    IDEMPOTENCY_METHODS,
    IDEMPOTENCY_SAFE_CHARS,
    IDEMPOTENCY_TTL,
)

# 回放标记响应头
REPLAY_HEADER = "Idempotent-Replay"

# 缓存键前缀（cache 层会再拼全局前缀）
_CACHE_PREFIX = "idem:"

# 参与缓存的最大响应体（1MB）。超过则只透传不缓存。
_MAX_CACHE_BODY_BYTES = 1024 * 1024


def _normalize_key(raw: Optional[str]) -> Optional[str]:
    """校验并归一化幂等键；非法返回 None（按普通请求处理）"""
    if not raw:
        return None
    key = raw.strip()
    if not key or len(key) > IDEMPOTENCY_MAX_KEY_LENGTH:
        return None
    if not all(ch in IDEMPOTENCY_SAFE_CHARS for ch in key):
        return None
    return key


def _current_user_from_scope(scope: dict):
    """从 ASGI scope 取当前用户（认证中间件已写入）"""
    state = scope.get("state") or {}
    return state.get("current_user")


def _scope_of(request: Request) -> str:
    """获取幂等作用域（用户维度）

    已登录请求用 user_id 隔离，避免不同用户使用相同 key 时互相回放。
    匿名请求共用 ``anon``，因此幂等键主要适用于已登录接口。
    """
    current_user = getattr(request.state, "current_user", None)
    user_id = getattr(current_user, "user_id", None)
    return f"u{user_id}" if user_id else "anon"


def _build_cache_key(user_scope: str, key: str) -> str:
    """构造完整缓存键"""
    return f"{_CACHE_PREFIX}{user_scope}:{key}"


async def _load_replay(cache_key: str, scope: dict, receive, send) -> bool:
    """尝试回放缓存响应

    Returns:
        bool: True 表示已发送回放响应，调用方应立即返回；False 表示未命中
    """
    from core.cache import get_cache

    try:
        cached = await get_cache(cache_key)
    except Exception as exc:  # noqa: BLE001 - 缓存故障不应影响业务
        logger.warning(f"幂等缓存读取失败，按普通请求处理: {exc}")
        return False

    if not cached:
        return False

    try:
        payload = json.loads(cached) if isinstance(cached, str) else cached
        replay = JSONResponse(
            status_code=int(payload["status"]),
            content=payload["body"],
            headers={REPLAY_HEADER: "true"},
        )
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning(f"幂等缓存内容异常，按普通请求处理: {exc}")
        return False

    await replay(scope, receive, send)
    return True


async def _store_response(
    cache_key: str,
    status_code: int,
    headers: List[Tuple[bytes, bytes]],
    body: bytes,
) -> None:
    """把成功的 JSON 响应写入缓存；任何失败都只告警"""
    from core.cache import set_cache

    content_type = ""
    for name, value in headers:
        if name.lower() == b"content-type":
            content_type = value.decode("latin-1").lower()
            break

    if "application/json" not in content_type:
        return
    if len(body) > _MAX_CACHE_BODY_BYTES:
        logger.debug(f"幂等响应体过大（{len(body)}B），跳过缓存")
        return

    try:
        parsed = json.loads(body)
    except (TypeError, ValueError):
        # 非合法 JSON（如流式中途失败）不缓存
        return

    try:
        await set_cache(
            cache_key,
            json.dumps({"status": status_code, "body": parsed}, ensure_ascii=False),
            ttl=IDEMPOTENCY_TTL,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"幂等结果写入缓存失败（不影响本次响应）: {exc}")


class IdempotencyMiddleware:
    """幂等键中间件（纯 ASGI 实现）

    只对带合法 ``Idempotency-Key`` 头的写请求生效，其余请求零开销透传。

    与函数式版本的关键差别：响应直接透传给客户端，同时旁路收集 body，
    请求结束后再决定是否写入缓存。因此不需要"读完重建 Response"，
    也不会破坏下游压缩的尺寸判断。

    使用方式::

        app.add_middleware(IdempotencyMiddleware)
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not IDEMPOTENCY_ENABLED:
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "")
        if method not in IDEMPOTENCY_METHODS:
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        raw_key = request.headers.get(IDEMPOTENCY_HEADER)
        key = _normalize_key(raw_key)
        if key is None:
            if raw_key:
                logger.warning(
                    f"忽略非法 {IDEMPOTENCY_HEADER}: {raw_key[:32]!r} "
                    f"(仅允许字母数字 -_. 且长度≤{IDEMPOTENCY_MAX_KEY_LENGTH})"
                )
            await self.app(scope, receive, send)
            return

        current_user = _current_user_from_scope(scope)
        user_id = getattr(current_user, "user_id", None)
        cache_key = _build_cache_key(f"u{user_id}" if user_id else "anon", key)

        # 1. 命中缓存：直接回放，不执行下游
        if await _load_replay(cache_key, scope, receive, send):
            return

        # 2. 未命中：透传响应，同时旁路收集 body
        status_code = 0
        response_headers: List[Tuple[bytes, bytes]] = []
        chunks: List[bytes] = []
        too_large = False

        async def send_wrapper(message):
            nonlocal status_code, response_headers, too_large
            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_headers = list(message.get("headers") or [])
            elif message["type"] == "http.response.body":
                if not too_large:
                    chunks.append(message.get("body", b""))
                    if sum(len(c) for c in chunks) > _MAX_CACHE_BODY_BYTES:
                        too_large = True
                        chunks.clear()
            await send(message)

        await self.app(scope, receive, send_wrapper)

        # 3. 请求结束后写缓存（只缓存 2xx）
        if 200 <= status_code < 300 and not too_large and chunks:
            await _store_response(cache_key, status_code, response_headers, b"".join(chunks))


async def _read_body(response: Response) -> Optional[bytes]:
    """读取响应体（函数式版本使用）

    Args:
        response: 下游返回的响应

    Returns:
        Optional[bytes]: 响应体字节；无法读取时返回 None
    """
    body_iterator = getattr(response, "body_iterator", None)
    if body_iterator is None:
        return getattr(response, "body", None)

    chunks = []
    async for chunk in body_iterator:
        chunks.append(chunk if isinstance(chunk, bytes) else str(chunk).encode("utf-8"))
    return b"".join(chunks)


async def idempotency_middleware(request: Request, call_next):
    """[兼容保留] 函数式幂等中间件

    旧代码里的 ``app.middleware("http")(idempotency_middleware)`` 仍然可用，
    但会重新引入 ``BaseHTTPMiddleware`` 的流包装开销。
    新代码请改用 ``app.add_middleware(IdempotencyMiddleware)``。

    Args:
        request: FastAPI 请求对象
        call_next: 下一个中间件或路由处理函数

    Returns:
        Response: 首次执行的响应，或缓存的回放响应
    """
    if not IDEMPOTENCY_ENABLED or request.method not in IDEMPOTENCY_METHODS:
        return await call_next(request)

    raw_key = request.headers.get(IDEMPOTENCY_HEADER)
    key = _normalize_key(raw_key)
    if key is None:
        if raw_key:
            logger.warning(
                f"忽略非法 {IDEMPOTENCY_HEADER}: {raw_key[:32]!r} "
                f"(仅允许字母数字 -_. 且长度≤{IDEMPOTENCY_MAX_KEY_LENGTH})"
            )
        return await call_next(request)

    from core.cache import get_cache, set_cache

    cache_key = _build_cache_key(_scope_of(request), key)

    # 1. 命中缓存：直接回放
    try:
        cached = await get_cache(cache_key)
    except Exception as exc:  # noqa: BLE001 - 缓存故障不应影响业务
        logger.warning(f"幂等缓存读取失败，按普通请求处理: {exc}")
        cached = None

    if cached:
        try:
            payload = json.loads(cached) if isinstance(cached, str) else cached
            return JSONResponse(
                status_code=int(payload["status"]),
                content=payload["body"],
                headers={REPLAY_HEADER: "true"},
            )
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning(f"幂等缓存内容异常，按普通请求处理: {exc}")

    # 2. 未命中：执行并缓存成功的 JSON 响应
    response = await call_next(request)

    if not (200 <= response.status_code < 300):
        return response

    content_type = (response.headers.get("content-type") or "").lower()
    if "application/json" not in content_type:
        return response

    body = await _read_body(response)
    if body is None:
        return response

    # 重建响应：原始 body_iterator 已被消费，必须用读到的内容重新构造。
    # content-length / content-type 交给 Response 重新计算，避免出现重复头。
    safe_headers = {
        name: value
        for name, value in response.headers.items()
        if name.lower() not in ("content-length", "content-type")
    }

    rebuilt = Response(
        content=body,
        status_code=response.status_code,
        headers=safe_headers,
        media_type=response.media_type,
    )

    try:
        await set_cache(
            cache_key,
            json.dumps({"status": response.status_code, "body": json.loads(body)}),
            ttl=IDEMPOTENCY_TTL,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"幂等结果写入缓存失败（不影响本次响应）: {exc}")

    return rebuilt
