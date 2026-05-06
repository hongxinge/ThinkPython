"""
助手函数 - 响应封装
"""
from typing import Any, Dict, List, Optional
from fastapi.responses import JSONResponse


def success_response(data: Any = None, message: str = "success", code: int = 200) -> Dict:
    """成功响应"""
    return {
        "code": code,
        "message": message,
        "data": data,
    }


def error_response(message: str = "error", code: int = 500, data: Any = None) -> Dict:
    """错误响应"""
    return {
        "code": code,
        "message": message,
        "data": data,
    }


def paginate_response(items: List[Any], total: int, page: int = 1, page_size: int = 10) -> Dict:
    """分页响应"""
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


def json_response(data: Dict, status_code: int = 200) -> JSONResponse:
    """JSON响应"""
    return JSONResponse(
        status_code=status_code,
        content=data,
    )
