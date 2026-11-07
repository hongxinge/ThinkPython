"""Wave 0 回归测试：已人工复现的缺陷（RED 集合）。

约定：
1. 每个用例对应一处已确认缺陷，当前状态下**预期失败**，统一用
   ``@pytest.mark.xfail(strict=True)`` 标记；
2. 缺陷修复后用例会自动转为 XPASS，pytest 判定为失败，强制开发者移除
   xfail 标记，形成"修好即解锁"的门禁，避免缺陷被悄悄重新引入；
3. 所有用例只依赖内存资源或源码文本，不连接 MySQL / Redis。

对应缺陷的复现证据见 `.workbuddy/memory/2026-11-07.md`。
"""
import asyncio
import os
import subprocess
import sys

import pytest

pytestmark = pytest.mark.regression

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run_python(code: str) -> subprocess.CompletedProcess:
    """在独立子进程中执行代码，避免污染当前进程的 SQLAlchemy 元数据。"""
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


# ============== P0 安全 ==============

def test_default_jwt_secret_not_in_use():
    """已修复：.env 已配置强随机密钥，本用例保留为回归防线。"""
    from config.auth import USING_DEFAULT_JWT_SECRET

    assert USING_DEFAULT_JWT_SECRET is False


def test_production_startup_rejects_default_secret():
    """生产模式（debug=False）下使用默认密钥必须拒绝启动。"""
    from config.auth import validate_secret_config

    with pytest.raises(RuntimeError):
        validate_secret_config(using_default=True, debug=False)

    # debug 模式只告警，不阻塞本地开发；已配置强密钥时无需告警
    assert validate_secret_config(using_default=True, debug=True) is True
    assert validate_secret_config(using_default=False, debug=False) is False


def test_refresh_token_cannot_be_used_as_access_token():
    """已修复：decode_token 默认只接受 type=access，本用例保留为回归防线。"""
    from helpers.auth import create_refresh_token, decode_token

    assert decode_token(create_refresh_token(1)) is None


def test_global_whitelist_requires_path_boundary():
    """已修复：白名单前缀必须带路径段边界，本用例保留为回归防线。"""
    from core.auth_middleware import _is_in_global_whitelist

    assert _is_in_global_whitelist("/docs-evil") is False


def test_file_info_rejects_path_outside_uploads():
    """已修复：文件接口只允许访问上传根目录内的文件，本用例保留为回归防线。"""
    import time

    import jwt
    from httpx import ASGITransport, AsyncClient

    from config.auth import JWT_ALGORITHM, JWT_SECRET
    from main import app

    # 使用当前配置的密钥签发合法 token，使断言聚焦于"路径归属校验"而非认证
    token = jwt.encode(
        {"user_id": 1, "username": "regression", "type": "access", "exp": int(time.time()) + 3600},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )

    async def call():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(
                "/api/util/file/info",
                params={"file_path": os.path.join(PROJECT_ROOT, "requirements.txt")},
                headers={"Authorization": f"Bearer {token}"},
            )

    response = asyncio.run(call())
    assert response.status_code != 200


def test_upload_category_cannot_escape_uploads_dir():
    """已修复：上传分类走白名单校验，非法值直接拒绝。"""
    from utils.file import FileUtil

    with pytest.raises(ValueError):
        FileUtil.generate_subdir("../../evil")

    # 合法分类仍应返回规范的日期子目录
    assert FileUtil.generate_subdir("images").startswith("images/")


def test_cors_wildcard_and_credentials_not_combined():
    """已修复：来源为 "*" 时自动关闭 credentials，本用例保留为回归防线。"""
    from config.app import APP_CONFIG

    cors = APP_CONFIG["cors"]
    assert not (cors["allow_origins"] == ["*"] and cors["allow_credentials"])


def test_register_request_requires_email():
    """已修复：注册契约要求 email 必填，与数据库约束对齐。"""
    from app.api.controller.auth_controller import RegisterRequest

    assert RegisterRequest.model_fields["email"].is_required()


# ============== P0 工程闭环 ==============

def test_db_migrate_history_reports_real_failure():
    """已修复：alembic.ini 全 ASCII，GBK 环境下不再解码崩溃。"""
    result = subprocess.run(
        [sys.executable, "think.py", "db-migrate", "--history"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output = (result.stdout or "") + (result.stderr or "")

    assert result.returncode == 0
    assert "gbk" not in output.lower()


def test_db_migrate_failure_exits_non_zero():
    """已修复：迁移失败返回非零退出码，避免 CI/部署脚本把失败当成功。"""
    env = dict(os.environ)
    # 指向不存在的目录，SQLite 无法打开，迁移必定失败
    env["DATABASE_URL"] = "sqlite+aiosqlite:////__nonexistent_thinkpython_dir__/x.db"

    result = subprocess.run(
        [sys.executable, "think.py", "db-migrate", "--upgrade"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )

    assert result.returncode != 0


# ============== P1 功能正确性 ==============

def test_memory_rate_limiter_check_is_awaitable():
    """已修复：内存限流器与 Redis 限流器统一为异步接口。"""
    from middleware.ratelimit import MemoryRateLimiter, RateLimitMiddleware

    middleware = RateLimitMiddleware.__new__(RateLimitMiddleware)
    middleware.limiter = MemoryRateLimiter()

    assert asyncio.run(middleware._check("regression-key", 1.0, 10)) is True


def test_paginate_handles_zero_page_size():
    """已修复：分页参数会归一化，page_size<=0 不再除零。"""
    from core.base_controller import BaseController

    result = BaseController().paginate([], total=0, page=1, page_size=0)
    assert result["data"]["total_pages"] == 0


def test_user_models_can_coexist():
    """已修复：single 的 User 改为 re-export，全仓库只有一个 user 表映射。"""
    code = (
        "import sys\n"
        f"sys.path.insert(0, {PROJECT_ROOT!r})\n"
        "from app.common.model.user_model import User as A\n"
        "from app.single.model.user_model import User as B\n"
        "print('ok')\n"
    )
    result = _run_python(code)

    assert result.returncode == 0, result.stderr


def test_example_user_service_binds_model_class():
    """已修复：UserService 在类体中声明 model_class，BaseService CRUD 可用。"""
    from app.single.service.user_service import UserService

    assert UserService.model_class is not None


def test_excel_export_rejects_invalid_header_type_explicitly():
    """已修复：write_excel 显式校验类型并抛 TypeError，不再抛 AttributeError。"""
    import tempfile

    from utils.excel import ExcelUtil

    path = os.path.join(tempfile.gettempdir(), "_tp_regression_export.xlsx")
    try:
        with pytest.raises(TypeError):
            ExcelUtil.write_excel(data=[[1, "a"]], headers=["ID", "名称"], output_path=path)
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_app_exception_code_not_used_as_http_status():
    """已修复：业务码与 HTTP 状态码分离，非法业务码回落 500。"""
    from starlette.requests import Request

    from core.exception import AppException, app_exception_handler

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/regression",
        "raw_path": b"/regression",
        "query_string": b"",
        "headers": [],
        "scheme": "http",
        "server": ("test", 80),
        "client": ("test", 123),
        "root_path": "",
    }
    response = asyncio.run(
        app_exception_handler(Request(scope), AppException("回归测试", code=40001))
    )

    assert response.status_code <= 599


def test_controller_does_not_commit_manually():
    """已修复：控制器只 flush，事务提交统一由 get_db 负责。"""
    path = os.path.join(PROJECT_ROOT, "app", "api", "controller", "auth_controller.py")
    with open(path, encoding="utf-8") as file:
        source = file.read()

    assert "await db.commit()" not in source


# ============== 已修复项的正向验证 ==============

def test_password_hash_is_salted_and_verifiable():
    """PBKDF2 哈希：同一密码两次结果不同，且均可正确校验。"""
    from app.common.service.auth_service import AuthService

    service = AuthService.__new__(AuthService)
    first = service.hash_password("s3cret-pass")
    second = service.hash_password("s3cret-pass")

    assert first.startswith("pbkdf2_sha256$")
    assert first != second
    assert service._verify_password("s3cret-pass", first) is True
    assert service._verify_password("wrong-pass", first) is False


def test_legacy_md5_hash_still_verifies():
    """历史 MD5 密码仍可登录，并由 needs_rehash 标记为待升级。"""
    from app.common.service.auth_service import AuthService
    from helpers.common import md5

    service = AuthService.__new__(AuthService)
    legacy = md5("legacy-pass")

    assert service._verify_password("legacy-pass", legacy) is True
    assert service.needs_rehash(legacy) is True
    assert service.needs_rehash(service.hash_password("x")) is False


# ============== 限流规则命中（配置一致性） ==============

def test_login_rate_limit_matches_prefixed_paths():
    """已修复：登录限流规则能命中多模块 / 全局前缀下的真实路径。

    修复前 pattern 写死 /auth/login，真实路径是 /api/auth/login，
    精确匹配失败导致登录限流永不生效（暴力破解无约束）。
    """
    from middleware.ratelimit import RateLimitMiddleware

    middleware = RateLimitMiddleware.__new__(RateLimitMiddleware)
    patterns = ["/auth/login", "/login"]

    assert middleware._path_matches("/api/auth/login", patterns) is True
    assert middleware._path_matches("/api/v1/api/auth/login", patterns) is True
    assert middleware._path_matches("/admin/auth/login/", patterns) is True


def test_rate_limit_path_match_respects_segment_boundary():
    """已修复：限流路径不做无边界的裸字符串匹配。"""
    from middleware.ratelimit import RateLimitMiddleware

    middleware = RateLimitMiddleware.__new__(RateLimitMiddleware)

    assert middleware._path_matches("/auth/login-evil", ["/auth/login"]) is False
    assert middleware._path_matches("/api/util/file/info", ["/auth/login"]) is False
    assert middleware._path_matches("/api/auth/register", ["/auth/login"]) is False


def test_rate_limit_wildcard_pattern_supported():
    """限流规则支持 /api/* 形式的末尾通配。"""
    from middleware.ratelimit import RateLimitMiddleware

    middleware = RateLimitMiddleware.__new__(RateLimitMiddleware)

    assert middleware._path_matches("/api/auth/login", ["/api/*"]) is True
    assert middleware._path_matches("/api", ["/api/*"]) is True
    assert middleware._path_matches("/health", ["/api/*"]) is False


# ============== 客户端契约：错误码与请求追踪 ==============

def test_auth_error_codes_distinguish_expired_from_invalid():
    """已修复：过期与无效返回不同业务码，客户端才能区分「刷新」与「重新登录」。"""
    import time

    import jwt

    from config.auth import JWT_ALGORITHM, JWT_SECRET
    from core.error_codes import ErrorCode
    from helpers.auth import create_token, decode_token_detail

    expired = jwt.encode(
        {"user_id": 1, "type": "access", "exp": int(time.time()) - 10},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    payload, code = decode_token_detail(expired)
    assert payload is None
    assert code == ErrorCode.TOKEN_EXPIRED

    payload, code = decode_token_detail("not-a-jwt")
    assert payload is None
    assert code == ErrorCode.TOKEN_INVALID

    payload, code = decode_token_detail(create_token(1))
    assert payload is not None
    assert code is None


def test_error_response_carries_request_id():
    """错误响应体与响应头都带 request_id，客户端上报问题时可直接引用。"""
    from httpx import ASGITransport, AsyncClient

    from main import app

    async def call():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(
                "/api/util/file/info",
                params={"file_path": "uploads/x.txt"},
                headers={"X-Request-ID": "client-trace-001"},
            )

    response = asyncio.run(call())

    assert response.status_code == 401
    assert response.headers.get("X-Request-ID") == "client-trace-001"
    assert response.json()["request_id"] == "client-trace-001"
    # 未携带 Token 有独立业务码，便于客户端跳转登录
    assert response.json()["code"] == 1001


def test_token_version_invalidates_issued_tokens(tmp_path):
    """已修复：改密（token_version +1）后，旧 Token 立即失效。"""
    db_file = tmp_path / "token_version.db"
    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite+aiosqlite:///{db_file.as_posix()}",
        "CACHE_TYPE": "memory",
        "CACHE_ENABLED": "true",
        # 关闭缓存，保证每次都读数据库，结果确定
        "TOKEN_VERSION_CACHE_TTL": "0",
    }

    code = """
import asyncio

from core import database as db_module
from core.cache import close_cache, init_cache
from core.database import Base, init_database
from core.token_state import bump_token_version, is_token_version_valid
from app.common.model.user_model import User


async def main():
    await init_database()
    await init_cache()
    async with db_module.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with db_module.async_session() as session:
        user = User(username="tv_user", password="x", email="tv@example.com", status=1)
        session.add(user)
        await session.commit()
        user_id = user.id

    print("before", await is_token_version_valid(user_id, 0))

    async with db_module.async_session() as session:
        await bump_token_version(session, user_id)
        await session.commit()

    print("old_token", await is_token_version_valid(user_id, 0))
    print("new_token", await is_token_version_valid(user_id, 1))

    await close_cache()


asyncio.run(main())
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    output = (result.stdout or "") + (result.stderr or "")

    assert "before True" in output, output
    assert "old_token False" in output, output
    assert "new_token True" in output, output


def test_login_failure_lock_threshold():
    """账号连续失败达到阈值后被锁定（抛 423），成功后计数清零。"""
    from app.common.service.auth_service import AuthService
    from core.exception import AccountLockedException

    service = AuthService.__new__(AuthService)

    async def scenario():
        from core.cache import close_cache, delete_cache, init_cache

        await init_cache()
        await delete_cache("login_fail:lock_probe")

        # 失败 4 次不锁
        for _ in range(4):
            await service._record_login_failure("lock_probe")

        # 第 5 次触发锁定
        try:
            await service._record_login_failure("lock_probe")
            return "no-lock"
        except AccountLockedException:
            pass

        # 锁定后再次尝试登录仍应被拦截
        try:
            await service._ensure_not_locked("lock_probe")
            locked = False
        except AccountLockedException:
            locked = True

        # 成功登录清除计数后恢复
        await service._clear_login_failures("lock_probe")
        await service._ensure_not_locked("lock_probe")

        await close_cache()
        return "locked" if locked else "not-locked"

    assert asyncio.run(scenario()) == "locked"


def test_refresh_rotation_and_readiness(tmp_path):
    """端到端：刷新令牌轮换使旧 refresh 失效；/health/ready 校验依赖。"""
    db_file = tmp_path / "refresh.db"
    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite+aiosqlite:///{db_file.as_posix()}",
        "CACHE_TYPE": "memory",
        "CACHE_ENABLED": "true",
        "TOKEN_VERSION_CACHE_TTL": "0",
        # 故意关闭全局黑名单：轮换仍必须让旧 refresh 失效
        "TOKEN_BLACKLIST_ENABLED": "false",
    }

    code = """
from fastapi.testclient import TestClient

from core import database as db_module
from core.database import Base
from main import app


async def create_tables():
    async with db_module.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


with TestClient(app) as client:
    client.portal.call(create_tables)

    client.post(
        "/api/auth/register",
        json={"username": "u1", "password": "Passw0rd!", "email": "u1@example.com"},
    )
    data = client.post(
        "/api/auth/login",
        json={"username": "u1", "password": "Passw0rd!"},
    ).json()["data"]

    print("has_refresh", bool(data.get("refresh_token")))

    first = client.post("/api/auth/refresh", json={"refresh_token": data["refresh_token"]})
    print("refresh_ok", first.status_code == 200)

    reused = client.post("/api/auth/refresh", json={"refresh_token": data["refresh_token"]})
    print("reuse_blocked", reused.status_code == 401 and reused.json().get("code") == 1009)

    ready = client.get("/health/ready")
    payload = ready.json()["data"]
    print("ready", ready.status_code, payload.get("database"), payload.get("cache"))
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    output = (result.stdout or "") + (result.stderr or "")

    assert "has_refresh True" in output, output
    assert "refresh_ok True" in output, output
    assert "reuse_blocked True" in output, output
    assert "ready 200 ok ok" in output, output


# ============== RBAC 权限模型 ==============

def test_permission_matching_rules():
    """权限匹配：全局通配、精确匹配、未知角色默认无权限。"""
    from config.permissions import has_all_permissions, has_any_permission, has_permission

    assert has_permission("admin", "order:delete") is True          # * 通配
    assert has_permission("user", "profile:read") is True           # 精确
    assert has_permission("user", "order:delete") is False
    assert has_permission("ghost", "profile:read") is False         # 未知角色安全默认
    assert has_permission("", "profile:read") is False

    # any 语义
    assert has_any_permission("user", ["order:read", "profile:read"]) is True
    # all 语义
    assert has_all_permissions("user", ["order:read", "profile:read"]) is False
    # 空需求视为通过（接口未声明权限时不拦截）
    assert has_all_permissions("user", []) is True


def test_permission_resource_wildcard(monkeypatch):
    """资源级通配 order:* 覆盖该资源下所有动作，且不影响其他资源。"""
    from config import permissions

    monkeypatch.setitem(permissions.ROLE_PERMISSIONS, "ops", {"order:*"})

    assert permissions.has_permission("ops", "order:read") is True
    assert permissions.has_permission("ops", "order:write") is True
    assert permissions.has_permission("ops", "user:read") is False


def test_rbac_and_idempotency_end_to_end(tmp_path):
    """端到端：普通用户被 403 拦截、提权后可访问；相同幂等键只落一条数据。"""
    db_file = tmp_path / "rbac_idem.db"
    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite+aiosqlite:///{db_file.as_posix()}",
        "CACHE_TYPE": "memory",
        "CACHE_ENABLED": "true",
        "TOKEN_VERSION_CACHE_TTL": "0",
    }

    code = """
import os
import sqlite3

from fastapi.testclient import TestClient

from core import database as db_module
from core.database import Base
from main import app


async def create_tables():
    async with db_module.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def login(client, username, password):
    return client.post(
        "/api/auth/login", json={"username": username, "password": password}
    ).json()["data"]


with TestClient(app) as client:
    client.portal.call(create_tables)

    payload = {"username": "bob", "password": "Passw0rd!", "email": "bob@example.com"}
    idem_headers = {"Idempotency-Key": "order-0001"}

    first = client.post("/api/auth/register", json=payload, headers=idem_headers)
    print("idem_first", first.status_code, first.headers.get("Idempotent-Replay"))

    replay = client.post("/api/auth/register", json=payload, headers=idem_headers)
    print("idem_replay", replay.status_code, replay.headers.get("Idempotent-Replay"))

    db_path = os.environ["DATABASE_URL"].split("///")[-1]
    con = sqlite3.connect(db_path)
    print("user_count", con.execute("select count(*) from user").fetchone()[0])
    con.close()

    data = login(client, "bob", "Passw0rd!")
    auth = {"Authorization": "Bearer " + data["access_token"]}

    print("role", client.get("/api/auth/permissions", headers=auth).json()["data"]["role"])

    denied = client.get("/admin/admin/menu", headers=auth)
    print("denied", denied.status_code, denied.json().get("code"))

    con = sqlite3.connect(db_path)
    con.execute("update user set role='admin' where username='bob'")
    con.commit()
    con.close()

    promoted = login(client, "bob", "Passw0rd!")
    allowed = client.get(
        "/admin/admin/menu", headers={"Authorization": "Bearer " + promoted["access_token"]}
    )
    print("allowed", allowed.status_code)
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    output = (result.stdout or "") + (result.stderr or "")

    assert "idem_first 200 None" in output, output
    assert "idem_replay 200 true" in output, output
    assert "user_count 1" in output, output
    assert "role user" in output, output
    assert "denied 403 1010" in output, output
    assert "allowed 200" in output, output
