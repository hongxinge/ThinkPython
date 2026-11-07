"""幂等键中间件

作用：
    让客户端可以安全重试写请求。客户端为一次业务操作生成 ``Idempotency-Key``，
    服务端缓存首次成功的响应；相同 key 再次到达时直接回放，不重复执行。

执行位置（重要）：
    本中间件必须注册在**认证中间件之后**（即更内层），原因：
    1. 需要读取 ``request.state.current_user`` 做用户维度隔离；
    2. 认证失败的请求不应写入幂等缓存。

响应约定：
    回放的响应带 ``Idempotent-Replay: true`` 头，客户端可据此判断这是缓存结果。

安全与边界：
    - key 只接受字母、数字、``-``、``_``、``.``，长度 ≤128，非法则忽略（按普通请求处理）；
    - 只缓存 2xx 且 Content-Type 为 JSON 的响应，避免把错误或文件流固化；
    - 缓存不可用时退化为普通请求，不影响可用性。
"""
import json
from typing import Optional

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


def _scope_of(request: Request) -> str:
    """获取幂等作用域（用户维度）

    已登录请求用 user_id 隔离，避免不同用户使用相同 key 时互相回放。
    匿名请求共用 ``anon``，因此幂等键主要适用于已登录接口。
    """
    current_user = getattr(request.state, "current_user", None)
    user_id = getattr(current_user, "user_id", None)
    return f"u{user_id}" if user_id else "anon"


async def _read_body(response: Response) -> Optional[bytes]:
    """读取响应体（仅在需要缓存时调用）

    Starlette 的响应体是字节流迭代器，读完后需要重新构造响应才能返回给客户端。

    Args:
        response: 下游返回的响应

    Returns:
        Optional[bytes]: 响应体字节；无法读取时返回 None
    """
    body_iterator = getattr(response, "body_iterator", None)
    if body_iterator is None:
        # 普通 Response 直接有 body 属性
        return getattr(response, "body", None)

    chunks = []
    async for chunk in body_iterator:
        chunks.append(chunk if isinstance(chunk, bytes) else str(chunk).encode("utf-8"))
    return b"".join(chunks)


async def idempotency_middleware(request: Request, call_next):
    """幂等键中间件

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

    cache_key = f"{_CACHE_PREFIX}{_scope_of(request)}:{key}"

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
        # 文件下载等非 JSON 响应不缓存
        return response

    body = await _read_body(response)
    if body is None:
        return response

    # 重建响应：原始 body_iterator 已被消费，必须用读到的内容重新构造。
    # content-length / content-type 交给 Response 重新计算，避免出现重复头
    # （dict(response.headers) 已包含旧值，直接透传会产生两个 content-length）。
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
