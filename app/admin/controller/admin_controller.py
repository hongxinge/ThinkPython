"""
ThinkPython 示例后台管理员控制器 - 多模块模式

本文件是多模块模式下 admin 模块的示例控制器，展示后台管理系统的常见接口。
此控制器提供管理员登录、获取管理员信息和获取菜单权限等功能。

访问路径：
- POST /admin/login      - 管理员登录（验证账号密码，返回 Token）
- GET  /admin/info       - 获取当前登录管理员信息
- GET  /admin/menu       - 获取管理员的菜单权限列表

架构说明：
在多模块模式下，模块名会作为 URL 前缀。
例如 admin 模块的控制器路由会自动加上 /admin 前缀。

安全注意事项：
- 登录接口必须使用 HTTPS
- 密码必须加密存储（推荐 bcrypt）
- Token 必须设置合理的过期时间
- 敏感操作需要二次验证
"""
from pydantic import BaseModel
from core.base_controller import BaseController
from helpers.response import success_response


class AdminLoginRequest(BaseModel):
    """管理员登录请求体模型 - 用于 Pydantic 参数验证
    
    Attributes:
        username: 管理员用户名
        password: 管理员密码（明文，服务端需要加密后比对）
    """
    username: str  # 管理员用户名
    password: str  # 管理员密码


class AdminController(BaseController):
    """后台管理员控制器 - 处理后台管理相关的路由
    
    此控制器演示了后台管理系统的常见接口设计：
    - 登录认证：验证管理员身份并返回 JWT Token
    - 用户信息：从 Token 中解析管理员信息
    - 菜单权限：根据管理员角色返回对应的菜单和权限
    
    多模块模式下的路由规则：
    - 路由定义中不需要写 /admin 前缀，系统会自动添加
    - 例如 @self.router.post("/admin/login") 实际路径为 /admin/admin/login
    - 建议定义时省略模块前缀：@self.router.post("/login")
    
    访问示例：
        # 管理员登录
        curl -X POST http://localhost:8000/admin/admin/login \
             -H "Content-Type: application/json" \
             -d '{"username": "admin", "password": "admin123"}'
    """
    
    def __init__(self):
        # 调用父类构造函数，初始化 self.router
        super().__init__()
        # 注册路由
        self._setup_routes()
    
    def _setup_routes(self):
        """初始化路由配置"""
        
        # 管理员登录接口
        @self.router.post("/admin/login", summary="管理员登录")
        async def login(request: AdminLoginRequest):
            """管理员登录 - 验证账号密码并返回 JWT Token
            
            登录流程：
            1. 验证用户名和密码是否正确
            2. 生成 JWT Token（包含用户 ID 和角色信息）
            3. 返回 Token 给客户端
            
            Args:
                request: 登录请求体，包含用户名和密码
                
            Returns:
                Dict: 登录成功返回 Token
            """
            # TODO: 验证管理员账号密码
            # 1. 从数据库查询管理员信息
            # 2. 使用 bcrypt 验证密码：bcrypt.checkpw(password.encode(), admin.password.encode())
            # 3. 如果密码错误，抛出 UnauthorizedException
            
            # TODO: 生成 JWT Token
            # from helpers.auth import create_token
            # token = create_token(user_id=admin.id, extra_data={"role": admin.role})
            
            return self.success(data={"token": "example-token"}, message="登录成功")
        
        # 获取管理员信息接口
        @self.router.get("/admin/info", summary="获取管理员信息")
        async def get_info():
            """获取当前登录管理员的详细信息
            
            从请求头的 Authorization 中提取 Token，
            解析 Token 获取用户 ID，然后查询管理员信息。
            
            Returns:
                Dict: 管理员信息，包括用户名、角色等
            """
            # TODO: 从 Token 获取管理员信息
            # 1. 从请求头获取 Token：authorization = Header(None)
            # 2. 解析 Token：payload = decode_token(token)
            # 3. 根据 user_id 查询管理员信息
            
            return self.success(data={"username": "admin", "role": "super_admin"})
        
        # 获取菜单权限接口
        @self.router.get("/admin/menu", summary="获取菜单权限")
        async def get_menu():
            """根据管理员角色返回可访问的菜单列表
            
            不同角色的管理员看到不同的菜单和权限。
            例如：超级管理员看到所有菜单，普通管理员只看到部分菜单。
            
            Returns:
                Dict: 菜单列表，包含菜单 ID、名称、图标和路径
            """
            # TODO: 根据角色返回菜单
            # 1. 从 Token 获取管理员角色
            # 2. 根据角色查询对应的菜单权限
            # 3. 构建菜单树形结构（使用 helpers.common.tree_data()）
            
            return self.success(data={
                "menus": [
                    {"id": 1, "name": "首页", "icon": "home", "path": "/dashboard"},
                    {"id": 2, "name": "用户管理", "icon": "user", "path": "/user"},
                ]
            })
