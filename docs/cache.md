# Async Cache Layer Documentation

企业级 FastAPI 异步缓存层，基于 Redis 实现，支持集群模式、自定义键生成策略和缓存失效机制。

## 目录

- [功能特性](#功能特性)
- [快速开始](#快速开始)
- [配置选项](#配置选项)
- [装饰器使用](#装饰器使用)
- [手动缓存操作](#手动缓存操作)
- [缓存键策略](#缓存键策略)
- [最佳实践](#最佳实践)
- [监控与调试](#监控与调试)
- [CLI 命令](#cli-命令)

## 功能特性

- ✅ **异步 Redis 连接池** - 高性能连接管理
- ✅ **JSON/Pickle 序列化** - 灵活的数据序列化
- ✅ **@cache 装饰器** - 声明式缓存
- ✅ **@invalidate_cache 装饰器** - 自动缓存失效
- ✅ **Redis Sentinel 集群支持** - 高可用架构
- ✅ **自定义键生成** - 灵活的缓存键策略
- ✅ **条件缓存** - 基于条件的智能缓存
- ✅ **健康检查** - 内置连接健康监测
- ✅ **CLI 管理工具** - 便捷的缓存管理

## 快速开始

### 1. 基本缓存

```python
from app.core.cache import cache

@cache(ttl=300, key_builder=lambda user_id: f"user:{user_id}")
async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    return await user_repo.get(session, id=user_id)
```

### 2. 缓存失效

```python
from app.core.cache import invalidate_cache

@invalidate_cache(pattern="users:*")
async def update_user(session: AsyncSession, user_id: int, data: UserUpdate) -> User:
    # ... 更新逻辑
    return await user_repo.update(session, user_id, data)
```

## 配置选项

在 `.env` 文件中配置缓存：

```bash
# Redis 缓存连接
REDIS_CACHE_URL=redis://localhost:6379/1
REDIS_PASSWORD=your_password

# 连接池配置
REDIS_POOL_MAX_CONNECTIONS=100
REDIS_SOCKET_TIMEOUT=5.0
REDIS_SOCKET_CONNECT_TIMEOUT=5.0

# Redis Sentinel 配置
REDIS_USE_SENTINEL=false
REDIS_SENTINEL_HOSTS=localhost:26379,localhost:26380
REDIS_SENTINEL_MASTER_NAME=mymaster

# 缓存策略
CACHE_DEFAULT_TTL=300
CACHE_SERIALIZER=json  # json or pickle
```

## 装饰器使用

### @cache 装饰器

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ttl` | int | 300 | 缓存过期时间（秒） |
| `key_builder` | Callable | None | 自定义键生成函数 |
| `prefix` | str | 模块名 | 键前缀 |
| `skip_args` | list[int] | [0] | 跳过的参数索引（通常跳过 session） |
| `condition` | Callable | None | 缓存条件函数 |

### 基础示例

```python
@cache(ttl=300)
async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    return await user_repo.get(session, id=user_id)
```

### 自定义键生成器

```python
@cache(
    ttl=600,
    key_builder=lambda session, user_id: f"user:profile:{user_id}",
)
async def get_user_profile(session: AsyncSession, user_id: int) -> User:
    return await user_repo.get_with_profile(session, user_id=user_id)
```

### 条件缓存

```python
@cache(
    ttl=300,
    condition=lambda result, session, user_id: result is not None and result.is_active,
)
async def get_active_user(session: AsyncSession, user_id: int) -> User | None:
    return await user_repo.get(session, id=user_id)
```

### @invalidate_cache 装饰器

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `pattern` | str | None | 失效键模式（如 "users:*"） |
| `key_builder` | Callable | None | 生成特定键进行删除 |

### 按模式失效

```python
@invalidate_cache(pattern="users:*")
async def create_user(session: AsyncSession, data: UserCreate) -> User:
    # 创建后使所有 users:* 缓存失效
    return await user_repo.create(session, data)
```

### 按特定键失效

```python
@invalidate_cache(key_builder=lambda session, user_id: f"user:{user_id}")
async def update_user(session: AsyncSession, user_id: int, data: UserUpdate) -> User:
    # 更新后仅使特定用户缓存失效
    return await user_repo.update(session, user_id, data)
```

## 手动缓存操作

```python
from app.core.cache import (
    get_cache,
    set_cache,
    delete_cache,
    delete_cache_pattern,
    clear_cache,
    get_cache_info,
)

# 获取缓存
user_data = await get_cache("user:123")

# 设置缓存
await set_cache("user:123", {"id": 123, "name": "John"}, ttl=300)

# 删除特定键
await delete_cache("user:123")

# 按模式删除
await delete_cache_pattern("users:*")

# 清除所有缓存
await clear_cache()

# 获取缓存信息
info = await get_cache_info()
```

## 缓存键策略

### 键命名约定

```
{resource}:{identifier}:{subresource}:{params}

示例：
- users:id:123          # 特定用户
- users:email:abc@test.com  # 按邮箱
- users:list:skip:0:limit:10  # 用户列表
- products:category:electronics:page:1  # 产品分页
```

### 键生成策略

```python
from app.core.cache import CacheKeyBuilder

# 1. 简单键生成器
key = CacheKeyBuilder.simple_key_builder(
    func=get_user,
    prefix="users",
    user_id=123,
)
# 结果: users:app.modules.users.get_user:["123"]

# 2. 哈希键生成器
key = CacheKeyBuilder.hash_key_builder(
    func=get_user,
    prefix="users",
    user_id=123,
)
# 结果: users:get_user:a1b2c3d4

# 3. 自定义模板键生成器
builder = CacheKeyBuilder.custom_key_builder("user:{user_id}:profile")
key = builder(get_user, "users", user_id=123)
# 结果: user:123:profile
```

## 最佳实践

### 1. 合理设置 TTL

```python
# 用户基础信息 - 变化较少，可长缓存
@cache(ttl=1800)  # 30分钟
async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    ...

# 列表数据 - 变化频繁，短缓存
@cache(ttl=60)  # 1分钟
async def get_users_list(session: AsyncSession, skip: int = 0, limit: int = 100):
    ...

# 配置数据 - 几乎不变，极长缓存
@cache(ttl=3600)  # 1小时
async def get_app_config(session: AsyncSession):
    ...
```

### 2. 缓存粒度

```python
# ✅ 好：细粒度缓存，按需失效
@cache(ttl=300, key_builder=lambda s, uid: f"user:{uid}")
async def get_user(session: AsyncSession, user_id: int):
    return await user_repo.get(session, user_id)

@invalidate_cache(key_builder=lambda s, uid: f"user:{uid}")
async def update_user(session: AsyncSession, user_id: int, data):
    return await user_repo.update(session, user_id, data)

# ❌ 避免：粗粒度缓存，频繁失效
@cache(ttl=300)
async def get_all_users(session: AsyncSession):
    return await user_repo.get_all(session)

@invalidate_cache(pattern="users:*")  # 影响太大
async def update_one_user(session: AsyncSession, user_id: int, data):
    ...
```

### 3. 敏感数据不缓存

```python
# ❌ 不要缓存敏感数据
@cache(ttl=300)
async def get_user_credentials(session: AsyncSession, user_id: int):
    return await user_repo.get_credentials(session, user_id)

# ✅ 只缓存公开数据
@cache(ttl=300)
async def get_user_profile(session: AsyncSession, user_id: int):
    return await user_repo.get_profile(session, user_id)
```

### 4. 优雅降级

```python
@cache(ttl=300)
async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    try:
        return await user_repo.get(session, id=user_id)
    except Exception:
        # 失败时从缓存读取（如果可用）
        # 装饰器会自动处理，但你可以在 Service 层做额外处理
        raise
```

### 5. 缓存预热

```python
async def warm_cache():
    """在应用启动时预热常用数据缓存."""
    async with get_db_session() as session:
        # 缓存热门用户
        popular_users = await user_repo.get_popular(session, limit=100)
        for user in popular_users:
            await set_cache(f"user:{user.id}", user, ttl=3600)
        
        # 缓存配置
        configs = await config_repo.get_all(session)
        await set_cache("app:config", configs, ttl=7200)
```

### 6. 分布式环境下的缓存一致性

```python
# 使用事件驱动缓存失效
from app.core.eventbus import eventbus
from app.core.events import USER_UPDATED

@invalidate_cache(key_builder=lambda s, uid: f"user:{uid}")
async def update_user(session: AsyncSession, user_id: int, data: UserUpdate) -> User:
    user = await user_repo.update(session, user_id, data)
    # 发布事件通知其他实例
    eventbus.publish(USER_UPDATED, {"user_id": user_id})
    return user

# 在其他实例中监听并失效本地缓存
def handle_user_updated(event):
    # 可选：清除本地缓存或让自然过期
    pass

eventbus.subscribe(USER_UPDATED, handle_user_updated)
```

## 监控与调试

### 日志输出

缓存层会自动记录以下日志：

```
- Cache hit (DEBUG)
- Cache miss (DEBUG)
- Cache set (DEBUG)
- Cache invalidated (DEBUG)
- Cache error (WARNING)
- Cache initialized (INFO)
```

### 健康检查

```python
# 在 /health/ready 端点包含缓存健康检查
{
    "status": "ready",
    "cache": {
        "redis": "connected"  # 或 "unavailable"
    }
}
```

### 指标监控

使用 `get_cache_info()` 获取统计信息：

```python
info = await get_cache_info()
# {
#     "status": "connected",
#     "redis_version": "7.0.0",
#     "used_memory_human": "1.5M",
#     "connected_clients": 10,
#     "keyspace_hits": 1000,
#     "keyspace_misses": 100,
# }
```

计算命中率：
```python
hits = info.get("keyspace_hits", 0)
misses = info.get("keyspace_misses", 0)
total = hits + misses
hit_rate = (hits / total * 100) if total > 0 else 0
```

## CLI 命令

### 安装 CLI

```bash
pip install -e .  # 或 pip install -e .[dev]
```

### 查看缓存信息

```bash
manage cache info
```

### 查看统计

```bash
manage cache stats
```

### 列出缓存键

```bash
# 列出所有键
manage cache keys

# 按模式列出
manage cache keys "users:*"

# 限制数量
manage cache keys "users:*" --limit 50
```

### 获取/设置缓存

```bash
# 获取缓存值
manage cache get "user:123"

# 设置缓存值
manage cache set "user:123" '{"id": 123, "name": "Test"}' --ttl 300
```

### 删除缓存

```bash
# 删除特定键
manage cache delete "user:123"

# 按模式删除（预览）
manage cache delete-pattern "users:*" --dry-run

# 按模式删除（执行）
manage cache delete-pattern "users:*"

# 清除所有缓存
manage cache clear --force
```

## 完整示例

### Users 模块缓存实现

```python
# app/modules/users/service.py

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache, invalidate_cache
from app.core.exceptions import ConflictException, NotFoundException
from app.modules.users.models import User
from app.modules.users.repository import user_repo
from app.modules.users.schemas import UserCreate, UserUpdate


@cache(ttl=300, key_builder=lambda session, user_id: f"users:id:{user_id}")
async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    """Get user by ID with caching.

    Cache key: users:id:{user_id}
    TTL: 5 minutes
    """
    return await user_repo.get(session, id=user_id)


@cache(ttl=300, key_builder=lambda session, email: f"users:email:{email}")
async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """Get user by email with caching.

    Cache key: users:email:{email}
    TTL: 5 minutes
    """
    return await user_repo.get_by_email(session, email=email)


@cache(ttl=60, key_builder=lambda session, skip=0, limit=100: f"users:list:skip:{skip}:limit:{limit}")
async def get_users(session: AsyncSession, skip: int = 0, limit: int = 100) -> list[User]:
    """Get users list with caching (short TTL due to frequent changes).

    Cache key: users:list:skip:{skip}:limit:{limit}
    TTL: 1 minute
    """
    users = await user_repo.get_multi(session, skip=skip, limit=limit)
    return list(users)


@cache(ttl=60, prefix="users")
async def get_users_count(session: AsyncSession) -> int:
    """Get total users count with caching (short TTL).

    Cache key: users:{module}.{function}
    TTL: 1 minute
    """
    return await user_repo.count(session)


@invalidate_cache(pattern="users:*")
async def create_user(session: AsyncSession, data: UserCreate) -> User:
    """Create a new user and invalidate all users cache.

    Invalidates: All cache keys matching 'users:*'
    """
    existing = await user_repo.get_by_email(session, email=data.email)
    if existing:
        raise ConflictException(f"Email {data.email} already registered")
    
    user = await user_repo.create(session, data=data)
    return user


@invalidate_cache(pattern="users:*")
async def update_user(session: AsyncSession, user_id: int, data: UserUpdate) -> User:
    """Update user and invalidate users cache.

    Invalidates: All cache keys matching 'users:*'
    """
    user = await user_repo.get(session, id=user_id)
    if not user:
        raise NotFoundException(f"User with id {user_id} not found")
    
    if data.email and data.email != user.email:
        existing = await user_repo.get_by_email(session, email=data.email)
        if existing:
            raise ConflictException(f"Email {data.email} already registered")
    
    user = await user_repo.update(session, instance=user, data=data)
    return user


@invalidate_cache(pattern="users:*")
async def delete_user(session: AsyncSession, user_id: int) -> User:
    """Delete user and invalidate users cache.

    Invalidates: All cache keys matching 'users:*'
    """
    user = await user_repo.get(session, id=user_id)
    if not user:
        raise NotFoundException(f"User with id {user_id} not found")
    
    return await user_repo.delete(session, id=user_id)
```

## 故障排除

### 缓存未生效

1. 检查 Redis 连接：
   ```bash
   manage cache info
   ```

2. 确认装饰器参数：
   - 确保 `ttl` 设置正确
   - 检查 `key_builder` 生成唯一键

3. 查看日志级别（设置为 DEBUG）：
   ```bash
   LOG_LEVEL=DEBUG uvicorn app.main:app
   ```

### 缓存一致性问题

1. 确保数据更新时调用了 `@invalidate_cache`
2. 考虑在分布式环境中使用事件驱动失效
3. 设置合理的 TTL，让数据自然过期

### Redis 连接问题

1. 检查 Redis URL 配置
2. 确认 Redis 服务运行状态
3. 验证网络连接（特别是 Sentinel 模式）

## 参考资料

- [aiocache Documentation](https://github.com/aio-libs/aiocache)
- [Redis Python Client](https://redis.readthedocs.io/en/stable/)
- [Redis Sentinel Guide](https://redis.io/docs/management/sentinel/)
