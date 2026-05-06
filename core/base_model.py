"""
基础模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime
from core.database import Base


class BaseModel(Base):
    """基础模型类"""
    
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
