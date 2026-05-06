"""
路由自动注册
支持单模块和多模块模式切换
"""
import os
import importlib
import inspect
from pathlib import Path
from fastapi import APIRouter
from config.app import APP_CONFIG

BASE_DIR = Path(__file__).resolve().parent.parent


def get_router_by_mode() -> APIRouter:
    """根据配置获取路由 (支持单/多模块切换)"""
    main_router = APIRouter()
    
    if APP_CONFIG["module_mode"] == "multi":
        register_multi_modules(main_router)
    else:
        register_single_module(main_router)
    
    return main_router


def register_single_module(main_router: APIRouter):
    """注册单模块路由"""
    controller_dir = BASE_DIR / "app" / "single" / "controller"
    _register_controllers_from_dir(main_router, controller_dir, prefix="", module_path="app.single")


def register_multi_modules(main_router: APIRouter):
    """注册多模块路由"""
    modules = APP_CONFIG["modules"]
    app_dir = BASE_DIR / "app"
    
    for module in modules:
        module = module.strip()
        if not module:
            continue
        
        controller_dir = app_dir / module / "controller"
        prefix = f"/{module}"
        _register_controllers_from_dir(main_router, controller_dir, prefix=prefix, module_path=f"app.{module}")


def _register_controllers_from_dir(main_router: APIRouter, controller_dir: Path, prefix: str, module_path: str):
    """从目录自动注册控制器"""
    if not controller_dir.exists():
        return
    
    for file_path in controller_dir.glob("*.py"):
        if file_path.name.startswith("_"):
            continue
        
        full_module_name = f"{module_path}.controller.{file_path.stem}"
        try:
            module = importlib.import_module(full_module_name)
            _register_controller_routes(main_router, module, prefix)
        except Exception as e:
            print(f"Warning: Failed to register controller {full_module_name}: {e}")


def _register_controller_routes(main_router: APIRouter, module, prefix: str = ""):
    """从模块中注册控制器路由"""
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if hasattr(obj, "router") and hasattr(obj, "__module__"):
            if module.__name__ == obj.__module__:
                instance = obj()
                main_router.include_router(
                    instance.router,
                    prefix=prefix,
                    tags=[name],
                )
