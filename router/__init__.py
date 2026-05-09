"""
ThinkPython 路由自动注册模块

本模块实现了控制器的自动扫描和路由注册功能，支持单模块和多模块两种模式：
- 单模块模式（module_mode="single"）：扫描 app/single/controller/ 目录下的所有控制器
- 多模块模式（module_mode="multi"）：扫描 app/{module}/controller/ 目录下的控制器

工作流程：
1. 根据配置确定模块模式
2. 扫描控制器目录，找到所有 .py 文件
3. 动态导入每个控制器模块
4. 检查模块中是否定义了继承 BaseController 的类
5. 实例化控制器并将其 router 注册到主路由

约定：
- 控制器文件命名：xxx_controller.py（如 user_controller.py）
- 控制器类命名：XxxController（如 UserController）
- 控制器类必须继承 BaseController 并具有 router 属性
- 以 _ 开头的文件会被忽略（如 __init__.py）

使用示例:
    # 在 main.py 中调用
    from router import get_router_by_mode
    
    main_router = get_router_by_mode()
    app.include_router(main_router)
"""
import os
import importlib
import inspect
from pathlib import Path
from fastapi import APIRouter
from loguru import logger
from config.app import APP_CONFIG

# 项目根目录（router/__init__.py 的上一级目录）
BASE_DIR = Path(__file__).resolve().parent.parent


def get_router_by_mode() -> APIRouter:
    """根据配置获取主路由器（支持单/多模块模式切换）
    
    这是路由注册的入口函数，由 main.py 调用。
    根据 config/app.py 中的 module_mode 配置决定使用哪种路由注册策略。
    
    Returns:
        APIRouter: 包含所有已注册控制器路由的主路由器实例
        
    使用示例:
        from router import get_router_by_mode
        
        app = FastAPI()
        main_router = get_router_by_mode()
        app.include_router(main_router)
    """
    main_router = APIRouter()
    
    # 根据模块模式选择对应的路由注册策略
    if APP_CONFIG["module_mode"] == "multi":
        register_multi_modules(main_router)
    else:
        register_single_module(main_router)
    
    return main_router


def register_single_module(main_router: APIRouter):
    """注册单模块路由
    
    扫描 app/single/controller/ 目录，将该目录下所有控制器注册到主路由。
    适用于小型项目，所有控制器共享同一个 URL 命名空间。
    
    Args:
        main_router: FastAPI 主路由器实例
    """
    controller_dir = BASE_DIR / "app" / "single" / "controller"
    # 单模块模式下 prefix 为空，路由直接注册到根路径
    _register_controllers_from_dir(main_router, controller_dir, prefix="", module_path="app.single")


def register_multi_modules(main_router: APIRouter):
    """注册多模块路由
    
    智能扫描策略：
    1. 自动扫描 app/ 目录下所有包含 controller/ 子目录的模块
    2. 如果 ENABLED_MODULES 配置为空（或包含 "*"），则加载所有发现的模块
    3. 如果 ENABLED_MODULES 配置了具体模块名，则作为白名单过滤（只加载配置的模块）
    
    例如：
    - app/admin/ 存在 → 注册到 /admin/xxx
    - app/api/ 存在 → 注册到 /api/xxx
    - app/user/ 存在 → 注册到 /user/xxx（无需修改配置，自动发现！）
    
    Args:
        main_router: FastAPI 主路由器实例
    """
    app_dir = BASE_DIR / "app"
    modules = APP_CONFIG["modules"]
    
    # 判断是否启用了白名单模式
    # 如果 modules 列表只包含空字符串或 "*"，表示自动发现所有模块
    is_auto_discover = not modules or modules == [""] or modules == ["*"]
    
    if is_auto_discover:
        # 自动发现模式：扫描 app/ 下所有包含 controller/ 子目录的模块
        # 注意：common 模块是公共代码目录，不作为独立模块注册路由
        logger.info("模块模式: 自动发现（加载所有模块）")
        discovered_modules = []
        if app_dir.exists():
            for item in app_dir.iterdir():
                if item.is_dir() and item.name not in ("__pycache__", "common") and not item.name.startswith("_"):
                    # 检查是否包含 controller 子目录
                    if (item / "controller").exists():
                        discovered_modules.append(item.name)
        modules = discovered_modules
    
    # 遍历模块列表，注册每个模块的路由
    for module in modules:
        module = module.strip()
        if not module:
            continue
        
        controller_dir = app_dir / module / "controller"
        prefix = f"/{module}"
        _register_controllers_from_dir(main_router, controller_dir, prefix=prefix, module_path=f"app.{module}")


def _register_controllers_from_dir(main_router: APIRouter, controller_dir: Path, prefix: str, module_path: str):
    """从指定目录自动扫描并注册所有控制器
    
    这是路由注册的核心实现函数，执行以下步骤：
    1. 检查目录是否存在
    2. 遍历目录下所有 .py 文件
    3. 跳过以 _ 开头的文件（如 __init__.py）
    4. 动态导入模块（如 app.single.controller.user_controller）
    5. 调用 _register_controller_routes() 注册该模块中的控制器类
    
    Args:
        main_router: FastAPI 主路由器实例
        controller_dir: 控制器文件所在的目录路径
        prefix: 路由 URL 前缀（如 "/admin"）
        module_path: Python 模块路径前缀（如 "app.admin"）
    """
    if not controller_dir.exists():
        logger.warning(f"控制器目录不存在: {controller_dir}")
        return
    
    registered_count = 0
    # 遍历目录下所有 Python 文件
    for file_path in controller_dir.glob("*.py"):
        if file_path.name.startswith("_"):
            continue  # 跳过 __init__.py 等内部文件
        
        # 构造完整的模块导入路径，如 app.single.controller.user_controller
        full_module_name = f"{module_path}.controller.{file_path.stem}"
        try:
            # 动态导入模块
            module = importlib.import_module(full_module_name)
            # 注册该模块中的控制器路由
            count = _register_controller_routes(main_router, module, prefix)
            registered_count += count
        except Exception as e:
            logger.error(f"注册控制器失败 {full_module_name}: {e}")
    
    logger.info(f"注册完成: {registered_count} 个控制器从 {controller_dir.name}")


def _register_controller_routes(main_router: APIRouter, module, prefix: str = "") -> int:
    """从模块中查找并注册控制器路由
    
    使用 inspect.getmembers() 遍历模块中定义的所有类，
    找出继承自 BaseController 的类（通过检查是否有 router 属性），
    实例化后将其实例的 router 注册到主路由。
    
    Args:
        main_router: FastAPI 主路由器实例
        module: 已导入的控制器模块
        prefix: 路由 URL 前缀
        
    Returns:
        int: 成功注册的控制器数量
    """
    count = 0
    # 遍历模块中定义的所有类
    for name, obj in inspect.getmembers(module, inspect.isclass):
        # 判断条件：
        # 1. 类有 router 属性（说明是 BaseController 的子类）
        # 2. 类定义在当前模块中（避免重复注册导入的基类）
        if hasattr(obj, "router") and hasattr(obj, "__module__"):
            if module.__name__ == obj.__module__:
                # 实例化控制器（__init__ 中会调用 _setup_routes() 注册路由）
                instance = obj()
                # 将控制器的 router 挂载到主路由上
                main_router.include_router(
                    instance.router,
                    prefix=prefix,  # URL 前缀
                    tags=[name],  # 在 API 文档中按控制器名称分组
                )
                count += 1
                logger.debug(f"注册控制器: {prefix}/{name}")
    return count
