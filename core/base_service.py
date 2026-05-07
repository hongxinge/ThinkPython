"""
基础服务层
"""
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import DeclarativeBase
from core.exception import AppException


class BaseService:
    """基础服务类"""
    
    model_class: DeclarativeBase = None
    
    def __init__(self, db: AsyncSession):
        if db is None:
            raise AppException("数据库连接未初始化", code=500)
        self.db = db
    
    async def get_by_id(self, id: int) -> Optional[DeclarativeBase]:
        """根据ID获取记录"""
        return await self.db.get(self.model_class, id)
    
    async def get_all(self, page: int = 1, page_size: int = 10) -> Tuple[List[DeclarativeBase], int]:
        """获取所有记录 (分页) - 使用聚合查询优化性能"""
        # 验证分页参数
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 10
        
        # 使用聚合函数COUNT(*)查询总数，避免加载所有数据
        count_stmt = select(func.count()).select_from(self.model_class)
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0
        
        # 分页查询数据
        offset = (page - 1) * page_size
        stmt = select(self.model_class).offset(offset).limit(page_size)
        result = await self.db.execute(stmt)
        items = result.scalars().all()
        
        return items, total
    
    async def create(self, data: Dict[str, Any]) -> DeclarativeBase:
        """创建记录"""
        instance = self.model_class(**data)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance
    
    async def update(self, id: int, data: Dict[str, Any]) -> Optional[DeclarativeBase]:
        """更新记录"""
        instance = await self.get_by_id(id)
        if instance:
            for key, value in data.items():
                setattr(instance, key, value)
            await self.db.flush()
            await self.db.refresh(instance)
        return instance
    
    async def delete(self, id: int) -> bool:
        """删除记录"""
        instance = await self.get_by_id(id)
        if instance:
            await self.db.delete(instance)
            await self.db.flush()
            return True
        return False
