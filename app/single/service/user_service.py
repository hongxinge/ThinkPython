"""
ThinkPython 示例用户服务 - 单模块模式

本文件定义了 UserService 服务类，封装与用户相关的业务逻辑。
服务层是 Controller 和 Model 之间的中间层，职责包括：
- 调用 BaseModel 的 CRUD 方法进行数据库操作
- 处理业务规则和数据验证
- 为 Controller 提供封装好的数据接口

架构分层：
Controller（接收请求/返回响应）
    ↓
Service（业务逻辑/数据操作）
    ↓
Model（数据结构定义）

使用示例:
    from app.single.service.user_service import UserService
    from core.database import get_db
    
    # 在控制器中使用
    db = await anext(get_db())
    service = UserService(db)
    
    # 查询用户
    user = await service.get_by_id(1)
    users, total = await service.get_all(page=1, page_size=10)
    
    # 创建用户
    user = await service.create({"username": "张三", "email": "zhangsan@example.com"})
"""
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from core.base_service import BaseService


class UserService(BaseService):
    """用户服务类 - 封装用户相关的业务逻辑
    
    继承 BaseService 后自动获得以下 CRUD 方法：
    - get_by_id(): 根据 ID 获取用户
    - get_all(): 获取用户列表（分页）
    - create(): 创建用户
    - update(): 更新用户
    - delete(): 删除用户
    
    可以在此基础上添加自定义的业务方法。
    
    使用示例:
        service = UserService(db)
        user = await service.get_by_id(1)
        exists = await service.check_user_exists("zhangsan")
    """
    
    def __init__(self, db: AsyncSession):
        """初始化用户服务
        
        Args:
            db: SQLAlchemy 异步数据库会话，通过 FastAPI 依赖注入传入
        """
        super().__init__(db)
        # self.model_class = User  # 如果需要直接操作模型，取消注释并导入 User 模型
    
    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """根据用户名获取用户信息
        
        Args:
            username: 要查询的用户名
            
        Returns:
            Optional[Dict[str, Any]]: 用户信息字典，用户不存在时返回 None
            
        使用示例:
            user = await self.get_user_by_username("zhangsan")
            if user:
                print(user["id"])
        """
        # TODO: 实现具体业务逻辑
        # 示例实现：
        # from sqlalchemy import select
        # from app.single.model.user_model import User
        # stmt = select(User).where(User.username == username)
        # result = await self.db.execute(stmt)
        # return result.scalar_one_or_none()
        return None
    
    async def check_user_exists(self, username: str) -> bool:
        """检查指定用户名的用户是否已存在
        
        常用于注册时检查用户名是否重复。
        
        Args:
            username: 要检查的用户名
            
        Returns:
            bool: 用户存在返回 True，否则返回 False
            
        使用示例:
            if await self.check_user_exists("zhangsan"):
                raise Exception("用户名已存在")
        """
        user = await self.get_user_by_username(username)
        return user is not None
