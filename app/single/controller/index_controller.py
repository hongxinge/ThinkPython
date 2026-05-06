"""
示例控制器 - Index
"""
from core.base_controller import BaseController
from helpers.response import success_response


class IndexController(BaseController):
    """首页控制器"""
    
    def __init__(self):
        super().__init__()
        self._setup_routes()
    
    def _setup_routes(self):
        @self.router.get("/", summary="首页")
        async def index():
            return success_response(data={"message": "Welcome to ThinkPython!"})
        
        @self.router.get("/info", summary="系统信息")
        async def info():
            from config.app import APP_CONFIG
            return success_response(data={
                "app_name": APP_CONFIG["name"],
                "version": APP_CONFIG["version"],
                "debug": APP_CONFIG["debug"],
            })
