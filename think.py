#!/usr/bin/env python
"""
ThinkPython CLI 命令行工具
类似 ThinkPHP 的 think 命令
用法: python think.py <command> [arguments]
"""
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# 加载 .env 文件
load_dotenv(BASE_DIR / ".env")


class Command:
    """基础命令类"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
    
    def handle(self, args: argparse.Namespace) -> None:
        """执行命令"""
        raise NotImplementedError


class RunCommand(Command):
    """启动服务命令"""
    
    def __init__(self):
        super().__init__("run", "启动开发服务器")
    
    def handle(self, args: argparse.Namespace) -> None:
        import uvicorn
        from config.app import APP_CONFIG
        
        host = getattr(args, "host", "0.0.0.0")
        port = getattr(args, "port", 8000)
        reload = getattr(args, "reload", APP_CONFIG["debug"])
        
        print(f"🚀 {APP_CONFIG['name']} v{APP_CONFIG['version']} 启动中...")
        print(f"📍 地址: http://{host}:{port}")
        print(f"📖 API文档: http://{host}:{port}/docs")
        
        uvicorn.run(
            "main:app",
            host=host,
            port=port,
            reload=reload,
        )


class MakeControllerCommand(Command):
    """创建控制器命令"""
    
    def __init__(self):
        super().__init__("make-controller", "创建控制器文件")
    
    def handle(self, args: argparse.Namespace) -> None:
        name = args.name
        module = getattr(args, "module", None)
        
        if not module:
            from config.app import APP_CONFIG
            if APP_CONFIG["module_mode"] == "multi":
                module = APP_CONFIG["default_module"]
            else:
                module = "single"
        
        controller_dir = BASE_DIR / "app" / module / "controller"
        controller_dir.mkdir(parents=True, exist_ok=True)
        
        file_name = f"{name.lower()}_controller.py"
        file_path = controller_dir / file_name
        
        if file_path.exists():
            print(f"❌ 控制器已存在: {file_path}")
            return
        
        class_name = f"{name}Controller"
        
        content = f'''"""
{name} 控制器
"""
from pydantic import BaseModel
from core.base_controller import BaseController
from helpers.response import success_response, error_response


class {name}Request(BaseModel):
    """{name}请求模型"""
    pass


class {class_name}(BaseController):
    """{name}控制器"""
    
    def __init__(self):
        super().__init__()
        self._setup_routes()
    
    def _setup_routes(self):
        @self.router.get("/{name.lower()}/list", summary="{name}列表")
        async def get_list(page: int = 1, page_size: int = 10):
            # TODO: 调用Service层获取数据
            return self.success(data={{
                "items": [],
                "total": 0,
            }})
        
        @self.router.get("/{name.lower()}/{{item_id}}", summary="{name}详情")
        async def get_detail(item_id: int):
            # TODO: 调用Service层获取详情
            return self.success(data={{"id": item_id}})
        
        @self.router.post("/{name.lower()}", summary="创建{name}")
        async def create(request: {name}Request):
            # TODO: 调用Service层创建数据
            return self.success(data=request.dict(), message="创建成功")
        
        @self.router.put("/{name.lower()}/{{item_id}}", summary="更新{name}")
        async def update(item_id: int, request: {name}Request):
            # TODO: 调用Service层更新数据
            return self.success(data={{"id": item_id}}, message="更新成功")
        
        @self.router.delete("/{name.lower()}/{{item_id}}", summary="删除{name}")
        async def delete(item_id: int):
            # TODO: 调用Service层删除数据
            return self.success(message="删除成功")
'''
        
        file_path.write_text(content, encoding="utf-8")
        print(f"✅ 控制器创建成功: {file_path}")


class MakeModelCommand(Command):
    """创建模型命令"""
    
    def __init__(self):
        super().__init__("make-model", "创建数据模型文件")
    
    def handle(self, args: argparse.Namespace) -> None:
        name = args.name
        module = getattr(args, "module", None)
        
        if not module:
            from config.app import APP_CONFIG
            if APP_CONFIG["module_mode"] == "multi":
                module = APP_CONFIG["default_module"]
            else:
                module = "single"
        
        model_dir = BASE_DIR / "app" / module / "model"
        model_dir.mkdir(parents=True, exist_ok=True)
        
        file_name = f"{name.lower()}_model.py"
        file_path = model_dir / file_name
        
        if file_path.exists():
            print(f"❌ 模型已存在: {file_path}")
            return
        
        table_name = name.lower() + "s"
        
        content = f'''"""
{name} 模型
"""
from sqlalchemy import Column, String, Integer, Text
from core.base_model import BaseModel


class {name}(BaseModel):
    """{name}模型"""
    
    __tablename__ = "{table_name}"
    
    # TODO: 添加字段
    # name = Column(String(100), nullable=False, comment="名称")
    # status = Column(Integer, default=1, comment="状态")
'''
        
        file_path.write_text(content, encoding="utf-8")
        print(f"✅ 模型创建成功: {file_path}")


class MakeServiceCommand(Command):
    """创建服务命令"""
    
    def __init__(self):
        super().__init__("make-service", "创建服务文件")
    
    def handle(self, args: argparse.Namespace) -> None:
        name = args.name
        module = getattr(args, "module", None)
        
        if not module:
            from config.app import APP_CONFIG
            if APP_CONFIG["module_mode"] == "multi":
                module = APP_CONFIG["default_module"]
            else:
                module = "single"
        
        service_dir = BASE_DIR / "app" / module / "service"
        service_dir.mkdir(parents=True, exist_ok=True)
        
        file_name = f"{name.lower()}_service.py"
        file_path = service_dir / file_name
        
        if file_path.exists():
            print(f"❌ 服务已存在: {file_path}")
            return
        
        content = f'''"""
{name} 服务
"""
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from core.base_service import BaseService


class {name}Service(BaseService):
    """{name}服务"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db)
        # self.model_class = {name}  # 关联到{name}模型
    
    async def get_list(self, page: int = 1, page_size: int = 10) -> tuple:
        """获取列表"""
        # TODO: 实现具体业务逻辑
        return [], 0
    
    async def get_detail(self, item_id: int) -> Optional[Dict[str, Any]]:
        """获取详情"""
        # TODO: 实现具体业务逻辑
        return None
    
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建"""
        # TODO: 实现具体业务逻辑
        return data
    
    async def update(self, item_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """更新"""
        # TODO: 实现具体业务逻辑
        return None
    
    async def delete(self, item_id: int) -> bool:
        """删除"""
        # TODO: 实现具体业务逻辑
        return False
'''
        
        file_path.write_text(content, encoding="utf-8")
        print(f"✅ 服务创建成功: {file_path}")


class MakeModuleCommand(Command):
    """创建模块命令"""
    
    def __init__(self):
        super().__init__("make-module", "创建新模块")
    
    def handle(self, args: argparse.Namespace) -> None:
        name = args.name.lower()
        module_dir = BASE_DIR / "app" / name
        
        if module_dir.exists():
            print(f"❌ 模块已存在: {module_dir}")
            return
        
        # 创建模块目录结构
        (module_dir / "controller").mkdir(parents=True)
        (module_dir / "service").mkdir(parents=True)
        (module_dir / "model").mkdir(parents=True)
        
        # 创建 __init__.py
        for d in [module_dir, module_dir / "controller", module_dir / "service", module_dir / "model"]:
            (d / "__init__.py").write_text("")
        
        # 更新 .env 文件
        env_file = BASE_DIR / ".env"
        if env_file.exists():
            content = env_file.read_text(encoding="utf-8")
            if "ENABLED_MODULES" in content:
                content = content.replace(
                    "ENABLED_MODULES=",
                    f"ENABLED_MODULES={name},"
                )
                env_file.write_text(content, encoding="utf-8")
        
        print(f"✅ 模块创建成功: {module_dir}")
        print(f"💡 请在 .env 中确认 ENABLED_MODULES 包含 '{name}'")


class DBMigrateCommand(Command):
    """数据库迁移命令"""
    
    def __init__(self):
        super().__init__("db-migrate", "执行数据库迁移")
    
    def handle(self, args: argparse.Namespace) -> None:
        import asyncio
        from core.database import init_database, Base, engine
        
        async def run_migration():
            await init_database()
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("✅ 数据库迁移完成")
        
        try:
            asyncio.run(run_migration())
        except Exception as e:
            print(f"❌ 数据库迁移失败: {e}")


class ListRoutesCommand(Command):
    """列出所有路由命令"""
    
    def __init__(self):
        super().__init__("list-routes", "列出所有已注册的路由")
    
    def handle(self, args: argparse.Namespace) -> None:
        from main import app
        
        print(f"\n{'方法':<10} {'路径':<40} {'描述':<30}")
        print("-" * 80)
        
        for route in app.routes:
            if hasattr(route, "methods"):
                methods = ", ".join(route.methods - {"HEAD", "OPTIONS"})
                path = route.path
                name = getattr(route, "name", "")
                summary = ""
                if hasattr(route, "summary") and route.summary:
                    summary = route.summary
                print(f"{methods:<10} {path:<40} {summary:<30}")
        
        print(f"\n共 {len([r for r in app.routes if hasattr(r, 'methods')])} 个路由\n")


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        prog="think",
        description="ThinkPython CLI 命令行工具",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # run 命令
    run_parser = subparsers.add_parser("run", help="启动开发服务器")
    run_parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    run_parser.add_argument("--port", type=int, default=8000, help="监听端口")
    run_parser.add_argument("--no-reload", action="store_true", help="关闭热重载")
    
    # make-controller 命令
    mc_parser = subparsers.add_parser("make-controller", help="创建控制器")
    mc_parser.add_argument("name", help="控制器名称")
    mc_parser.add_argument("--module", "-m", help="模块名称")
    
    # make-model 命令
    mm_parser = subparsers.add_parser("make-model", help="创建数据模型")
    mm_parser.add_argument("name", help="模型名称")
    mm_parser.add_argument("--module", "-m", help="模块名称")
    
    # make-service 命令
    ms_parser = subparsers.add_parser("make-service", help="创建服务")
    ms_parser.add_argument("name", help="服务名称")
    ms_parser.add_argument("--module", "-m", help="模块名称")
    
    # make-module 命令
    mm_parser = subparsers.add_parser("make-module", help="创建新模块")
    mm_parser.add_argument("name", help="模块名称")
    
    # db-migrate 命令
    subparsers.add_parser("db-migrate", help="执行数据库迁移")
    
    # list-routes 命令
    subparsers.add_parser("list-routes", help="列出所有路由")
    
    return parser


def main():
    """CLI入口"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 命令映射
    commands = {
        "run": RunCommand,
        "make-controller": MakeControllerCommand,
        "make-model": MakeModelCommand,
        "make-service": MakeServiceCommand,
        "make-module": MakeModuleCommand,
        "db-migrate": DBMigrateCommand,
        "list-routes": ListRoutesCommand,
    }
    
    command_class = commands.get(args.command)
    if command_class:
        command = command_class()
        command.handle(args)
    else:
        print(f"❌ 未知命令: {args.command}")
        parser.print_help()


if __name__ == "__main__":
    main()
