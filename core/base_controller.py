"""
基础控制器
"""
from fastapi import APIRouter, Request, Depends
from typing import Any, Dict, Optional


class BaseController:
    """基础控制器"""
    
    router: APIRouter = None
    
    def __init__(self):
        self.router = APIRouter()
    
    def success(self, data: Any = None, message: str = "success", code: int = 200) -> Dict:
        """返回成功响应"""
        return {
            "code": code,
            "message": message,
            "data": data,
        }
    
    def error(self, message: str = "error", code: int = 500, data: Any = None) -> Dict:
        """返回错误响应"""
        return {
            "code": code,
            "message": message,
            "data": data,
        }
    
    def paginate(self, items: list, total: int, page: int = 1, page_size: int = 10) -> Dict:
        """返回分页响应"""
        return {
            "code": 200,
            "message": "success",
            "data": {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size,
            },
        }
