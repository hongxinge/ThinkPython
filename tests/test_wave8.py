"""Wave 8 回归：客户端契约收敛、分片并发合并、慢 SQL 可观测

三项改动均按 ADR D0 的五项一致性判据自检通过：
- 精确响应模型：收益直接落在客户端 SDK 的请求链路；
- complete 互斥锁：弱网重试场景，避免重复合并；
- 慢 SQL 日志：接口性能可观测，附带 request_id 便于排障。

Excel 导入导出属管理端示例能力，按 D0 不纳入核心契约演进，故本轮不为其
声明 ApiResponse；文件下载/预览与 health 探针返回非 JSON 载荷，同样不套包装。
"""
import os
import threading
import time
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from core.database import install_slow_query_logging
from utils.chunked_upload import ChunkedUploadError, ChunkedUploadManager
from utils.file import FileUtil

_UPLOAD_ID = "a" * 32


@pytest.fixture
def isolated_chunks(tmp_path, monkeypatch):
    """把分片根目录与上传目标目录都指向 tmp_path，避免污染仓库 uploads/"""
    chunk_root = tmp_path / "chunks"
    upload_root = tmp_path / "uploads"
    chunk_root.mkdir()
    upload_root.mkdir()
    monkeypatch.setattr(ChunkedUploadManager, "_chunk_root", staticmethod(lambda: chunk_root))
    monkeypatch.setattr(FileUtil, "get_upload_root", classmethod(lambda cls: upload_root))
    return chunk_root, upload_root


# ==================================================================
# 一、complete 跨进程互斥锁
# ==================================================================

def test_complete_lock_is_exclusive_and_released(isolated_chunks):
    """同一 upload_id 的锁互斥；释放后可再次获取，锁目录不残留"""
    chunk_root, _ = isolated_chunks

    with ChunkedUploadManager._complete_lock(_UPLOAD_ID):
        with pytest.raises(ChunkedUploadError, match="正在合并"):
            with ChunkedUploadManager._complete_lock(_UPLOAD_ID):
                pass

    # 正常释放后可重入（会话重试 / 后续任务不受影响）
    with ChunkedUploadManager._complete_lock(_UPLOAD_ID):
        pass
    assert not (chunk_root / ".locks" / f"{_UPLOAD_ID}.lock").exists()


def test_stale_complete_lock_is_reclaimed(isolated_chunks):
    """进程崩溃留下的陈旧锁超过 TTL 后可被清理，不会永久死锁"""
    chunk_root, _ = isolated_chunks
    lock = chunk_root / ".locks" / f"{_UPLOAD_ID}.lock"
    lock.mkdir(parents=True)
    old = time.time() - 400
    os.utime(lock, (old, old))

    with ChunkedUploadManager._complete_lock(_UPLOAD_ID):
        pass
    assert not lock.exists()


def test_cleanup_expired_never_removes_lock_dir(isolated_chunks):
    """过期会话清理不能把 .locks 当成残留会话删掉"""
    chunk_root, _ = isolated_chunks
    lock_dir = chunk_root / ".locks"
    lock_dir.mkdir(exist_ok=True)
    old = time.time() - 200000
    os.utime(lock_dir, (old, old))

    ChunkedUploadManager._cleanup_expired()
    assert lock_dir.exists()


def test_concurrent_complete_merges_only_once(isolated_chunks):
    """两个线程同时 complete：恰好一个成功，另一个收到业务异常"""
    meta = ChunkedUploadManager.init("demo.bin", total_size=4, chunk_size=2)
    upload_id = meta["upload_id"]
    session = ChunkedUploadManager._session_dir(upload_id)
    (session / "0.part").write_bytes(b"ab")
    (session / "1.part").write_bytes(b"cd")

    barrier = threading.Barrier(2)

    def worker():
        barrier.wait()
        try:
            return ("ok", ChunkedUploadManager.complete(upload_id))
        except ChunkedUploadError as exc:
            return ("err", str(exc))

    results = []
    threads = [threading.Thread(target=lambda: results.append(worker())) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert len(results) == 2
    successes = [r for r in results if r[0] == "ok"]
    assert len(successes) == 1, results
    assert successes[0][1]["file_size"] == 4
    assert len([r for r in results if r[0] == "err"]) == 1


# ==================================================================
# 二、慢 SQL 日志
# ==================================================================

def test_slow_sql_is_logged_without_parameters():
    """超过阈值时记录耗时、request_id 与 SQL，但不打印参数值"""
    logs = []
    engine = create_engine("sqlite://")
    install_slow_query_logging(engine, threshold_ms=0.000001, sink=logs.append)
    with engine.connect() as conn:
        conn.execute(text("SELECT :secret AS n"), {"secret": 424242})

    assert len(logs) == 1, logs
    line = logs[0]
    assert "slow_sql" in line
    assert "ms" in line
    assert "request_id=" in line
    # SQLAlchemy 已把 :secret 编译为占位符，日志里只留语句骨架
    assert "SELECT ? AS n" in line
    assert "424242" not in line  # 参数值不得进入日志
    engine.dispose()


def test_slow_sql_disabled_by_zero():
    """阈值 0 表示关闭监听，不产生任何日志与额外开销"""
    logs = []
    engine = create_engine("sqlite://")
    install_slow_query_logging(engine, threshold_ms=0, sink=logs.append)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    assert logs == []
    engine.dispose()


def test_slow_sql_logging_supports_async_engine():
    """生产路径：异步引擎的 sync_engine 事件在 greenlet 上下文中也能触发"""
    import asyncio

    from sqlalchemy.ext.asyncio import create_async_engine

    logs = []

    async def run():
        # 引擎在协程内创建，避免跨事件循环绑定
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        install_slow_query_logging(engine, threshold_ms=0.000001, sink=logs.append)
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        finally:
            await engine.dispose()

    asyncio.run(run())
    assert any("slow_sql" in line for line in logs), logs


# ==================================================================
# 三、客户端响应契约（OpenAPI 精确度）
# ==================================================================

def _success_ref(spec, path, method):
    op = spec["paths"][path][method]
    return op["responses"]["200"]["content"]["application/json"]["schema"].get("$ref", "")


def test_client_endpoints_have_typed_response_models():
    """客户端会调用的业务接口必须产出精确响应模型，而非 unknown"""
    from main import app

    spec = app.openapi()
    targets = [
        ("/api/auth/login", "post"),
        ("/api/auth/refresh", "post"),
        ("/api/auth/register", "post"),
        ("/api/auth/profile", "get"),
        ("/api/auth/profile", "put"),
        ("/api/auth/change-password", "post"),
        ("/api/auth/forgot-password", "post"),
        ("/api/product/list", "get"),
        ("/api/product/{product_id}", "get"),
        ("/api/util/file/upload", "post"),
        ("/api/util/file/upload-multiple", "post"),
        ("/api/util/file/info", "get"),
        ("/api/util/file/delete", "delete"),
        ("/api/util/file/chunked/complete", "post"),
    ]
    for path, method in targets:
        assert "ApiResponse" in _success_ref(spec, path, method), (path, method)

    precise = sum(
        1
        for ops in spec["paths"].values()
        for op in ops.values()
        if "ApiResponse" in op.get("responses", {})
        .get("200", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema", {})
        .get("$ref", "")
    )
    assert precise >= 23, precise


def test_profile_and_product_schema_fields_are_complete():
    """模型字段必须与 self.success(data=...) 一致，避免响应字段被过滤"""
    from main import app

    schemas = app.openapi()["components"]["schemas"]
    assert {"user_id", "username", "email", "nickname", "status", "created_at"} <= set(
        schemas["ProfileData"]["properties"]
    )
    assert {"items", "total"} <= set(schemas["ProductListData"]["properties"])
    assert {"id", "name"} <= set(schemas["ProductData"]["properties"])
    assert {"total", "success", "failed", "files"} <= set(
        schemas["MultiUploadData"]["properties"]
    )
