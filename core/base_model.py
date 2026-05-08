"""
ThinkPython 基础模型

本模块定义了 BaseModel 基类，所有 ORM 数据模型都应继承此类。
BaseModel 提供了所有数据表通用的字段：
- id: 自增主键
- created_at: 记录创建时间（自动填充）
- updated_at: 记录更新时间（自动更新）

继承 BaseModel 的模型会自动：
- 注册到 SQLAlchemy 的 Base.metadata 中，方便统一创建表
- 拥有统一的 id、created_at、updated_at 字段

使用示例:
    from core.base_model import BaseModel
    from sqlalchemy import Column, String
    
    class User(BaseModel):
        __tablename__ = "users"
        
        username = Column(String(50), nullable=False, comment="用户名")
        email = Column(String(100), nullable=False, comment="邮箱")
"""
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime
from core.database import Base


class BaseModel(Base):
    """基础模型基类 - 所有数据模型都应继承此类
    
    这是一个抽象基类（__abstract__ = True），不会单独映射到数据库表。
    继承它的子类会自动获得以下通用字段：
    - id: 自增主键，Integer 类型
    - created_at: 创建时间，插入时自动设置为当前时间
    - updated_at: 更新时间，插入时和每次更新时自动设置为当前时间
    
    注意：
    - 子类必须设置 __tablename__ 属性来指定数据库表名
    - Base 的 __abstract__ = True 确保 BaseModel 本身不会创建数据表
    
    使用示例:
        from core.base_model import BaseModel
        from sqlalchemy import Column, String
        
        class Product(BaseModel):
            __tablename__ = "products"
            
            name = Column(String(100), nullable=False, comment="产品名称")
            price = Column(Integer, comment="价格（单位：分）")
    """
    
    # 标记为抽象类，SQLAlchemy 不会为 BaseModel 创建数据表
    __abstract__ = True
    
    # 自增主键 ID，所有继承模型的统一主键字段
    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    
    # 记录创建时间，插入时自动设置为当前时间
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    
    # 记录更新时间，插入时设置为当前时间，每次更新记录时自动更新
    # onupdate 参数确保每次 UPDATE 操作都会自动刷新此字段
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
