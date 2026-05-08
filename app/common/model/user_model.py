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
    - avatar: 头像URL
    - status: 状态（0=禁用，1=启用）
    - created_at: 创建时间（继承自BaseModel）
    - updated_at: 更新时间（继承自BaseModel）
"""
from sqlalchemy import Column, String, Integer, SmallInteger
from core.base_model import BaseModel


class User(BaseModel):
    """公共用户模型 - 供 admin、api 等多个模块共用
    
    本模型对应数据库中的 user 表，定义了用户相关的核心字段。
    任何需要操作用户数据的模块都应该引入此模型，而不是重新定义。
    
    Attributes:
        username: 用户名，唯一，最长50字符
        password: 密码（应存储哈希值，不存储明文）
        email: 邮箱地址，唯一，最长100字符
        mobile: 手机号，最长20字符
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
