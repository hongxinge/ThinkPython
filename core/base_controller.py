"""
ThinkPython 基础控制器

本模块定义了 BaseController 基类，所有业务控制器都应继承此类。
BaseController 提供了统一的响应格式和常用方法，包括：
- success(): 返回成功响应
- error(): 返回错误响应
- paginate(): 返回分页响应

控制器职责：
- 接收 HTTP 请求参数
- 调用 Service 层处理业务逻辑
- 返回格式化的响应数据

注意：控制器应尽量保持简洁，业务逻辑应放在 Service 层。

使用示例:
    from core.base_controller import BaseController
    
    class UserController(BaseController):
        def __init__(self):
            super().__init__()
            self._setup_routes()
        
        def _setup_routes(self):
            @self.router.get("/users")
            async def list_users():
                return self.success(data=[{"id": 1, "name": "张三"}])
"""
from fastapi import APIRouter, Request, Depends
from typing import Any, Dict, Optional


class BaseController:
    """基础控制器基类
    
    所有业务控制器都应继承此类，继承后自动获得：
    - 一个 APIRouter 实例（self.router），用于注册路由
    - success() / error() / paginate() 等响应辅助方法
    
    子类需要在 __init__ 中调用 super().__init__() 初始化 router，
    然后调用自定义的 _setup_routes() 方法注册路由。
    
    使用示例:
        class UserController(BaseController):
            def __init__(self):
                super().__init__()
                self._setup_routes()
            
            def _setup_routes(self):
                @self.router.get("/users")
                async def get_users():
                    return self.success(data={"users": []})
    """
    
    # FastAPI 路由实例，用于注册 HTTP 路由
    router: APIRouter = None
    
    def __init__(self):
        """初始化控制器，创建 APIRouter 实例"""
        self.router = APIRouter()
    
    def success(self, data: Any = None, message: str = "success", code: int = 200) -> Dict:
        """返回成功响应
        
        构造统一的 JSON 响应格式：{"code": 200, "message": "success", "data": ...}
        
        Args:
            data: 响应数据，可以是任意类型（字典、列表、对象等）
            message: 成功提示信息
            code: 业务状态码，默认 200
            
        Returns:
            Dict: 格式化的成功响应字典
            
        使用示例:
            return self.success(data={"id": 1, "name": "张三"})
            return self.success(message="操作成功")
            return self.success(data=users, code=200, message="获取成功")
        """
        return {
            "code": code,
            "message": message,
            "data": data,
        }
    
    def error(self, message: str = "error", code: int = 500, data: Any = None) -> Dict:
        """返回错误响应
        
        构造统一的 JSON 错误响应格式：{"code": 500, "message": "error", "data": ...}
        
        Args:
            message: 错误提示信息
            code: 业务错误码，默认 500
            data: 附加的错误详情数据（可选）
            
        Returns:
            Dict: 格式化的错误响应字典
            
        使用示例:
            return self.error(message="操作失败")
            return self.error(message="参数错误", code=400)
        """
        return {
            "code": code,
            "message": message,
            "data": data,
        }
    
    def paginate(self, items: list, total: int, page: int = 1, page_size: int = 10) -> Dict:
        """返回分页响应
        
        构造统一的分页数据响应格式，包含数据列表、总数、当前页码等信息。
        
        Args:
            items: 当前页的数据列表
            total: 数据总条数
            page: 当前页码，从 1 开始
            page_size: 每页条数
            
        Returns:
            Dict: 格式化的分页响应字典，结构如下：
                {
                    "code": 200,
                    "message": "success",
                    "data": {
                        "items": [...],       # 当前页数据
                        "total": 100,         # 总条数
                        "page": 1,            # 当前页码
                        "page_size": 10,      # 每页条数
                        "total_pages": 10     # 总页数
                    }
                }
                
        使用示例:
            items = [{"id": 1}, {"id": 2}]
            return self.paginate(items, total=100, page=1, page_size=10)
        """
        return {
            "code": 200,
            "message": "success",
            "data": {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                # 向上取整计算总页数，例如 101 条数据 / 每页 10 条 = 11 页
                "total_pages": (total + page_size - 1) // page_size,
            },
        }
