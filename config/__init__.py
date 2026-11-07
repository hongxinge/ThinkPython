"""配置包入口。

在任何 `config.*` 子模块读取环境变量之前，统一加载项目根目录下的 .env，
避免出现"先导入 config.auth 就拿不到 .env 配置"的隐式依赖。
"""
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
