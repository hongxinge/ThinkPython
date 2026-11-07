"""统一响应契约的 Pydantic 模型

框架的响应体一直是 ``{code, message, data, request_id}``，但此前所有路由都写
``response_model=dict``，导致 OpenAPI 里只有 ``additionalProperties: true`` ——
客户端 SDK 拿不到 ``data`` 的字段信息，类型只能是 ``unknown``。

这里用**泛型模型**把这个结构显式表达出来，控制器即可声明::

    from core.schema import ApiResponse, PageData

    @self.router.post("/user/login", response_model=ApiResponse[LoginData])
    async def login(...):
        return self.success(data={"access_token": ...})

FastAPI 会据此生成精确 schema，``think.py make-client`` 也就能生成强类型客户端。
不声明 ``response_model`` 的接口仍然可用，只是类型退化为 ``unknown``——
升级是渐进的，不强制一次性改完。

一个必须注意的行为：声明 ``response_model`` 后，FastAPI 会**按模型过滤字段**。
返回 dict 中模型未定义的键会被丢弃。这是有意为之的契约收敛，但如果发现
某个字段"接口明明返回了、客户端却收不到"，先检查模型定义。
"""

from __future__ import annotations

from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一响应包装

    Attributes:
        code: 业务状态码，200 表示成功。客户端判断成功请用 ``code == 200``，
            不要只看 HTTP 状态（``ERROR_HTTP_MODE=legacy`` 下错误也是 200）
        message: 提示信息，可直接展示给用户
        data: 业务数据，具体类型由泛型参数决定
        request_id: 请求追踪 ID，反馈问题时提供给后端
    """

    model_config = ConfigDict(populate_by_name=True)

    code: int = Field(default=200, description="业务状态码，200 表示成功")
    message: str = Field(default="success", description="提示信息")
    data: Optional[T] = Field(default=None, description="业务数据")
    request_id: Optional[str] = Field(default=None, description="请求追踪 ID")


class PageData(BaseModel, Generic[T]):
    """分页数据结构，配合 ``ApiResponse[PageData[T]]`` 使用

    与 ``BaseController.paginate()`` 的返回完全对应，可直接套用。
    """

    items: List[T] = Field(default_factory=list, description="当前页数据")
    total: int = Field(default=0, description="总记录数")
    page: int = Field(default=1, description="当前页码，从 1 开始")
    page_size: int = Field(default=10, description="每页条数")
    total_pages: int = Field(default=0, description="总页数")


class EmptyData(BaseModel):
    """无数据返回时的占位模型

    用于 ``ApiResponse[EmptyData]``，替代 ``dict``，让客户端拿到确定的空对象类型
    而不是 ``unknown``。
    """

    model_config = ConfigDict(extra="allow")


__all__ = ["ApiResponse", "PageData", "EmptyData"]
