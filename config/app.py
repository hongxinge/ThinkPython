"""
应用配置文件
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


BASE_DIR = Path(__file__).resolve().parent.parent


APP_CONFIG = {
    # 应用名称
    "name": os.getenv("APP_NAME", "ThinkPython"),
    
    # 应用版本
    "version": os.getenv("APP_VERSION", "1.0.0"),
    
    # 调试模式
    "debug": os.getenv("APP_DEBUG", "True").lower() == "true",
    
    # 模块模式: "single" 单模块 | "multi" 多模块
    "module_mode": os.getenv("MODULE_MODE", "single"),
    
    # 启用的模块列表 (仅在 module_mode="multi" 时生效)
    "modules": os.getenv("ENABLED_MODULES", "admin,api").split(","),
    
    # 默认模块 (访问时不指定模块前缀时使用的模块)
    "default_module": os.getenv("DEFAULT_MODULE", "api"),
    
    # 路由前缀 (多模块时使用, {prefix}/{module}/{controller}/{action})
    "route_prefix": os.getenv("ROUTE_PREFIX", ""),
    
    # 时区
    "timezone": os.getenv("TIMEZONE", "Asia/Shanghai"),
    
    # 语言
    "language": os.getenv("LANGUAGE", "zh-CN"),
    
    # CORS 配置
    "cors": {
        "allow_origins": os.getenv("CORS_ORIGINS", "*").split(","),
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    },
    
    # 日志配置
    "log": {
        "level": os.getenv("LOG_LEVEL", "INFO"),
        "file": BASE_DIR / "logs" / "app.log",
        "max_bytes": 10 * 1024 * 1024,  # 10MB
        "backup_count": 5,
    },
}
