"""角色与权限定义（RBAC）

定位说明：
    ThinkPython 面向客户端 API，权限模型刻意保持「够用且可读」——
    不引入 role / permission / user_role / role_permission 五张表，
    而是用「用户持有一个角色 + 角色在代码中声明权限集」的方式。

    对绝大多数 To C App 与中小型后台，这套模型已经足够：
    - To C 场景通常只有「普通用户 / 管理员」两类；
    - 需要更细粒度时，再在业务层用资源归属判断（如「只能改自己的订单」），
      那属于数据级权限，不应塞进接口级 RBAC。

扩展方式：
    直接修改本文件的 ``ROLE_PERMISSIONS`` 即可，无需改表结构。
    角色名写入 ``user.role`` 字段，签发 Token 时写入 payload 的 ``role``。

权限标识约定：
    ``<资源>:<动作>``，如 ``user:read``、``order:write``。
    支持通配：
    - ``*``          拥有全部权限（超级管理员）
    - ``order:*``    拥有 order 资源的全部动作

注意（重要）：
    角色的权威来源是 Token。修改用户角色后，必须同时调用
    ``core.token_state.bump_token_version()`` 使其旧 Token 失效，
    否则旧 Token 里的 role 会一直沿用到过期。
"""
import os
from typing import Dict, Set

# 默认角色：新注册用户与未显式指定角色的用户
DEFAULT_ROLE = os.getenv("DEFAULT_ROLE", "user")

# 角色 -> 权限集合
# 生产项目按业务补充，例如运营 "operator": {"order:read", "user:read"}
ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    # 超级管理员：拥有全部权限
    "admin": {"*"},
    # 普通用户：只能读写自己的资料
    "user": {"profile:read", "profile:write"},
}


def get_role_permissions(role: str) -> Set[str]:
    """获取角色对应的权限集合

    Args:
        role: 角色名

    Returns:
        Set[str]: 权限集合；未知角色返回空集合（安全默认：无任何权限）
    """
    if not role:
        return set()
    return set(ROLE_PERMISSIONS.get(role, set()))


def has_permission(role: str, permission: str) -> bool:
    """判断角色是否拥有指定权限

    匹配顺序：全局通配 ``*`` → 精确匹配 → 资源级通配 ``资源:*``

    Args:
        role: 角色名
        permission: 需要的权限标识，如 ``user:read``

    Returns:
        bool: 有权限返回 True

    使用示例:
        >>> has_permission("admin", "order:delete")
        True
        >>> has_permission("user", "order:delete")
        False
    """
    if not role or not permission:
        return False

    granted = get_role_permissions(role)
    if not granted:
        return False

    if "*" in granted or permission in granted:
        return True

    # 资源级通配：order:* 覆盖 order:read / order:write
    if ":" in permission:
        resource = permission.split(":", 1)[0]
        if f"{resource}:*" in granted:
            return True

    return False


def has_any_permission(role: str, permissions) -> bool:
    """判断角色是否拥有其中任意一个权限（OR 语义）

    Args:
        role: 角色名
        permissions: 权限标识的可迭代对象

    Returns:
        bool: 命中任意一个即返回 True；空列表视为「无需权限」
    """
    required = list(permissions or [])
    if not required:
        return True
    return any(has_permission(role, perm) for perm in required)


def has_all_permissions(role: str, permissions) -> bool:
    """判断角色是否拥有全部权限（AND 语义）

    Args:
        role: 角色名
        permissions: 权限标识的可迭代对象

    Returns:
        bool: 全部命中才返回 True；空列表视为「无需权限」
    """
    required = list(permissions or [])
    if not required:
        return True
    return all(has_permission(role, perm) for perm in required)
