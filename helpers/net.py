"""网络相关工具：客户端 IP 解析

为什么需要单独封装：
    应用部署在 Nginx / 负载均衡之后时，``request.client.host`` 拿到的是代理的 IP，
    所有真实用户会被识别成同一个来源。后果是：
    - 限流把全站用户算作一个 IP，正常用户被一起限流；
    - 审计日志无法定位真实来源。

安全前提（重要）：
    ``X-Forwarded-For`` 由客户端可伪造。只有在**确定前面有可信代理**时才应采信，
    因此由 ``TRUST_PROXY`` 开关控制，默认关闭：
    - 直连部署（无反向代理）：保持 ``TRUST_PROXY=false``；
    - Nginx / 云负载均衡后：设置 ``TRUST_PROXY=true``，并在代理层覆盖该头
      （Nginx 用 ``proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;``）。
"""
from typing import Optional

from fastapi import Request

from config.app import APP_CONFIG


def get_client_ip(request: Request) -> str:
    """获取客户端真实 IP

    取值优先级（仅在可信代理模式下采信头部）：
    ``X-Forwarded-For`` 第一段 → ``X-Real-IP`` → 连接对端地址

    Args:
        request: FastAPI 请求对象

    Returns:
        str: 客户端 IP；无法获取时返回 "unknown"
    """
    if APP_CONFIG.get("trust_proxy"):
        forwarded: Optional[str] = request.headers.get("X-Forwarded-For")
        if forwarded:
            # XFF 形如 "client, proxy1, proxy2"，取第一段为原始客户端
            first = forwarded.split(",")[0].strip()
            if first:
                return first

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

    return request.client.host if request.client else "unknown"
