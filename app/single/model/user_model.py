"""
示例模型 - User
"""
from sqlalchemy import Column, String, Integer
from core.base_model import BaseModel


class User(BaseModel):
    """用户模型"""
    
    __tablename__ = "user"
    
    username = Column(String(50), unique=True, nullable=False, comment="用户名")
    email = Column(String(100), unique=True, nullable=False, comment="邮箱")
    mobile = Column(String(20), comment="手机号")
    password = Column(String(255), nullable=False, comment="密码")
    status = Column(Integer, default=1, comment="状态: 0禁用 1启用")
