"""
ThinkPython API 限流配置

集中管理 API 请求频率限制配置，包括：
- 是否启用限流
- 限流后端选择（Redis / Memory）
- 限流规则定义（全局、IP、用户、路由）

限流策略说明：
1. 全局限流：整个应用允许的最大请求频率
2. IP 限流：单个 IP 地址允许的最大请求频率
3. 用户限流：已登录用户允许的最大请求频率（可选）
4. 路由限流：特定接口（如登录）允许的最大请求频率

使用方式：
    # 在 main.py 中启用限流
    from middleware.ratelimit import setup_rate_limit
    
    app = FastAPI()
    setup_rate_limit(app)
    
    # 在 .env 中配置限流开关
    RATE_LIMIT_ENABLED=true
"""
import os

# ==============================
# 限流开关和后端配置
# ==============================

# 是否启用限流功能
# True: 启用限流，所有请求将经过限流检查
# False: 关闭限流，所有请求直接放行
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "false").lower() == "true"

# 限流后端选择
# "memory": 内存限流器，适用于单机环境（开发/测试）
# "redis": Redis 限流器，适用于分布式环境（生产）
RATE_LIMIT_BACKEND = os.getenv("RATE_LIMIT_BACKEND", "memory")

# ==============================
# 限流规则配置
# ==============================

# 限流规则字典
# 格式：{规则名: {"requests": 最大请求数, "period": 时间窗口（秒）}}
# 
# 支持的规则类型：
# - "global": 全局限流，限制整个应用的请求频率
# - "ip": IP 限流，限制单个 IP 的请求频率
# - "user": 用户限流，限制单个用户的请求频率（需要认证）
# - 其他自定义规则名：路由限流，需要额外配置 "paths" 字段

RATE_LIMIT_RULES = {
    # 全局限流：1000 次/分钟（约 16.7 次/秒）
    # 适用于保护整个应用免受突发流量冲击
    "global": {
        "requests": int(os.getenv("RATE_LIMIT_GLOBAL_REQUESTS", "1000")),
        "period": int(os.getenv("RATE_LIMIT_GLOBAL_PERIOD", "60")),
    },
    
    # IP 限流：100 次/分钟（约 1.67 次/秒）
    # 适用于防止单个 IP 恶意刷接口
    "ip": {
        "requests": int(os.getenv("RATE_LIMIT_IP_REQUESTS", "100")),
        "period": int(os.getenv("RATE_LIMIT_IP_PERIOD", "60")),
    },
    
    # 登录接口限流：5 次/分钟
    # 适用于防止暴力破解密码
    "login": {
        "requests": int(os.getenv("RATE_LIMIT_LOGIN_REQUESTS", "5")),
        "period": int(os.getenv("RATE_LIMIT_LOGIN_PERIOD", "60")),
        "paths": ["/auth/login", "/login"],  # 需要限流的路由路径
    },
    
    # 注册接口限流：3 次/分钟
    # 适用于防止恶意批量注册
    "register": {
        "requests": int(os.getenv("RATE_LIMIT_REGISTER_REQUESTS", "3")),
        "period": int(os.getenv("RATE_LIMIT_REGISTER_PERIOD", "60")),
        "paths": ["/auth/register", "/register"],
    },
    
    # 忘记密码接口限流：2 次/分钟
    # 适用于防止短信/邮件轰炸
    "forgot_password": {
        "requests": int(os.getenv("RATE_LIMIT_FORGOT_PASSWORD_REQUESTS", "2")),
        "period": int(os.getenv("RATE_LIMIT_FORGOT_PASSWORD_PERIOD", "60")),
        "paths": ["/auth/forgot-password", "/forgot-password"],
    },
}

# ==============================
# Redis 限流配置
# ==============================

# Redis Key 前缀，用于区分不同应用的限流数据
RATE_LIMIT_REDIS_PREFIX = os.getenv("RATE_LIMIT_REDIS_PREFIX", "ratelimit:")
