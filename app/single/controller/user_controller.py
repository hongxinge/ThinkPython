"""
示例控制器 - User
"""
from typing import Optional
from pydantic import BaseModel
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from core.base_controller import BaseController
from core.database import get_db
from core.exception import NotFoundException
from app.single.service.user_service import UserService


class UserCreateRequest(BaseModel):
    """用户创建请求模型"""
    username: str
    email: str
    mobile: Optional[str] = None


class UserUpdateRequest(BaseModel):
    """用户更新请求模型"""
    username: Optional[str] = None
    email: Optional[str] = None
    mobile: Optional[str] = None


class UserController(BaseController):
    """用户控制器"""
    
    def __init__(self):
        super().__init__()
        self._setup_routes()
    
    def _setup_routes(self):
        @self.router.get("/user/list", summary="用户列表")
        async def get_users(page: int = 1, page_size: int = 10, db: AsyncSession = Depends(get_db)):
            """获取用户列表（分页）"""
            service = UserService(db)
            items, total = await service.get_all(page, page_size)
            return self.paginate(items, total, page, page_size)
        
        @self.router.get("/user/{user_id}", summary="获取用户详情")
        async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
            """获取用户详情"""
            service = UserService(db)
            user = await service.get_by_id(user_id)
            if not user:
                raise NotFoundException(f"用户 {user_id} 不存在")
            return self.success(data=user)
        
        @self.router.post("/user", summary="创建用户")
        async def create_user(request: UserCreateRequest, db: AsyncSession = Depends(get_db)):
            """创建用户"""
            service = UserService(db)
            user_data = request.model_dump(exclude_none=True)
            user = await service.create(user_data)
            return self.success(data=user, message="创建成功")
        
        @self.router.put("/user/{user_id}", summary="更新用户")
        async def update_user(user_id: int, request: UserUpdateRequest, db: AsyncSession = Depends(get_db)):
            """更新用户"""
            service = UserService(db)
            user_data = request.model_dump(exclude_unset=True)
            user = await service.update(user_id, user_data)
            if not user:
                raise NotFoundException(f"用户 {user_id} 不存在")
            return self.success(data=user, message="更新成功")
        
        @self.router.delete("/user/{user_id}", summary="删除用户")
        async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
            """删除用户"""
            service = UserService(db)
            success = await service.delete(user_id)
            if not success:
                raise NotFoundException(f"用户 {user_id} 不存在")
            return self.success(message="删除成功")
