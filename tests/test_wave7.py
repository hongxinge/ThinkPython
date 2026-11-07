"""Wave 7 回归测试：纯 ASGI 中间件与文件分片上传

为什么要专门测「中间件不是 BaseHTTPMiddleware」：

函数式中间件（``app.middleware("http")(fn)``）底层是 ``BaseHTTPMiddleware``，
它把响应包进 anyio 内存流逐块转发。实测一层就多约 110µs/请求（本地合成基准，
纯 ASGI 15.9µs vs Base 125.2µs），而且会让 GZip 失去尺寸判断能力。
这些代价是隐性的——代码能跑、测试能过，只有在压测和流量账单上才显形。
所以用结构断言把它钉死，避免以后有人"顺手"改回函数式写法。
"""

from __future__ import annotations

import asyncio
import io
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# 中间件结构
# ---------------------------------------------------------------------------


def test_no_base_http_middleware_in_stack():
    """中间件栈里不允许出现 BaseHTTPMiddleware

    BaseHTTPMiddleware 会把响应转成流式分块，导致：
    1. 每请求多一次内存拷贝（实测 +110µs）；
    2. GZip 跳过 minimum_size 判断，小响应被压大。

    新增中间件时请实现 ``__call__(scope, receive, send)``。
    """
    from starlette.middleware.base import BaseHTTPMiddleware

    from main import create_app

    app = create_app()
    offenders = [
        m.cls.__name__
        for m in app.user_middleware
        if isinstance(m.cls, type) and issubclass(m.cls, BaseHTTPMiddleware)
    ]

    assert offenders == [], f"以下中间件仍在使用 BaseHTTPMiddleware: {offenders}"


def test_gzip_is_outermost_middleware():
    """压缩必须是最外层，才能覆盖中间件自身产生的 401/429 响应

    注意索引方向：Starlette 的 ``add_middleware`` 用 ``insert(0, ...)``，
    而构建时按 ``reversed`` 包装，两者叠加的结果是
    **``user_middleware`` 索引越小越靠外**——第一项是最外层。
    """
    from starlette.middleware.gzip import GZipMiddleware

    from main import create_app

    app = create_app()
    assert app.user_middleware, "中间件栈为空"
    assert app.user_middleware[0].cls is GZipMiddleware


def test_expected_middleware_order():
    """固定从外到内的顺序：GZip -> 日志 -> CORS -> 限流 -> 认证 -> 幂等

    顺序错了会出现具体故障，不是审美问题：

    - CORS 在认证内层 → 预检请求被 401 拦截，浏览器拿不到 CORS 头；
    - 限流在认证内层 → 登录接口不受限流保护，暴力破解无约束；
    - 幂等在认证外层 → 认证失败也写缓存，且读不到 user_id。

    限流默认关闭，未启用时不参与顺序断言。
    """
    from main import create_app

    app = create_app()
    names = [m.cls.__name__ for m in app.user_middleware]

    def index_of(fragment: str):
        for i, name in enumerate(names):
            if fragment in name:
                return i
        return None

    gzip_i = index_of("GZip")
    log_i = index_of("RequestLog")
    cors_i = index_of("CORS")
    auth_i = index_of("Auth")
    idem_i = index_of("Idempotency")
    rate_i = index_of("RateLimit")

    assert None not in (gzip_i, log_i, cors_i, auth_i, idem_i), names

    # 索引越小越靠外
    assert gzip_i < log_i < cors_i, names
    assert cors_i < auth_i < idem_i, names
    if rate_i is not None:
        assert cors_i < rate_i < auth_i, names


def test_auth_middleware_short_circuits_without_calling_app():
    """认证拒绝时必须短路，不把请求交给下游

    这验证 ASGI 实现的早退语义：返回 401 后直接发响应，
    下游路由（以及数据库）不应被触碰。
    """
    from core.auth_middleware import AuthMiddleware

    called = {"downstream": False}

    async def downstream(scope, receive, send):
        called["downstream"] = True

    middleware = AuthMiddleware(downstream)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/auth/profile",
        "raw_path": b"/api/auth/profile",
        "query_string": b"",
        "root_path": "",
        "headers": [(b"host", b"test")],
        "client": ("1.1.1.1", 1234),
        "server": ("test", 80),
        "scheme": "http",
        "http_version": "1.1",
        "app": None,
        "state": {},
    }

    messages = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    # 构造一个带路由表的假 app，供认证中间件做白名单匹配
    from main import create_app

    scope["app"] = create_app()

    asyncio.run(middleware(scope, receive, send))

    assert called["downstream"] is False, "认证失败后不应调用下游"
    start = next(m for m in messages if m["type"] == "http.response.start")
    assert start["status"] == 401


# ---------------------------------------------------------------------------
# 分片上传
# ---------------------------------------------------------------------------

_CHUNKED_DEMO = '''
import hashlib
import os

from fastapi.testclient import TestClient

from core import database as dbm
from core.database import Base
from main import app
from utils.file import FileUtil

FileUtil.DEFAULT_UPLOAD_DIR = os.environ["PROBE_UPLOAD_DIR"]


async def create_tables():
    async with dbm.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


payload = os.urandom(1024 * 1024)
expected = hashlib.sha256(payload).hexdigest()

with TestClient(app) as client:
    client.portal.call(create_tables)

    client.post(
        "/api/auth/register",
        json={"username": "chunk_user", "password": "Passw0rd!", "email": "c@example.com"},
    )
    token = client.post(
        "/api/auth/login", json={"username": "chunk_user", "password": "Passw0rd!"}
    ).json()["data"]["access_token"]
    auth = {"Authorization": "Bearer " + token}

    init = client.post(
        "/api/util/file/chunked/init",
        json={
            "filename": "big.bin",
            "total_size": len(payload),
            "chunk_size": 400 * 1024,
            "category": "files",
        },
        headers=auth,
    )
    info = init.json()["data"]
    upload_id = info["upload_id"]
    cs = info["chunk_size"]
    print("init", init.status_code, info["total_chunks"])

    # 乱序上传：模拟分片并发/重排到达
    for i in (2, 0, 1):
        resp = client.post(
            "/api/util/file/chunked/chunk",
            params={"upload_id": upload_id, "index": i},
            files={"file": ("p", payload[i * cs : (i + 1) * cs], "application/octet-stream")},
            headers=auth,
        )
        print("chunk", i, resp.status_code)

    # 重传同一分片必须幂等
    again = client.post(
        "/api/util/file/chunked/chunk",
        params={"upload_id": upload_id, "index": 0},
        files={"file": ("p", payload[0:cs], "application/octet-stream")},
        headers=auth,
    )
    print("replay_count", again.json()["data"]["received_count"])

    status = client.get(
        "/api/util/file/chunked/status", params={"upload_id": upload_id}, headers=auth
    ).json()["data"]
    print("missing", status["missing"])

    done = client.post(
        "/api/util/file/chunked/complete", params={"upload_id": upload_id}, headers=auth
    )
    result = done.json()["data"]
    actual = hashlib.sha256(open(result["absolute_path"], "rb").read()).hexdigest()
    print("completed", done.status_code, result["file_size"], actual == expected)
    print("url", result["url"])

    # 合并后会话必须销毁
    print("after_status", client.get(
        "/api/util/file/chunked/status", params={"upload_id": upload_id}, headers=auth
    ).status_code)

    # 超大分片应被拒绝
    huge_id = client.post(
        "/api/util/file/chunked/init",
        json={"filename": "x.bin", "total_size": 1000, "chunk_size": 1000},
        headers=auth,
    ).json()["data"]["upload_id"]
    print("oversize", client.post(
        "/api/util/file/chunked/chunk",
        params={"upload_id": huge_id, "index": 0},
        files={"file": ("p", b"x" * 5000)},
        headers=auth,
    ).status_code)

    # 缺分片合并应被拒绝且不产生文件
    partial_id = client.post(
        "/api/util/file/chunked/init",
        json={"filename": "y.bin", "total_size": 2000, "chunk_size": 1000},
        headers=auth,
    ).json()["data"]["upload_id"]
    client.post(
        "/api/util/file/chunked/chunk",
        params={"upload_id": partial_id, "index": 0},
        files={"file": ("p", b"a" * 1000)},
        headers=auth,
    )
    print("incomplete", client.post(
        "/api/util/file/chunked/complete", params={"upload_id": partial_id}, headers=auth
    ).status_code)

    # 非法 upload_id 不得触发路径穿越
    print("traversal", client.get(
        "/api/util/file/chunked/status", params={"upload_id": "../../etc"}, headers=auth
    ).status_code)

    # 取消后磁盘不留残片
    abort_id = client.post(
        "/api/util/file/chunked/init",
        json={"filename": "z.bin", "total_size": 1000, "chunk_size": 500},
        headers=auth,
    ).json()["data"]["upload_id"]
    client.post(
        "/api/util/file/chunked/chunk",
        params={"upload_id": abort_id, "index": 0},
        files={"file": ("p", b"z" * 500)},
        headers=auth,
    )
    print("abort", client.delete(f"/api/util/file/chunked/{abort_id}", headers=auth).status_code)
    session_dir = FileUtil.get_upload_root() / ".chunks" / abort_id
    print("abort_cleaned", not session_dir.exists())
'''


def _run_chunked_demo(tmp_path):
    """在子进程里跑分片上传全流程，避免污染本进程的全局上传目录"""
    upload_dir = tmp_path / "uploads"
    env = {
        "DATABASE_URL": f"sqlite+aiosqlite:///{(tmp_path / 'chunk.db').as_posix()}",
        "CACHE_TYPE": "memory",
        "PROBE_UPLOAD_DIR": str(upload_dir),
        "PYTHONIOENCODING": "utf-8",
    }
    result = subprocess.run(
        [sys.executable, "-c", _CHUNKED_DEMO],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**__import__("os").environ, **env},
    )
    output = (result.stdout or "") + (result.stderr or "")
    return result, output


def test_chunked_upload_end_to_end(tmp_path):
    """分片上传：乱序、重传幂等、合并内容一致、会话销毁、URL 正确"""
    result, output = _run_chunked_demo(tmp_path)

    assert result.returncode == 0, output
    assert "init 200 3" in output, output
    # 三个分片都成功（按行首匹配，避免匹配到日志里的 URL 片段）
    chunk_lines = [line for line in output.splitlines() if line.startswith("chunk ")]
    assert len(chunk_lines) == 3, chunk_lines
    for index in (0, 1, 2):
        assert f"chunk {index} 200" in chunk_lines, chunk_lines
    # 重复上传同一分片不应重复计数
    assert "replay_count 3" in output, output
    # 全部到齐
    assert "missing []" in output, output
    # 合并成功且内容逐字节一致
    assert "completed 200 1048576 True" in output, output
    # 合并后会话销毁，避免残留分片
    assert "after_status 404" in output, output

    # URL 必须是对外逻辑路径，不能暴露服务器磁盘路径
    url_line = next(line for line in output.splitlines() if line.startswith("url "))
    assert url_line.startswith("url /uploads/files/"), url_line
    assert ":\\" not in url_line and "C:/" not in url_line


def test_chunked_upload_rejects_invalid_input(tmp_path):
    """分片上传的边界：超大分片、缺片合并、路径穿越、取消清理"""
    result, output = _run_chunked_demo(tmp_path)

    assert result.returncode == 0, output
    assert "oversize 400" in output, output          # 分片超过预期大小
    assert "incomplete 400" in output, output        # 分片未齐不能合并
    assert "traversal 404" in output, output         # 非法 upload_id 不触发路径穿越
    assert "abort 200" in output, output             # 取消成功
    assert "abort_cleaned True" in output, output    # 取消后磁盘无残留
