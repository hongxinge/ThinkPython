# 缓存使用

ThinkPython 支持 Redis、Memory、Memcached 三种缓存后端，通过 `.env` 文件切换。

## 配置方式

所有缓存在 `config/cache.py` 中管理。

### Memory（默认）

零配置，数据存储在内存中，进程重启后丢失，适合开发环境。

**.env 配置：**

```env
CACHE_TYPE=memory
MEMORY_CACHE_MAX_SIZE=1000
MEMORY_CACHE_TTL=300
```

### Redis（生产环境推荐）

支持持久化和分布式缓存。

**.env 配置：**

```env
CACHE_TYPE=redis
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
```

**安装驱动：**

```bash
pip install redis
```

### Memcached

**.env 配置：**

```env
CACHE_TYPE=memcached
MEMCACHED_SERVERS=127.0.0.1:11211
```

## 代码示例

框架提供了三个全局函数操作缓存，自动处理键前缀和序列化。

### 引入

```python
from core.cache import get_cache, set_cache, delete_cache
```

### 设置缓存

```python
# 使用默认过期时间（默认 1 小时）
await set_cache("user:1", {"name": "张三", "age": 25})

# 指定过期时间（秒）
await set_cache("user:1", {"name": "张三"}, ttl=60)

# 缓存简单字符串
await set_cache("site:name", "ThinkPython")
```

### 获取缓存

```python
# 读取缓存，不存在时返回 None
data = await get_cache("user:1")
if data:
    print(data["name"])
```

### 删除缓存

```python
await delete_cache("user:1")
```

### 在 Controller 中使用示例

```python
from core.cache import get_cache, set_cache, delete_cache

class UserController(BaseController):
    
    def _setup_routes(self):
        @self.router.get("/user/{user_id}")
        async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
            # 先查缓存
            cache_data = await get_cache(f"user:{user_id}")
            if cache_data:
                return self.success(data=cache_data)
            
            # 缓存未命中，查询数据库
            service = UserService(db)
            user = await service.get_by_id(user_id)
            
            # 写入缓存，5 分钟过期
            await set_cache(f"user:{user_id}", user, ttl=300)
            
            return self.success(data=user)
        
        @self.router.put("/user/{user_id}")
        async def update_user(user_id: int, request: UserUpdateRequest, db: AsyncSession = Depends(get_db)):
            service = UserService(db)
            user_data = request.model_dump(exclude_unset=True)
            user = await service.update(user_id, user_data)
            
            # 更新后删除旧缓存
            await delete_cache(f"user:{user_id}")
            
            return self.success(data=user, message="更新成功")
```

## 缓存配置项

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `CACHE_TYPE` | 缓存类型 | `memory` |
| `CACHE_ENABLED` | 是否启用缓存 | `True` |
| `CACHE_DEFAULT_TTL` | 默认过期时间（秒） | `3600` |
| `CACHE_PREFIX` | 缓存键前缀 | `thinkpython:` |
| `REDIS_HOST` | Redis 地址 | `127.0.0.1` |
| `REDIS_PORT` | Redis 端口 | `6379` |
| `REDIS_DB` | Redis 数据库编号 | `0` |
| `MEMORY_CACHE_MAX_SIZE` | 内存缓存最大条目数 | `1000` |
| `MEMORY_CACHE_TTL` | 内存缓存默认过期时间（秒） | `300` |

---

[← 返回首页](../README.md)
