"""请求上下文（contextvars）

客户端 API 排障的核心诉求是「一次请求的所有信息能串起来」。HTTP 是无状态的，
因此需要把 request_id 放进上下文变量，让日志、异常处理器、响应体都能拿到它，
而不必层层传参。

设计要点：
- 只依赖标准库，避免与 core.exception / middleware 形成循环导入；
- 使用 ``ContextVar`` 而非全局变量：asyncio 下每个请求任务有独立上下文，
  并发请求之间不会互相覆盖；
- 提供 ``bind_request_id`` 上下文管理器，确保请求结束后自动清理。

使用方式::

    from core.context import bind_request_id, get_request_id

    with bind_request_id("abc-123"):
        logger.info(f"request_id={get_request_id()}")
"""
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator, Optional

# 当前请求的追踪 ID；空字符串表示不在请求上下文中（如 CLI、迁移脚本）
_request_id: ContextVar[str] = ContextVar("request_id", default="")

# 当前请求的客户端 IP（限流、审计日志使用）
_client_ip: ContextVar[str] = ContextVar("client_ip", default="")


def set_request_id(request_id: str) -> None:
    """设置当前上下文的 request_id"""
    _request_id.set(request_id or "")


def get_request_id() -> str:
    """获取当前上下文的 request_id，无则返回空字符串"""
    return _request_id.get()


def set_client_ip(ip: str) -> None:
    """设置当前上下文的客户端 IP"""
    _client_ip.set(ip or "")


def get_client_ip() -> str:
    """获取当前上下文的客户端 IP，无则返回空字符串"""
    return _client_ip.get()


@contextmanager
def bind_request_id(request_id: str, client_ip: Optional[str] = None) -> Iterator[str]:
    """在 with 块内绑定 request_id（以及可选的客户端 IP），退出时自动还原

    Args:
        request_id: 请求追踪 ID
        client_ip: 客户端 IP，可选

    Yields:
        str: 实际绑定的 request_id
    """
    token = _request_id.set(request_id or "")
    ip_token = _client_ip.set(client_ip or "")
    try:
        yield request_id or ""
    finally:
        _request_id.reset(token)
        _client_ip.reset(ip_token)
