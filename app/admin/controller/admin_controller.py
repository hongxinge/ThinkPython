"""
后台管理 - 管理员控制器示例
"""
from pydantic import BaseModel
from core.base_controller import BaseController
from helpers.response import success_response


class AdminLoginRequest(BaseModel):
    """管理员登录请求"""
    username: str
    password: str


class AdminController(BaseController):
    """后台管理员控制器"""
    
    def __init__(self):
        super().__init__()
        self._setup_routes()
    
    def _setup_routes(self):
        @self.router.post("/admin/login", summary="管理员登录")
        async def login(request: AdminLoginRequest):
            # TODO: 验证管理员账号密码
            # TODO: 生成token
            return self.success(data={"token": "example-token"}, message="登录成功")
        
        @self.router.get("/admin/info", summary="获取管理员信息")
        async def get_info():
            # TODO: 从token获取管理员信息
            return self.success(data={"username": "admin", "role": "super_admin"})
        
        @self.router.get("/admin/menu", summary="获取菜单权限")
        async def get_menu():
            # TODO: 根据角色返回菜单
            return self.success(data={
                "menus": [
                    {"id": 1, "name": "首页", "icon": "home", "path": "/dashboard"},
                    {"id": 2, "name": "用户管理", "icon": "user", "path": "/user"},
                ]
            })
