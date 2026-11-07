"""单模块用户模型（兼容入口）。

历史版本在本文件中重复定义了 `User`，与 `app/common/model/user_model.py`
映射同一张 `user` 表，同一进程导入两者会触发：
    InvalidRequestError: Table 'user' is already defined for this MetaData instance.

现统一以 `app.common.model.user_model` 为唯一实体，本文件仅保留兼容导入路径：
    from app.single.model.user_model import User
"""
from app.common.model.user_model import User

__all__ = ["User"]
