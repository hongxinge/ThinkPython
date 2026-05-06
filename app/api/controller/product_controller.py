"""
API模块 - 示例控制器
"""
from core.base_controller import BaseController
from helpers.response import success_response


class ProductController(BaseController):
    """产品控制器示例"""
    
    def __init__(self):
        super().__init__()
        self._setup_routes()
    
    def _setup_routes(self):
        @self.router.get("/product/list", summary="产品列表")
        async def get_products(category_id: int = 0, page: int = 1, page_size: int = 10):
            # TODO: 调用Service层获取产品列表
            return self.success(data={
                "items": [],
                "total": 0,
            })
        
        @self.router.get("/product/{product_id}", summary="产品详情")
        async def get_product(product_id: int):
            # TODO: 调用Service层获取产品详情
            return self.success(data={"id": product_id, "name": "示例产品"})
