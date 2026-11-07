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

# CORS 来源与凭证开关预处理：
# 浏览器规范禁止 allow_origins="*" 与 allow_credentials=True 同时生效。
# 未显式指定来源时自动关闭凭证，避免产生浏览器必定拒绝的跨域配置。
_cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
_cors_allow_credentials = "*" not in _cors_origins


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

    # 错误响应模式
    # "standard" - 推荐：HTTP 状态码表达传输语义，body.code 表达业务语义
    # "legacy"   - 兼容旧版：所有 self.error() 一律返回 HTTP 200，靠 body.code 判断
    "error_http_mode": os.getenv("ERROR_HTTP_MODE", "standard").lower(),
    
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

    # 是否信任反向代理传来的客户端 IP 头（X-Forwarded-For / X-Real-IP）
    # False - 直连部署：只信任 TCP 连接的对端地址（默认，防伪造）
    # True  - 部署在 Nginx / 云负载均衡之后：采信代理写入的真实 IP，
    #         否则限流会把所有用户识别成同一个 IP
    "trust_proxy": os.getenv("TRUST_PROXY", "false").lower() == "true",
    
    # CORS（跨域资源共享）配置
    "cors": {
        # 允许的请求来源域名，"*" 表示允许所有来源（生产环境建议指定具体域名）
        "allow_origins": _cors_origins,
        # 是否允许携带认证信息（Cookie、Authorization 头等）
        # 来源为 "*" 时自动关闭，否则浏览器会拒绝携带凭证的跨域请求
        "allow_credentials": _cors_allow_credentials,
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
        # 慢请求阈值（毫秒）：超过此耗时的请求以 WARNING 级别记录，
        # 便于直接按日志级别抓取慢接口，无需额外 APM
        "slow_request_ms": int(os.getenv("LOG_SLOW_REQUEST_MS", "500")),
    },
}
