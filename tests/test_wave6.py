"""Wave 6 回归测试：契约导出、SDK 生成、压缩与 SQLite 加固

这些用例守护的是「开发者接入体验」这条链路，回归时最容易断的几个点：

1. OpenAPI 导出不能依赖 HTTP 端点（生产关掉 schema 也要能生成 SDK）；
2. 契约体检要能识别「响应类型退化」，否则 SDK 类型悄悄变成 unknown 也没人发现；
3. SDK 必须把服务端 ``ApiResponse[T]`` 的 ``data`` 抽出来，不能生成双层包装；
4. 压缩必须遵守尺寸门限——小响应被压缩反而变大，是探活接口的高频浪费；
5. SQLite 的 PRAGMA 必须真正下发，尤其外键默认是关闭的。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# OpenAPI 导出与体检
# ---------------------------------------------------------------------------


def test_openapi_export_writes_valid_json(tmp_path):
    """导出的 JSON 可被解析，且包含全部已注册路由"""
    import json

    from core.openapi_export import export_schema

    target = tmp_path / "nested" / "openapi.json"
    path, size = export_schema(target)

    assert path.exists()
    assert size > 0

    schema = json.loads(path.read_text(encoding="utf-8"))
    assert schema["openapi"].startswith("3.")
    # 核心接口必须出现，否则说明路由注册在导出时丢失
    assert "/api/auth/login" in schema["paths"]
    assert "/api/auth/refresh" in schema["paths"]


def test_contract_report_detects_loose_response():
    """体检能识别 response_model=dict 造成的类型退化"""
    from core.openapi_export import inspect_schema

    report = inspect_schema()

    assert report["total_operations"] > 0
    # 本仓库仍有接口未声明精确模型，体检必须如实报告而不是给个漂亮分数
    assert report["counts"]["loose_response"] >= 1
    codes = {issue["code"] for issue in report["issues"]}
    assert "LOOSE_RESPONSE" in codes


def test_wrapper_models_are_recognized():
    """ApiResponse[T] 生成后能被识别为响应包装，避免 SDK 双层泛型"""
    from core.openapi_export import build_schema
    from core.sdkgen import is_response_wrapper, wrapper_schema_names

    schema = build_schema()
    components = schema["components"]["schemas"]

    names = wrapper_schema_names(schema)
    # 声明了 ApiResponse[X] 的接口会生成 ApiResponse_Xxx_ 扁平模型
    assert any(name.startswith("ApiResponse_") for name in names)

    for name in names:
        assert is_response_wrapper(components[name], components)


# ---------------------------------------------------------------------------
# SDK 生成
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def generated_sdk(tmp_path_factory):
    """生成一次 SDK，供同模块多个用例复用（生成开销不大但没必要重复）"""
    from core.openapi_export import build_schema, inspect_schema
    from core.sdkgen import generate

    out = tmp_path_factory.mktemp("sdk")
    schema = build_schema()
    report = inspect_schema(schema)
    result = generate(out, schema=schema, base_url_hint="https://api.example.com", report=report)
    return out, result


def test_sdk_generates_expected_files(generated_sdk):
    out, result = generated_sdk

    for name in ("src/types.ts", "src/client.ts", "src/api.ts", "src/index.ts", "README.md", "tsconfig.json", "package.json"):
        assert (out / name).exists(), f"缺少 {name}"

    assert result["operations"] > 0
    assert len(result["files"]) == 7


def test_sdk_unwraps_response_data_type(generated_sdk):
    """登录接口必须生成 ApiResponse<LoginData>，而不是 unknown 或双层包装"""
    out, _ = generated_sdk
    api = (out / "src" / "api.ts").read_text(encoding="utf-8")

    assert "postApiAuthLogin" in api
    assert "Promise<ApiResponse<LoginData>>" in api
    # 双层包装是最容易犯的错，显式排除
    assert "ApiResponse<ApiResponse" not in api
    # 包装模型不应作为独立接口导出
    types = (out / "src" / "types.ts").read_text(encoding="utf-8")
    assert "interface ApiResponse_LoginData_" not in types


def test_sdk_client_has_essential_capabilities(generated_sdk):
    """客户端必须内置刷新、幂等、追踪能力，否则等于没生成"""
    out, _ = generated_sdk
    client = (out / "src" / "client.ts").read_text(encoding="utf-8")

    assert "Idempotency-Key" in client
    assert "X-Request-ID" in client
    assert "ensureRefreshed" in client          # 并发刷新串行化
    assert "TOKEN_EXPIRED" in client            # 1004 自动刷新重放
    assert "needsRelogin" in client             # 1005 等需要重新登录
    assert "class NetworkError" in client       # 网络错误与业务错误分离


def test_sdk_output_braces_balanced(generated_sdk):
    """轻量语法护栏：括号与引号不配对是最常见的生成器回归

    这里不做完整 TS 解析（CI 未必装 Node），只保证结构性错误能被抓住。
    """
    out, _ = generated_sdk

    for name in ("src/types.ts", "src/client.ts", "src/api.ts", "src/index.ts"):
        text = (out / name).read_text(encoding="utf-8")
        assert text.count("{") == text.count("}"), f"{name} 花括号不配对"
        assert text.count("(") == text.count(")"), f"{name} 圆括号不配对"
        assert text.count("[") == text.count("]"), f"{name} 方括号不配对"


def test_sdk_package_declares_build_scripts(generated_sdk):
    """生成的 package.json 要能直接 npm run typecheck"""
    import json

    out, _ = generated_sdk
    pkg = json.loads((out / "package.json").read_text(encoding="utf-8"))

    assert "build" in pkg["scripts"]
    assert "typecheck" in pkg["scripts"]
    assert "typescript" in pkg["devDependencies"]


# ---------------------------------------------------------------------------
# 响应压缩
# ---------------------------------------------------------------------------


def test_gzip_skips_small_response():
    """小于门限的响应不压缩——压缩后反而更大，探活接口每次都在浪费流量"""
    from fastapi.testclient import TestClient

    from main import create_app

    app = create_app()
    with TestClient(app) as client:
        with client.stream("GET", "/health", headers={"Accept-Encoding": "gzip"}) as response:
            raw = b"".join(response.iter_raw())
            encoding = response.headers.get("content-encoding")
        plain = client.get("/health").content

    assert encoding is None, "小响应不应被压缩"
    assert len(raw) == len(plain)


def test_gzip_compresses_large_response():
    """大 JSON 必须被压缩，且压缩率显著"""
    from fastapi.testclient import TestClient

    from main import create_app

    app = create_app()
    with TestClient(app) as client:
        with client.stream("GET", "/openapi.json", headers={"Accept-Encoding": "gzip"}) as response:
            raw = b"".join(response.iter_raw())
            encoding = response.headers.get("content-encoding")
        plain = client.get("/openapi.json").content

    assert encoding == "gzip"
    assert len(raw) < len(plain) * 0.5, "大 JSON 压缩率应超过 50%"


# ---------------------------------------------------------------------------
# SQLite 加固
# ---------------------------------------------------------------------------


def test_sqlite_pragmas_applied(tmp_path):
    """文件库必须启用 WAL / 外键 / NORMAL 同步 / busy_timeout

    SQLite 的外键约束默认是**关闭**的，不显式打开则约束形同虚设。
    用子进程验证，避免污染本进程的全局 engine。
    """
    db_file = tmp_path / "pragma.db"
    env = {
        "DATABASE_URL": f"sqlite+aiosqlite:///{db_file.as_posix()}",
        "CACHE_TYPE": "memory",
        "PYTHONIOENCODING": "utf-8",
    }

    code = """
import asyncio
import core.database as db
from sqlalchemy import text

async def main():
    await db.init_database()
    async with db.engine.connect() as conn:
        for name in ("journal_mode", "foreign_keys", "synchronous", "busy_timeout"):
            value = (await conn.execute(text("PRAGMA " + name))).scalar()
            print(name, value)
    await db.close_database()

asyncio.run(main())
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**__import__("os").environ, **env},
    )
    output = (result.stdout or "") + (result.stderr or "")

    assert "journal_mode wal" in output, output
    assert "foreign_keys 1" in output, output
    assert "synchronous 1" in output, output
    assert "busy_timeout 5000" in output, output


def test_openapi_stdout_is_pure_json():
    """`openapi --stdout` 的 stdout 必须是纯 JSON

    这条守着 CLI 的管道能力：日志如果走 stdout，`| jq`、`> openapi.json`
    都会混入日志行导致解析失败。日志应走 stderr（Unix 惯例）。
    """
    import json

    result = subprocess.run(
        [sys.executable, "think.py", "openapi", "--stdout"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert result.returncode == 0
    schema = json.loads(result.stdout)          # 混入任何日志行都会在此失败
    assert "paths" in schema
    assert "/api/auth/login" in schema["paths"]


def test_console_logs_go_to_stderr():
    """控制台日志输出到 stderr，stdout 留给数据"""
    code = """
import sys
from core.logger import setup_logging
setup_logging("INFO")
from loguru import logger
logger.info("stdout-probe")
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert "stdout-probe" not in result.stdout
    assert "stdout-probe" in result.stderr
