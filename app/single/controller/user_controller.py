"""
示例控制器 - User
"""
from typing import Optional
from pydantic import BaseModel
from core.base_controller import BaseController
from helpers.response import success_response, error_response


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
        async def get_users(page: int = 1, page_size: int = 10):
            # TODO: 调用Service层获取数据
            return self.success(data={
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
            })
        
        @self.router.get("/user/{user_id}", summary="获取用户详情")
        async def get_user(user_id: int):
            # TODO: 调用Service层获取数据
            return self.success(data={"id": user_id})
        
        @self.router.post("/user", summary="创建用户")
        async def create_user(request: UserCreateRequest):
            # TODO: 调用Service层创建数据
            return self.success(data={"id": 1, **request.dict()}, message="创建成功")
        
        @self.router.put("/user/{user_id}", summary="更新用户")
        async def update_user(user_id: int, request: UserUpdateRequest):
            # TODO: 调用Service层更新数据
            return self.success(data={"id": user_id}, message="更新成功")
        
        @self.router.delete("/user/{user_id}", summary="删除用户")
        async def delete_user(user_id: int):
            # TODO: 调用Service层删除数据
            return self.success(message="删除成功")
