"""
ThinkPython 示例用户模型 - 单模块模式

本文件定义了 User 数据模型，用于映射数据库中的 user 表。
User 模型继承自 BaseModel，自动获得以下通用字段：
- id: 自增主键
- created_at: 记录创建时间
- updated_at: 记录更新时间

字段说明：
- username: 用户名，唯一约束，不能为空
- email: 邮箱地址，唯一约束，不能为空
- mobile: 手机号，可选字段
- password: 密码，不能为空（存储前必须使用 bcrypt 或 md5 加密）
- status: 用户状态，0 表示禁用，1 表示启用，默认启用

使用示例:
    from app.single.model.user_model import User
    
    # 创建用户实例
    user = User(username="张三", email="zhangsan@example.com", password="encrypted_password")
    
    # 通过 SQLAlchemy 操作
    from core.database import get_db
    db = await anext(get_db())
    db.add(user)
    await db.commit()
"""
from sqlalchemy import Column, String, Integer
from core.base_model import BaseModel


class User(BaseModel):
    """用户数据模型 - 映射到数据库 user 表
    
    继承 BaseModel 后自动获得 id、created_at、updated_at 三个通用字段。
    此模型定义了用户表的结构和约束。
    
    数据库表名：user
    
    Attributes:
        username: 用户名，50 字符以内，唯一且必填
        email: 邮箱地址，100 字符以内，唯一且必填
        mobile: 手机号，20 字符以内，可选
        password: 密码，255 字符以内，必填（必须是加密后的密码）
        status: 用户状态，整数类型，0=禁用，1=启用，默认 1
    """
    
    # 指定数据库表名
    __tablename__ = "user"
    
    # 用户名，唯一索引，不允许为空
    username = Column(String(50), unique=True, nullable=False, comment="用户名")
    
    # 邮箱地址，唯一索引，不允许为空
    email = Column(String(100), unique=True, nullable=False, comment="邮箱")
    
    # 手机号，可选字段
    mobile = Column(String(20), comment="手机号")
    
    # 密码字段，必须存储加密后的值（使用 bcrypt/md5/sha256 等）
    password = Column(String(255), nullable=False, comment="密码")
    
    # 用户状态：0=禁用（不可登录），1=启用（正常），默认启用
    status = Column(Integer, default=1, comment="状态: 0禁用 1启用")
