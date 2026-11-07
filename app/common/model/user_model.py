"""
ThinkPython 公共用户模型

本模块定义公共用户模型（User），是 admin、api 等多个模块共用的基础数据模型。

设计意图：
    在多模块项目中，多个模块可能需要操作同一张数据库表。
    例如：
    - admin 模块需要管理用户（增删改查）
    - api 模块需要获取用户信息、更新用户资料
    
    将用户模型放在 common 模块中，避免在不同模块中重复定义相同的模型类。

使用方式：
    在任何模块的服务层中引入公共模型：
        from app.common.model.user_model import User
        
        # 在 admin 模块中使用
        user = await db.get(User, 1)
        
        # 在 api 模块中使用
        users = await db.execute(select(User).where(User.status == 1))

表结构说明：
    user 表包含以下字段：
    - id: 主键ID（继承自BaseModel）
    - username: 用户名
    - password: 密码（哈希存储）
    - email: 邮箱
    - mobile: 手机号
    - nickname: 用户昵称
    - avatar: 头像URL
    - status: 状态（0=禁用，1=启用）
    - token_version: Token 版本号（改密/禁用时递增）
    - role: 角色标识（权限映射见 config/permissions.py）
    - created_at: 创建时间（继承自BaseModel）
    - updated_at: 更新时间（继承自BaseModel）
"""
from sqlalchemy import Column, String, Integer, SmallInteger
from core.base_model import BaseModel
from config.permissions import DEFAULT_ROLE


class User(BaseModel):
    """公共用户模型 - 供 admin、api 等多个模块共用
    
    本模型对应数据库中的 user 表，定义了用户相关的核心字段。
    任何需要操作用户数据的模块都应该引入此模型，而不是重新定义。
    
    Attributes:
        username: 用户名，唯一，最长50字符
        password: 密码（应存储哈希值，不存储明文）
        email: 邮箱地址，唯一，最长100字符
        mobile: 手机号，最长20字符
        nickname: 用户昵称，最长50字符
        avatar: 用户头像URL地址，最长255字符
        status: 用户状态，0表示禁用，1表示启用
    """
    
    # 指定数据库表名
    __tablename__ = "user"
    
    # 用户名，唯一标识，不允许为空
    username = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,  # 添加索引，加速查询
        comment="用户名",
    )
    
    # 密码字段，存储 bcrypt 等算法的哈希值
    password = Column(
        String(255),
        nullable=False,
        comment="密码（哈希值）",
    )
    
    # 邮箱地址，唯一标识
    email = Column(
        String(100),
        unique=True,
        nullable=False,
        comment="邮箱",
    )
    
    # 手机号
    mobile = Column(
        String(20),
        nullable=True,
        comment="手机号",
    )

    # 用户昵称
    nickname = Column(
        String(50),
        nullable=True,
        default=None,
        comment="用户昵称",
    )

    # 头像URL
    avatar = Column(
        String(255),
        nullable=True,
        default=None,
        comment="头像URL",
    )
    
    # 用户状态：0=禁用，1=启用
    status = Column(
        SmallInteger,
        default=1,
        comment="状态: 0=禁用, 1=启用",
    )

    # Token 版本号：每次改密 / 禁用账号时 +1，使该用户已签发的 Token 立即失效。
    # 签发时写入 JWT payload 的 ver 字段，校验时与此列比对。
    token_version = Column(
        Integer,
        default=0,
        nullable=False,
        server_default="0",
        comment="Token 版本号，改密/禁用时递增使旧 Token 失效",
    )

    # 角色：决定该用户拥有的权限集合，角色到权限的映射见 config/permissions.py
    # 签发 Token 时写入 payload 的 role；修改角色后需 bump token_version 使旧 Token 失效
    # 默认值取 DEFAULT_ROLE，保证与权限模块的口径一致
    role = Column(
        String(32),
        nullable=False,
        default=DEFAULT_ROLE,
        server_default=DEFAULT_ROLE,
        comment="角色标识，如 user / admin",
    )
