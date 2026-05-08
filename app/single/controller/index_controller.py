"""
ThinkPython 示例首页控制器 - 单模块模式

本文件是 ThinkPython 框架的示例控制器，展示如何在单模块模式下创建路由。
此控制器提供基本的欢迎页面和系统信息接口。

访问路径：
- GET /          - 欢迎页面
- GET /info      - 系统信息（返回应用名称、版本号、调试模式）

架构说明：
在单模块模式下，所有控制器都放在 app/single/controller/ 目录下，
路由注册时不添加模块前缀，直接注册到根路径。
"""
from core.base_controller import BaseController
from helpers.response import success_response


class IndexController(BaseController):
    """首页控制器 - 处理首页相关的路由
    
    此控制器演示了 BaseController 的基本用法：
    - 继承 BaseController 获取 success/error/paginate 方法
    - 使用 self.router 注册路由
    - 通过 _setup_routes() 组织路由定义
    
    访问示例：
        curl http://localhost:8000/
        # 返回: {"code": 200, "message": "success", "data": "Welcome to ThinkPython!"}
    """
    
    def __init__(self):
        # 调用父类构造函数，初始化 self.router
        super().__init__()
        # 注册路由
        self._setup_routes()
    
    def _setup_routes(self):
        """初始化路由配置
        
        在此方法中定义所有路由，使用 FastAPI 的路由装饰器。
        所有路由会自动注册到 self.router，由路由系统统一挂载。
        """
        
        # 欢迎页面 - 返回欢迎信息
        @self.router.get("/", summary="首页")
        async def index():
            """首页接口 - 返回欢迎信息
            
            Returns:
                Dict: 欢迎信息响应
            """
            return success_response(data="Welcome to ThinkPython!")
        
        # 系统信息 - 返回应用配置信息
        @self.router.get("/info", summary="系统信息")
        async def info():
            """系统信息接口 - 返回应用名称、版本号和调试模式
            
            Returns:
                Dict: 系统信息响应
            """
            from config.app import APP_CONFIG
            return success_response(data={
                "app_name": APP_CONFIG["name"],
                "version": APP_CONFIG["version"],
                "debug": APP_CONFIG["debug"],
            })
