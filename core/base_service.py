"""
基础服务层
"""
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import DeclarativeBase


class BaseService:
    """基础服务类"""
    
    model_class: DeclarativeBase = None
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, id: int) -> Optional[DeclarativeBase]:
        """根据ID获取记录"""
        return await self.db.get(self.model_class, id)
    
    async def get_all(self, page: int = 1, page_size: int = 10) -> tuple:
        """获取所有记录 (分页)"""
        offset = (page - 1) * page_size
        stmt = select(self.model_class).offset(offset).limit(page_size)
        result = await self.db.execute(stmt)
        items = result.scalars().all()
        
        count_stmt = select(self.model_class)
        count_result = await self.db.execute(count_stmt)
        total = len(count_result.scalars().all())
        
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
