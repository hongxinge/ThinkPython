"""Token 状态校验（token_version）

解决什么问题：
    纯无状态 JWT 一旦签发，在过期前无法撤销。用户改密码、管理员禁用账号后，
    旧 Token 仍能继续访问，这是客户端 API 的典型安全缺口。

方案：
    用户表增加 ``token_version`` 整数列。签发 Token 时写入 payload 的 ``ver``；
    校验时比对数据库中的当前值。改密/禁用时把该值 +1，所有旧 Token 立即失效。
    刷新 Token 时原样透传 ``ver``，因此旧 Refresh Token 也无法"复活"。

性能权衡（为什么需要缓存）：
    逐请求查库会给数据库增加一次主键查询。这里用缓存（Redis/Memory）承接，
    默认缓存 60 秒：命中时零数据库开销，未命中才回落到一次主键查询。
    最坏情况下（改密后 60 秒内）旧 Token 仍可用，这由
    ``TOKEN_VERSION_CACHE_TTL`` 控制；把 TTL 设为 0 即退化为每次查库（最严格）。

关闭方式：
    ``TOKEN_VERSION_CHECK=false`` 时完全跳过校验，回到纯无状态 JWT（零开销），
    适合内部服务或不接受任何额外查库的场景。
"""
from typing import Optional

from loguru import logger

from config.auth import TOKEN_VERSION_CACHE_TTL, TOKEN_VERSION_CHECK

# 缓存键前缀（cache 层会再拼全局前缀）
TOKEN_VERSION_CACHE_PREFIX = "token_ver:"


def _cache_key(user_id: int) -> str:
    return f"{TOKEN_VERSION_CACHE_PREFIX}{user_id}"


async def get_current_token_version(user_id: int) -> Optional[int]:
    """获取用户当前的 token 版本号

    Args:
        user_id: 用户 ID

    Returns:
        Optional[int]: 版本号；用户不存在时返回 None
    """
    from core.cache import get_cache, set_cache

    # 1. 缓存优先
    try:
        cached = await get_cache(_cache_key(user_id))
    except Exception as exc:  # noqa: BLE001 - 缓存故障不应导致认证失败
        logger.warning(f"读取 token 版本缓存失败，回落到数据库: {exc}")
        cached = None

    if cached is not None:
        try:
            return int(cached)
        except (TypeError, ValueError):
            pass  # 缓存值异常时继续查库

    # 2. 回落数据库
    from core import database as db_module
    from sqlalchemy import select

    if db_module.async_session is None:
        await db_module.init_database()
    if db_module.async_session is None:
        return None

    # 延迟导入，避免 core 层在模块加载期依赖 app 层
    from app.common.model.user_model import User

    async with db_module.async_session() as session:
        result = await session.execute(
            select(User.token_version).where(User.id == user_id)
        )
        value = result.scalar_one_or_none()

    if value is None:
        return None

    # 3. 回填缓存（TTL=0 表示不缓存，始终以数据库为准）
    if TOKEN_VERSION_CACHE_TTL > 0:
        try:
            await set_cache(_cache_key(user_id), int(value), ttl=TOKEN_VERSION_CACHE_TTL)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"写入 token 版本缓存失败: {exc}")

    return int(value)


async def is_token_version_valid(user_id: int, token_version: Optional[int]) -> bool:
    """校验 Token 中的版本号是否仍然有效

    Args:
        user_id: Token 中的用户 ID
        token_version: Token payload 中的 ``ver``，缺失时按 0 处理（兼容存量 Token）

    Returns:
        bool: True 表示有效（或校验已关闭）
    """
    if not TOKEN_VERSION_CHECK:
        return True

    expected = 0 if token_version is None else token_version
    try:
        current = await get_current_token_version(user_id)
    except Exception as exc:  # noqa: BLE001 - 数据库不可用时不阻塞已登录用户
        logger.error(f"token 版本校验失败（放行当前请求）: {exc}")
        return True

    if current is None:
        # 用户已被删除
        return False

    return int(expected) == current


async def bump_token_version(db, user_id: int) -> bool:
    """使该用户的所有已签发 Token 立即失效

    在改密码、管理员禁用账号、强制下线等场景调用。
    使用 ``token_version = token_version + 1`` 的原子更新，并发调用不会丢计数。

    Args:
        db: 当前请求的 AsyncSession
        user_id: 用户 ID

    Returns:
        bool: 是否命中了用户记录
    """
    from sqlalchemy import update

    from app.common.model.user_model import User
    from core.cache import delete_cache

    result = await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(token_version=User.token_version + 1)
    )

    if not result.rowcount:
        return False

    # 立即清缓存，避免 TTL 窗口内旧 Token 仍被放行
    try:
        await delete_cache(_cache_key(user_id))
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"清除 token 版本缓存失败: {exc}")

    return True
