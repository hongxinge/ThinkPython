"""
ThinkPython 响应封装助手函数

本模块提供统一的 HTTP 响应格式封装函数，包括：
- success_response(): 成功响应
- error_response(): 错误响应
- paginate_response(): 分页响应
- json_response(): 返回 FastAPI JSONResponse 对象

与 core/base_controller.py 中的响应方法不同，
这些是独立函数，可以在任何地方使用，不限于控制器类中。

标准响应格式:
    {
        "code": 200,        # 业务状态码
        "message": "success",  # 提示信息
        "data": ...         # 响应数据
    }

使用示例:
    from helpers.response import success_response, error_response
    
    @router.get("/users")
    async def get_users():
        return success_response(data=[{"id": 1}])
    
    @router.post("/users")
    async def create_user():
        if not valid:
            return error_response(message="创建失败")
"""
from typing import Any, Dict, List, Optional
from fastapi.responses import JSONResponse


def success_response(data: Any = None, message: str = "success", code: int = 200) -> Dict:
    """构造成功响应字典
    
    Args:
        data: 响应数据，可以是任意类型
        message: 成功提示信息
        code: 业务状态码，默认 200
        
    Returns:
        Dict: 标准格式的成功响应字典
        
    使用示例:
        success_response(data={"id": 1})
        # {"code": 200, "message": "success", "data": {"id": 1}}
    """
    return {
        "code": code,
        "message": message,
        "data": data,
    }


def error_response(message: str = "error", code: int = 500, data: Any = None) -> Dict:
    """构造错误响应字典
    
    Args:
        message: 错误提示信息
        code: 业务错误码，默认 500
        data: 附加的错误详情数据（可选）
        
    Returns:
        Dict: 标准格式的错误响应字典
        
    使用示例:
        error_response(message="操作失败")
        # {"code": 500, "message": "操作失败", "data": None}
    """
    return {
        "code": code,
        "message": message,
        "data": data,
    }


def paginate_response(items: List[Any], total: int, page: int = 1, page_size: int = 10) -> Dict:
    """构造分页响应字典
    
    Args:
        items: 当前页的数据列表
        total: 数据总条数
        page: 当前页码，从 1 开始
        page_size: 每页条数
        
    Returns:
        Dict: 标准格式的分页响应字典
        
    使用示例:
        paginate_response(items=[{"id": 1}], total=100, page=1, page_size=10)
        # {
        #     "code": 200,
        #     "message": "success",
        #     "data": {
        #         "items": [...],
        #         "total": 100,
        #         "page": 1,
        #         "page_size": 10,
        #         "total_pages": 10
        #     }
        # }
    """
    return {
        "code": 200,
        "message": "success",
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,  # 向上取整计算总页数
        },
    }


def json_response(data: Dict, status_code: int = 200) -> JSONResponse:
    """构造 FastAPI JSONResponse 对象
    
    当需要直接控制 HTTP 状态码时使用此函数，
    例如返回 201 Created、400 Bad Request 等。
    
    Args:
        data: 响应内容字典
        status_code: HTTP 状态码，默认 200
        
    Returns:
        JSONResponse: FastAPI 的 JSON 响应对象
        
    使用示例:
        # 返回 201 Created
        json_response({"code": 201, "message": "创建成功"}, status_code=201)
        
        # 返回 400 Bad Request
        json_response({"code": 400, "message": "参数错误"}, status_code=400)
    """
    return JSONResponse(
        status_code=status_code,
        content=data,
    )
