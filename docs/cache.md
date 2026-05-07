# 缓存配置与使用

ThinkPython 支持多种缓存后端，包括 Redis、内存缓存和 Memcached。

---

## 快速开始

### 1. 使用内存缓存（零配置）

默认使用内存缓存，无需任何额外配置即可使用：

```env
CACHE_ENABLED=True
CACHE_TYPE=memory
```

### 2. 使用 Redis 缓存

```bash
# 安装 Redis 驱动
pip install redis
```

修改 `.env` 配置：

```env
CACHE_TYPE=redis
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_MAX_CONNECTIONS=20
```

---

## 在代码中使用缓存

### 基本用法

```python
from core.cache import get_cache, set_cache, delete_cache

# 设置缓存（使用默认过期时间）
await set_cache("user:1", {"name": "张三", "age": 25})

# 设置缓存（自定义过期时间60秒）
await set_cache("user:1", {"name": "张三"}, ttl=60)

# 获取缓存
user = await get_cache("user:1")
if user:
    print(f"缓存命中: {user}")
else:
    print("缓存未命中")

# 删除缓存
await delete_cache("user:1")
```

### 典型使用场景：查询缓存

```python
from core.cache import get_cache, set_cache

@self.router.get("/product/{product_id}", summary="商品详情")
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    """获取商品详情（带缓存）"""
    # 1. 先查缓存
    cache_key = f"product:{product_id}"
    cached = await get_cache(cache_key)
    if cached:
        return self.success(data=cached)
    
    # 2. 缓存未命中，查数据库
    service = ProductService(db)
    product = await service.get_by_id(product_id)
    if not product:
        raise NotFoundException(f"商品 {product_id} 不存在")
    
    # 3. 写入缓存（5分钟过期）
    await set_cache(cache_key, product, ttl=300)
    
    return self.success(data=product)
```

### 缓存更新时删除旧缓存

```python
@self.router.put("/product/{product_id}", summary="更新商品")
async def update_product(product_id: int, request: ProductUpdateRequest, db: AsyncSession = Depends(get_db)):
    """更新商品"""
    service = ProductService(db)
    product = await service.update(product_id, request.model_dump(exclude_unset=True))
    
    if product:
        # 更新成功后删除缓存，下次查询会重新加载
        await delete_cache(f"product:{product_id}")
    
    return self.success(data=product, message="更新成功")
```

---

## 缓存配置详解

### 通用配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `CACHE_ENABLED` | 是否启用缓存 | `True` |
| `CACHE_TYPE` | 缓存类型 | `memory` |
| `CACHE_DEFAULT_TTL` | 默认过期时间（秒） | `3600` |
| `CACHE_PREFIX` | 缓存键前缀 | `thinkpython:` |

### Redis 配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `REDIS_HOST` | Redis 服务器地址 | `127.0.0.1` |
| `REDIS_PORT` | Redis 端口 | `6379` |
| `REDIS_DB` | Redis 数据库编号 | `0` |
| `REDIS_PASSWORD` | Redis 密码 | `` |
| `REDIS_MAX_CONNECTIONS` | 最大连接数 | `20` |

### 内存缓存配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `MEMORY_CACHE_MAX_SIZE` | 最大缓存条目数 | `1000` |
| `MEMORY_CACHE_TTL` | 默认过期时间（秒） | `300` |

---

## 缓存类型对比

| 类型 | 适用场景 | 优点 | 缺点 |
|------|---------|------|------|
| **memory** | 开发环境、单机部署 | 零配置、速度快 | 进程重启丢失、不支持分布式 |
| **redis** | 生产环境、分布式部署 | 持久化、支持分布式、功能丰富 | 需要额外部署 Redis 服务 |
| **memcached** | 简单缓存场景 | 轻量级、高性能 | 功能相对简单 |

---

## 缓存最佳实践

### 1. 合理设置过期时间

```python
# 频繁变化的数据，过期时间短
await set_cache("hot_products", products, ttl=60)

# 相对稳定的数据，过期时间长
await set_cache("config:site", config, ttl=86400)  # 24小时
```

### 2. 使用有意义的前缀

缓存键使用前缀分类：

```python
# 用户相关
await set_cache("user:1", user_data)
await set_cache("user:list:page:1", user_list)

# 商品相关
await set_cache("product:1", product_data)
await set_cache("product:category:1", category_products)

# 配置相关
await set_cache("config:site", site_config)
```

### 3. 缓存穿透防护

```python
from core.cache import get_cache, set_cache

async def get_product(product_id: int):
    cache_key = f"product:{product_id}"
    cached = await get_cache(cache_key)
    
    # 缓存中存在（包括空值标记）
    if cached is not None:
        # 如果是空值标记，说明数据库中也不存在
        if cached == "__NOT_FOUND__":
            return None
        return cached
    
    # 查数据库
    product = await db_query(product_id)
    
    if product:
        await set_cache(cache_key, product, ttl=300)
    else:
        # 缓存空值，防止穿透（短时间过期）
        await set_cache(cache_key, "__NOT_FOUND__", ttl=60)
    
    return product
```

### 4. 批量操作

```python
# 批量设置缓存
products = await service.get_all()
for product in products:
    await set_cache(f"product:{product.id}", product, ttl=300)

# 批量删除缓存（使用模式匹配，需要Redis）
# 可以使用 Redis 的 KEYS 命令或设计时加入索引
```

---

## 常见问题

### Q: 缓存未生效？

1. 确认 `CACHE_ENABLED=True`
2. 检查缓存类型配置是否正确
3. 查看日志是否有连接错误

### Q: Redis 连接失败？

```bash
# 测试 Redis 连接
redis-cli ping
# 应该返回 PONG
```

### Q: 内存缓存会过期吗？

是的，内存缓存已实现 TTL 过期机制。每次读取时会检查是否过期。

---

## 下一步

- 📖 查看 [API 示例](api.md) 了解缓存在实际接口中的用法
- ⚙️ 查看 [配置说明](config.md) 了解所有配置项
