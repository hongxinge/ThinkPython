"""
ThinkPython 示例 API 产品控制器 - 多模块模式

本文件是多模块模式下 api 模块的示例控制器，展示对外 API 接口的设计。
此控制器提供产品列表查询和产品详情接口。

访问路径：
- GET /product/list              - 获取产品列表（支持按分类筛选和分页）
- GET /product/{product_id}      - 获取产品详情

架构说明：
在多模块模式下，api 模块的路由会自动加上 /api 前缀。
例如本控制器中的 /product/list 实际访问路径为 /api/product/list。

API 设计规范：
- 使用 RESTful 风格的 URL 设计
- 返回列表数据时使用分页
- 统一的响应格式：{"code": 200, "message": "success", "data": ...}
- 错误时使用标准 HTTP 状态码
"""
from core.base_controller import BaseController
from helpers.response import success_response


class ProductController(BaseController):
    """产品控制器示例 - 处理产品相关的 API 路由
    
    此控制器演示了面向外部 API 的接口设计：
    - 支持分类筛选
    - 支持分页查询
    - 返回统一格式的响应数据
    
    多模块模式下的路由规则：
    - api 模块的路由自动加上 /api 前缀
    - 例如 /product/list 实际路径为 /api/product/list
    
    访问示例：
        # 获取产品列表
        curl http://localhost:8000/api/product/list?category_id=1&page=1&page_size=10
        
        # 获取产品详情
        curl http://localhost:8000/api/product/1
    """
    
    def __init__(self):
        # 调用父类构造函数，初始化 self.router
        super().__init__()
        # 注册路由
        self._setup_routes()
    
    def _setup_routes(self):
        """初始化路由配置"""
        
        # 获取产品列表接口
        @self.router.get("/product/list", summary="产品列表")
        async def get_products(category_id: int = 0, page: int = 1, page_size: int = 10):
            """获取产品列表，支持按分类筛选和分页查询
            
            Args:
                category_id: 分类 ID，0 表示查询所有分类
                page: 当前页码，从 1 开始
                page_size: 每页条数
                
            Returns:
                Dict: 产品列表响应，包含 items 和 total
            """
            # TODO: 调用 Service 层获取产品列表
            # service = ProductService(db)
            # items, total = await service.get_by_category(category_id, page, page_size)
            # return self.paginate(items, total, page, page_size)
            
            return self.success(data={
                "items": [],
                "total": 0,
            })
        
        # 获取产品详情接口
        @self.router.get("/product/{product_id}", summary="产品详情")
        async def get_product(product_id: int):
            """根据产品 ID 获取产品详细信息
            
            Args:
                product_id: 产品 ID，从 URL 路径参数中获取
                
            Returns:
                Dict: 产品详细信息
                
            Raises:
                NotFoundException: 当产品不存在时抛出 404 异常
            """
            # TODO: 调用 Service 层获取产品详情
            # service = ProductService(db)
            # product = await service.get_by_id(product_id)
            # if not product:
            #     raise NotFoundException(f"产品 {product_id} 不存在")
            # return self.success(data=product)
            
            return self.success(data={"id": product_id, "name": "示例产品"})
