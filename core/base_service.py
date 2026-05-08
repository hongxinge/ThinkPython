"""
ThinkPython 基础服务层

本模块定义了 BaseService 基类，所有业务服务类都应继承此类。
BaseService 提供了通用的 CRUD（增删改查）操作方法，包括：
- get_by_id(): 根据 ID 获取单条记录
- get_all(): 获取分页数据列表
- create(): 创建新记录
- update(): 更新记录
- delete(): 删除记录

服务层职责：
- 封装数据库操作逻辑
- 处理业务规则和验证
- 为控制器层提供数据服务

架构分层：Controller -> Service -> Model
- Controller 负责接收请求和返回响应
- Service 负责业务逻辑和数据操作
- Model 负责定义数据结构

使用示例:
    from core.base_service import BaseService
    
    class UserService(BaseService):
        def __init__(self, db: AsyncSession):
            super().__init__(db)
            self.model_class = User  # 关联到 User 模型
        
        # 继承后可以直接使用 self.get_by_id(), self.create() 等方法
"""
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import DeclarativeBase
from core.exception import AppException


class BaseService:
    """基础服务类 - 提供通用的 CRUD 操作
    
    子类通过设置 model_class 属性来关联对应的 ORM 模型，
    然后即可使用继承的 CRUD 方法操作数据库。
    
    使用示例:
        class UserService(BaseService):
            def __init__(self, db: AsyncSession):
                super().__init__(db)
                self.model_class = User
            
            # 继承的方法可以直接使用
            user = await self.get_by_id(1)
            users, total = await self.get_all(page=1, page_size=10)
    """
    
    # 关联的 ORM 模型类，子类必须设置此属性
    model_class: DeclarativeBase = None
    
    def __init__(self, db: AsyncSession):
        """初始化服务类，接收数据库会话
        
        Args:
            db: SQLAlchemy 异步数据库会话，通过 FastAPI 依赖注入传入
            
        Raises:
            AppException: 当 db 为 None 时抛出，表示数据库连接未初始化
        """
        if db is None:
            raise AppException("数据库连接未初始化", code=500)
        self.db = db
    
    async def get_by_id(self, id: int) -> Optional[DeclarativeBase]:
        """根据主键 ID 获取单条记录
        
        Args:
            id: 记录的主键 ID
            
        Returns:
            Optional[DeclarativeBase]: 模型实例，记录不存在时返回 None
            
        使用示例:
            user = await self.get_by_id(1)
            if user:
                print(user.username)
        """
        return await self.db.get(self.model_class, id)
    
    async def get_all(self, page: int = 1, page_size: int = 10) -> Tuple[List[DeclarativeBase], int]:
        """获取所有记录（分页）
        
        使用聚合查询优化性能：先用 COUNT(*) 获取总数，再分页查询数据。
        避免了一次性加载全部数据到内存。
        
        Args:
            page: 当前页码，从 1 开始，小于 1 时自动修正为 1
            page_size: 每页条数，范围 1-100，超出范围时自动修正为 10
            
        Returns:
            Tuple[List[DeclarativeBase], int]: (数据列表, 总记录数)
            
        使用示例:
            items, total = await self.get_all(page=1, page_size=10)
            print(f"共 {total} 条记录，当前页 {len(items)} 条")
        """
        # 验证并修正分页参数
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 10
        
        # 使用聚合函数 COUNT(*) 查询总数，避免加载所有数据
        count_stmt = select(func.count()).select_from(self.model_class)
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0
        
        # 计算偏移量并分页查询数据
        offset = (page - 1) * page_size
        stmt = select(self.model_class).offset(offset).limit(page_size)
        result = await self.db.execute(stmt)
        items = result.scalars().all()
        
        return items, total
    
    async def create(self, data: Dict[str, Any]) -> DeclarativeBase:
        """创建新记录
        
        Args:
            data: 包含字段名和值的字典，用于构造新模型实例
            
        Returns:
            DeclarativeBase: 创建后的模型实例（已刷新，包含自增 ID 等数据库生成的值）
            
        使用示例:
            user = await self.create({"username": "张三", "email": "zhangsan@example.com"})
            print(user.id)  # 自动生成的主键 ID
        """
        # 使用字典解包创建模型实例
        instance = self.model_class(**data)
        self.db.add(instance)
        # flush() 将变更同步到数据库但不提交，用于获取自增 ID
        await self.db.flush()
        # refresh() 从数据库刷新实例属性，确保获取最新的数据库生成值
        await self.db.refresh(instance)
        return instance
    
    async def update(self, id: int, data: Dict[str, Any]) -> Optional[DeclarativeBase]:
        """更新指定 ID 的记录
        
        Args:
            id: 要更新的记录主键 ID
            data: 包含要更新字段名和新值的字典
            
        Returns:
            Optional[DeclarativeBase]: 更新后的模型实例，记录不存在时返回 None
            
        使用示例:
            user = await self.update(1, {"username": "新用户名"})
            if user:
                print("更新成功")
        """
        # 先查找记录是否存在
        instance = await self.get_by_id(id)
        if instance:
            # 使用 setattr 动态设置字段值
            for key, value in data.items():
                setattr(instance, key, value)
            await self.db.flush()
            await self.db.refresh(instance)
        return instance
    
    async def delete(self, id: int) -> bool:
        """删除指定 ID 的记录
        
        Args:
            id: 要删除的记录主键 ID
            
        Returns:
            bool: 删除成功返回 True，记录不存在返回 False
            
        使用示例:
            success = await self.delete(1)
            if success:
                print("删除成功")
        """
        # 先查找记录是否存在
        instance = await self.get_by_id(id)
        if instance:
            await self.db.delete(instance)
            await self.db.flush()
            return True
        return False
