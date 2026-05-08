"""
ThinkPython 应用配置文件

本文件负责加载和管理整个应用的全局配置项，包括：
- 应用基本信息（名称、版本、调试模式等）
- 模块模式配置（单模块/多模块）
- 路由前缀配置
- 时区和语言设置
- CORS 跨域配置
- 日志配置

所有配置项均支持通过 .env 环境变量覆盖，遵循 "环境变量优先" 的原则。
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载项目根目录下的 .env 环境变量文件
# Path(__file__).resolve().parent.parent 指向项目根目录
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


# 项目根目录的绝对路径，后续所有相对路径都基于此目录
BASE_DIR = Path(__file__).resolve().parent.parent


# ===============================
# 模块配置预处理
# ===============================
# ENABLED_MODULES 配置说明：
#   "*" 或空字符串 = 自动发现模式，框架自动扫描 app/ 下所有模块
#   具体模块名（逗号分隔）= 白名单模式，只加载配置的模块
_enabled_modules_raw = os.getenv("ENABLED_MODULES", "*")
_enabled_modules = [m.strip() for m in _enabled_modules_raw.split(",") if m.strip()]


# 应用配置字典，集中管理所有配置项
# 使用 os.getenv() 从环境变量读取，第二个参数为默认值
APP_CONFIG = {
    # 应用名称，用于日志、API 文档展示等场景
    "name": os.getenv("APP_NAME", "ThinkPython"),
    
    # 应用版本号，遵循语义化版本规范
    "version": os.getenv("APP_VERSION", "1.0.0"),
    
    # 调试模式开关
    # 开启后会显示详细的错误堆栈、启用 API 文档（/docs 和 /redoc）、开启热重载等
    "debug": os.getenv("APP_DEBUG", "True").lower() == "true",
    
    # 模块模式配置
    # "single" - 单模块模式：所有控制器放在 app/single/ 目录下，适合小型项目
    # "multi"  - 多模块模式：按业务模块拆分到 app/admin/、app/api/ 等目录，适合中大型项目
    "module_mode": os.getenv("MODULE_MODE", "single"),
    
    # 启用的模块列表（仅在 module_mode="multi" 时生效）
    # "*" 或留空  = 自动发现模式（推荐），框架自动扫描 app/ 下所有包含 controller/ 子目录的模块
    # "admin,api" = 白名单模式，只加载 admin 和 api 两个模块
    # 开发环境建议用 "*"，生产环境建议指定具体模块名
    "modules": _enabled_modules,
    
    # 默认模块：当 URL 中不指定模块前缀时，路由系统默认使用的模块
    "default_module": os.getenv("DEFAULT_MODULE", "api"),
    
    # 路由前缀：多模块模式下 URL 的统一前缀
    "route_prefix": os.getenv("ROUTE_PREFIX", ""),
    
    # 应用时区，用于时间格式化和日志时间戳
    "timezone": os.getenv("TIMEZONE", "Asia/Shanghai"),
    
    # 应用语言，用于国际化消息展示
    "language": os.getenv("LANGUAGE", "zh-CN"),
    
    # CORS（跨域资源共享）配置
    "cors": {
        # 允许的请求来源域名，"*" 表示允许所有来源（生产环境建议指定具体域名）
        "allow_origins": os.getenv("CORS_ORIGINS", "*").split(","),
        # 是否允许携带认证信息（Cookie、Authorization 头等）
        "allow_credentials": True,
        # 允许的 HTTP 请求方法
        "allow_methods": ["*"],
        # 允许的 HTTP 请求头
        "allow_headers": ["*"],
    },
    
    # 日志配置
    "log": {
        # 日志级别：DEBUG < INFO < WARNING < ERROR < CRITICAL
        "level": os.getenv("LOG_LEVEL", "INFO"),
        # 日志文件存储路径
        "file": BASE_DIR / "logs" / "app.log",
        # 单个日志文件的最大字节数（默认 10MB）
        "max_bytes": 10 * 1024 * 1024,
        # 保留的历史日志文件数量
        "backup_count": 5,
    },
}
