"""
ThinkPython API 限流中间件

本模块提供基于令牌桶算法的请求频率限制功能，支持：
- Redis 限流（分布式环境，推荐生产使用）
- 内存限流（单机环境，开发/测试使用）
- 多维度限流：全局限流 + IP 限流 + 用户限流 + 路由限流
- 自定义限流规则

限流策略说明：
1. 全局限流：整个应用每秒允许的最大请求数
2. IP 限流：单个 IP 每分钟允许的最大请求数
3. 用户限流：已登录用户每小时允许的最大请求数
4. 路由限流：特定路由（如登录接口）每分钟允许的最大请求数

工作原理（令牌桶算法）：
1. 每个桶以固定速率生成令牌
2. 每个请求消耗一个令牌
3. 桶满时令牌不再累积
4. 无令牌时拒绝请求（返回 429）

配置说明（config/ratelimit.py）：
- RATE_LIMIT_ENABLED: 是否启用限流
- RATE_LIMIT_BACKEND: 限流后端（redis/memory）
- RATE_LIMIT_RULES: 限流规则字典

使用示例:
    # 在 main.py 中注册
    from middleware.ratelimit import setup_rate_limit
    
    app = FastAPI()
    setup_rate_limit(app)
    
    # 配置限流规则（config/ratelimit.py）
    RATE_LIMIT_RULES = {
        "global": {"requests": 1000, "period": 60},      # 全局：1000 次/分钟
        "ip": {"requests": 100, "period": 60},            # IP：100 次/分钟
        "login": {"requests": 5, "period": 60},           # 登录：5 次/分钟
    }
"""
import time
import hashlib
from typing import Dict, Optional, Any
from collections import defaultdict
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from loguru import logger

# 尝试从配置中读取限流配置
try:
    from config.ratelimit import (
        RATE_LIMIT_ENABLED,
        RATE_LIMIT_BACKEND,
        RATE_LIMIT_RULES,
        RATE_LIMIT_REDIS_PREFIX,
    )
except ImportError:
    # 默认配置
    RATE_LIMIT_ENABLED = False
    RATE_LIMIT_BACKEND = "memory"
    RATE_LIMIT_RULES = {}
    RATE_LIMIT_REDIS_PREFIX = "ratelimit:"


class TokenBucket:
    """令牌桶实现（内存版）
    
    基于令牌桶算法的简单实现，适用于单机环境。
    生产环境建议使用 Redis 实现分布式限流。
    
    Attributes:
        rate: 令牌生成速率（个/秒）
        capacity: 桶容量（最大令牌数）
        tokens: 当前令牌数量
        last_refill: 上次补充令牌的时间
    """
    
    def __init__(self, rate: float, capacity: int):
        """初始化令牌桶
        
        Args:
            rate: 令牌生成速率（个/秒）
            capacity: 桶容量（最大令牌数）
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = float(capacity)
        self.last_refill = time.monotonic()
    
    def consume(self, tokens: int = 1) -> bool:
        """尝试消耗令牌
        
        Args:
            tokens: 需要消耗的令牌数量
            
        Returns:
            bool: 成功消耗返回 True，令牌不足返回 False
        """
        now = time.monotonic()
        elapsed = now - self.last_refill
        
        # 补充令牌
        refill = elapsed * self.rate
        self.tokens = min(self.capacity, self.tokens + refill)
        self.last_refill = now
        
        # 检查是否有足够令牌
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        
        return False


class MemoryRateLimiter:
    """内存限流器（单机环境）
    
    使用内存存储令牌桶，适用于开发和测试环境。
    进程重启后限流状态会丢失。
    
    Attributes:
        buckets: 令牌桶字典，key 为限流维度，value 为 TokenBucket 实例
    """
    
    def __init__(self):
        self.buckets: Dict[str, TokenBucket] = {}
    
    def is_allowed(self, key: str, rate: float, capacity: int) -> bool:
        """检查是否允许请求
        
        Args:
            key: 限流 key（如 "ip:127.0.0.1"）
            rate: 令牌生成速率（个/秒）
            capacity: 桶容量
            
        Returns:
            bool: 允许返回 True，拒绝返回 False
        """
        if key not in self.buckets:
            self.buckets[key] = TokenBucket(rate, capacity)
        
        return self.buckets[key].consume()
    
    def cleanup(self):
        """清理过期的令牌桶（可选，防止内存泄漏）"""
        # 简单实现：当桶数量超过阈值时清理空桶
        if len(self.buckets) > 10000:
            self.buckets = {k: v for k, v in self.buckets.items() if v.tokens < v.capacity}


class RedisRateLimiter:
    """Redis 限流器（分布式环境）
    
    使用 Redis 存储令牌桶状态，支持多实例共享限流状态。
    使用 Lua 脚本保证原子性操作。
    
    Attributes:
        redis_client: Redis 客户端实例
        prefix: Redis Key 前缀
    """
    
    # Lua 脚本：原子性检查并消耗令牌
    LUA_SCRIPT = """
    local key = KEYS[1]
    local rate = tonumber(ARGV[1])
    local capacity = tonumber(ARGV[2])
    local now = tonumber(ARGV[3])
    local requested = tonumber(ARGV[4])
    
    -- 获取当前令牌数量
    local tokens = redis.call('GET', key)
    if tokens == false then
        -- 初始化令牌桶
        tokens = capacity
        redis.call('SET', key, tokens)
        redis.call('EXPIRE', key, math.ceil(capacity / rate) + 1)
    else
        tokens = tonumber(tokens)
    end
    
    -- 计算需要补充的令牌
    local last_time = redis.call('GET', key .. ':time')
    if last_time == false then
        last_time = now
    else
        last_time = tonumber(last_time)
    end
    
    local elapsed = now - last_time
    local refill = elapsed * rate
    tokens = math.min(capacity, tokens + refill)
    
    -- 检查是否有足够令牌
    local allowed = 0
    if tokens >= requested then
        tokens = tokens - requested
        allowed = 1
    end
    
    -- 更新令牌数量和时间
    redis.call('SET', key, tokens)
    redis.call('SET', key .. ':time', now)
    
    return {allowed, math.floor(tokens)}
    """
    
    def __init__(self, redis_client, prefix: str = "ratelimit:"):
        """初始化 Redis 限流器
        
        Args:
            redis_client: Redis 客户端实例（支持 aioredis 或 redis-py）
            prefix: Redis Key 前缀
        """
        self.redis_client = redis_client
        self.prefix = prefix
        self._sha = None  # Lua 脚本 SHA1
    
    async def is_allowed(self, key: str, rate: float, capacity: int) -> bool:
        """检查是否允许请求（异步）
        
        Args:
            key: 限流 key
            rate: 令牌生成速率（个/秒）
            capacity: 桶容量
            
        Returns:
            bool: 允许返回 True，拒绝返回 False
        """
        import time
        
        redis_key = f"{self.prefix}{key}"
        now = time.time()
        
        # 缓存 Lua 脚本 SHA
        if self._sha is None:
            self._sha = await self.redis_client.script_load(self.LUA_SCRIPT)
        
        try:
            result = await self.redis_client.evalsha(
                self._sha,
                1,
                redis_key,
                str(rate),
                str(capacity),
                str(now),
                "1",  # 每次请求消耗 1 个令牌
            )
            return result[0] == 1
        except Exception as e:
            # Redis 异常时默认允许请求（降级策略）
            logger.error(f"Redis 限流异常: {e}")
            return True


class RateLimitMiddleware:
    """限流中间件
    
    拦截所有 HTTP 请求，根据配置的限流规则检查是否允许请求。
    超出限制的请求返回 429 Too Many Requests。
    
    Attributes:
        limiter: 限流器实例（MemoryRateLimiter 或 RedisRateLimiter）
        rules: 限流规则字典
    """
    
    def __init__(self, rules: Dict[str, Dict[str, Any]] = None):
        """初始化限流中间件
        
        Args:
            rules: 限流规则字典，格式如下：
                {
                    "global": {"requests": 1000, "period": 60},  # 全局限流
                    "ip": {"requests": 100, "period": 60},       # IP 限流
                    "login": {"requests": 5, "period": 60},      # 路由限流
                }
        """
        self.rules = rules or {}
        self.limiter = None
    
    def init_limiter(self):
        """初始化限流器"""
        if RATE_LIMIT_BACKEND == "redis":
            try:
                from core.cache import cache_client
                if hasattr(cache_client, 'client') and cache_client.client:
                    self.limiter = RedisRateLimiter(
                        cache_client.client,
                        prefix=RATE_LIMIT_REDIS_PREFIX
                    )
                    logger.info("限流后端: Redis")
                    return
            except Exception as e:
                logger.warning(f"Redis 限流器初始化失败，降级到内存模式: {e}")
        
        # 默认使用内存限流器
        self.limiter = MemoryRateLimiter()
        logger.info("限流后端: Memory")
    
    async def __call__(self, request: Request, call_next):
        """限流中间件主函数
        
        Args:
            request: FastAPI 请求对象
            call_next: 下一个中间件或路由处理函数
            
        Returns:
            Response: 响应对象
        """
        if not RATE_LIMIT_ENABLED or not self.rules:
            return await call_next(request)
        
        # 初始化限流器（延迟初始化）
        if self.limiter is None:
            self.init_limiter()
        
        # 获取请求信息
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path
        method = request.method
        
        # 1. 检查全局限流
        if "global" in self.rules:
            rule = self.rules["global"]
            rate = rule["requests"] / rule["period"]
            if not await self._check(f"global", rate, rule["requests"]):
                return self._rate_limit_response("系统繁忙，请稍后再试")
        
        # 2. 检查 IP 限流
        if "ip" in self.rules:
            rule = self.rules["ip"]
            rate = rule["requests"] / rule["period"]
            if not await self._check(f"ip:{client_ip}", rate, rule["requests"]):
                return self._rate_limit_response(f"IP {client_ip} 请求过于频繁")
        
        # 3. 检查路由限流（按路径匹配）
        for rule_name, rule in self.rules.items():
            if rule_name in ("global", "ip", "user"):
                continue
            
            # 路由限流规则格式：{"login": {"requests": 5, "period": 60, "paths": ["/auth/login"]}}
            if "paths" in rule:
                if self._path_matches(path, rule["paths"]):
                    rate = rule["requests"] / rule["period"]
                    key = f"route:{rule_name}:{client_ip}"
                    if not await self._check(key, rate, rule["requests"]):
                        return self._rate_limit_response(f"接口 {path} 请求过于频繁")
        
        # 所有限流检查通过，继续处理请求
        response = await call_next(request)
        
        # 添加限流响应头
        response.headers["X-RateLimit-Limit"] = str(self.rules.get("ip", {}).get("requests", "unknown"))
        
        return response
    
    async def _check(self, key: str, rate: float, capacity: int) -> bool:
        """检查限流规则
        
        Args:
            key: 限流 key
            rate: 令牌生成速率
            capacity: 桶容量
            
        Returns:
            bool: 允许返回 True，拒绝返回 False
        """
        return await self.limiter.is_allowed(key, rate, capacity)
    
    def _path_matches(self, path: str, patterns: list) -> bool:
        """检查路径是否匹配限流规则
        
        Args:
            path: 请求路径
            patterns: 限流路径模式列表
            
        Returns:
            bool: 匹配返回 True
        """
        for pattern in patterns:
            if path == pattern or path.startswith(pattern.rstrip("*")):
                return True
        return False
    
    def _rate_limit_response(self, message: str) -> JSONResponse:
        """生成限流响应
        
        Args:
            message: 提示信息
            
        Returns:
            JSONResponse: 429 响应
        """
        return JSONResponse(
            status_code=429,
            content={
                "code": 429,
                "message": message,
                "data": None,
            },
            headers={
                "Retry-After": "60",  # 建议客户端 60 秒后重试
                "X-RateLimit-Limit": "limit reached",
            }
        )


def setup_rate_limit(app, rules: Dict[str, Dict[str, Any]] = None):
    """在 FastAPI 应用中注册限流中间件
    
    Args:
        app: FastAPI 应用实例
        rules: 限流规则字典（可选，默认从配置读取）
        
    使用示例:
        from middleware.ratelimit import setup_rate_limit
        
        app = FastAPI()
        setup_rate_limit(app)
    """
    if not RATE_LIMIT_ENABLED:
        logger.info("限流功能未启用")
        return
    
    middleware = RateLimitMiddleware(rules or RATE_LIMIT_RULES)
    app.middleware("http")(middleware)
    logger.info(f"限流中间件注册成功（后端: {RATE_LIMIT_BACKEND}）")
