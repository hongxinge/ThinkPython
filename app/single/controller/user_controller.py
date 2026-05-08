"""
ThinkPython 示例用户控制器 - 单模块模式

本文件是 ThinkPython 框架的示例控制器，展示完整的 CRUD（增删改查）操作。
此控制器提供用户的列表查询、详情查看、创建、更新和删除功能。

访问路径：
- GET  /user/list        - 获取用户列表（分页）
- GET  /user/{user_id}   - 获取用户详情
- POST /user             - 创建用户
- PUT  /user/{user_id}   - 更新用户
- DELETE /user/{user_id} - 删除用户

架构分层：
Controller -> Service -> Model
- Controller: 接收请求参数，调用 Service，返回响应
- Service: 处理业务逻辑，操作数据库
- Model: 定义数据结构

请求验证：
使用 Pydantic 模型（UserCreateRequest/UserUpdateRequest）进行请求体验证，
FastAPI 会自动验证请求参数并返回 422 错误。
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
    """用户创建请求体模型 - 用于 Pydantic 参数验证
    
    当客户端发送 POST /user 请求时，FastAPI 会自动验证请求体是否符合此模型定义。
    
    Attributes:
        username: 用户名，必填字段
        email: 邮箱地址，必填字段
        mobile: 手机号，可选字段
    """
    username: str  # 用户名，必填
    email: str  # 邮箱，必填
    mobile: Optional[str] = None  # 手机号，可选


class UserUpdateRequest(BaseModel):
    """用户更新请求体模型 - 用于 Pydantic 参数验证
    
    所有字段都是可选的，客户端只需要传递需要更新的字段。
    使用 exclude_unset=True 过滤掉未传递的字段。
    
    Attributes:
        username: 用户名，可选
        email: 邮箱地址，可选
        mobile: 手机号，可选
    """
    username: Optional[str] = None  # 用户名，可选
    email: Optional[str] = None  # 邮箱，可选
    mobile: Optional[str] = None  # 手机号，可选


class UserController(BaseController):
    """用户控制器 - 处理用户相关的 CRUD 路由
    
    此控制器演示了完整的 RESTful API 设计：
    - GET 获取数据
    - POST 创建数据
    - PUT 更新数据
    - DELETE 删除数据
    
    依赖注入：
    使用 FastAPI 的 Depends(get_db) 自动注入数据库会话，
    请求结束后自动提交/回滚和关闭连接。
    
    访问示例：
        # 获取用户列表
        curl http://localhost:8000/user/list?page=1&page_size=10
        
        # 获取用户详情
        curl http://localhost:8000/user/1
        
        # 创建用户
        curl -X POST http://localhost:8000/user \
             -H "Content-Type: application/json" \
             -d '{"username": "张三", "email": "zhangsan@example.com"}'
    """
    
    def __init__(self):
        # 调用父类构造函数，初始化 self.router
        super().__init__()
        # 注册路由
        self._setup_routes()
    
    def _setup_routes(self):
        """初始化路由配置"""
        
        # 获取用户列表（分页）
        @self.router.get("/user/list", summary="用户列表")
        async def get_users(page: int = 1, page_size: int = 10, db: AsyncSession = Depends(get_db)):
            """获取用户列表，支持分页查询
            
            Args:
                page: 当前页码，从 1 开始
                page_size: 每页条数
                db: 数据库会话，由 FastAPI 依赖注入提供
                
            Returns:
                Dict: 分页响应，包含 items、total、page、page_size、total_pages
            """
            # 实例化用户服务，传入数据库会话
            service = UserService(db)
            # 调用服务层的分页查询方法
            items, total = await service.get_all(page, page_size)
            # 使用 BaseController 的分页响应方法格式化返回数据
            return self.paginate(items, total, page, page_size)
        
        # 获取用户详情
        @self.router.get("/user/{user_id}", summary="获取用户详情")
        async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
            """根据用户 ID 获取用户详细信息
            
            Args:
                user_id: 用户 ID，从 URL 路径参数中获取
                db: 数据库会话
                
            Returns:
                Dict: 用户详细信息
                
            Raises:
                NotFoundException: 当用户不存在时抛出 404 异常
            """
            service = UserService(db)
            user = await service.get_by_id(user_id)
            if not user:
                raise NotFoundException(f"用户 {user_id} 不存在")
            return self.success(data=user)
        
        # 创建用户
        @self.router.post("/user", summary="创建用户")
        async def create_user(request: UserCreateRequest, db: AsyncSession = Depends(get_db)):
            """创建新用户
            
            Args:
                request: 用户创建请求体，由 Pydantic 自动验证
                db: 数据库会话
                
            Returns:
                Dict: 创建成功后的用户信息
            """
            service = UserService(db)
            # model_dump(exclude_none=True) 将 Pydantic 模型转为字典，过滤掉 None 值
            user_data = request.model_dump(exclude_none=True)
            user = await service.create(user_data)
            return self.success(data=user, message="创建成功")
        
        # 更新用户
        @self.router.put("/user/{user_id}", summary="更新用户")
        async def update_user(user_id: int, request: UserUpdateRequest, db: AsyncSession = Depends(get_db)):
            """更新指定用户的信息
            
            Args:
                user_id: 要更新的用户 ID
                request: 用户更新请求体，只包含需要更新的字段
                db: 数据库会话
                
            Returns:
                Dict: 更新后的用户信息
                
            Raises:
                NotFoundException: 当用户不存在时抛出 404 异常
            """
            service = UserService(db)
            # exclude_unset=True 只包含客户端实际传递的字段，未传递的字段不会被覆盖
            user_data = request.model_dump(exclude_unset=True)
            user = await service.update(user_id, user_data)
            if not user:
                raise NotFoundException(f"用户 {user_id} 不存在")
            return self.success(data=user, message="更新成功")
        
        # 删除用户
        @self.router.delete("/user/{user_id}", summary="删除用户")
        async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
            """删除指定用户
            
            Args:
                user_id: 要删除的用户 ID
                db: 数据库会话
                
            Returns:
                Dict: 删除成功提示
                
            Raises:
                NotFoundException: 当用户不存在时抛出 404 异常
            """
            service = UserService(db)
            success = await service.delete(user_id)
            if not success:
                raise NotFoundException(f"用户 {user_id} 不存在")
            return self.success(message="删除成功")
