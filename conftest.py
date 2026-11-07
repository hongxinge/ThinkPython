"""pytest 全局配置与共享 fixture。

职责：
1. 统一把项目根注入 sys.path，避免各测试文件各自拼路径；
2. 注册自定义 marker（regression / security / integration）；
3. 提供不依赖外部服务的 ASGI 测试客户端。

注意：本文件不在导入期导入 main，避免路由扫描与配置求值影响测试收集。
"""
import sys
from pathlib import Path

import pytest
import pytest_asyncio

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def pytest_configure(config):
    """注册项目自定义 marker，避免 PytestUnknownMarkWarning。"""
    config.addinivalue_line("markers", "regression: 已确认缺陷的回归测试（修复前预期失败）")
    config.addinivalue_line("markers", "security: 安全相关测试")
    config.addinivalue_line("markers", "integration: 集成测试")


@pytest.fixture(scope="session")
def project_root() -> Path:
    """返回项目根目录，供需要读取工程文件的测试使用。"""
    return PROJECT_ROOT


@pytest_asyncio.fixture
async def api_client():
    """创建不触发 lifespan 的 ASGI 测试客户端。

    使用 httpx.ASGITransport 直接驱动应用，不启动 uvicorn、不连接 MySQL/Redis，
    适合验证路由、中间件与响应契约。
    """
    from httpx import ASGITransport, AsyncClient

    from main import create_app

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
