#!/usr/bin/env python
"""
ThinkPython CLI 命令行工具

本模块提供类似 ThinkPHP 的 think 命令，用于快速开发和管理项目。
通过命令行可以执行以下操作：
- run: 启动开发服务器
- make-controller: 快速创建控制器文件
- make-model: 快速创建数据模型文件
- make-service: 快速创建服务文件
- make-module: 快速创建完整模块（含 controller/service/model 目录）
- db-migrate: 执行数据库迁移（创建表结构）
- list-routes: 列出所有已注册的路由

用法:
    python think.py <command> [arguments]

示例:
    python think.py run                          # 启动开发服务器
    python think.py run --port 9000              # 指定端口启动
    python think.py make-controller User          # 创建 User 控制器
    python think.py make-model Product            # 创建 Product 模型
    python think.py make-service Order            # 创建 Order 服务
    python think.py make-module blog              # 创建 blog 模块
    python think.py db-migrate                    # 执行数据库迁移
    python think.py list-routes                   # 列出所有路由
"""
import sys
import argparse
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# 项目根目录（think.py 所在目录）
BASE_DIR = Path(__file__).resolve().parent

# 加载 .env 环境变量文件
load_dotenv(BASE_DIR / ".env")


class Command:
    """CLI 命令基类
    
    所有 CLI 命令都应继承此类，实现自己的 handle() 方法。
    每个命令有名称和描述，用于在 help 信息中展示。
    """
    
    def __init__(self, name: str, description: str = ""):
        """初始化命令
        
        Args:
            name: 命令名称，如 "run"、"make-controller"
            description: 命令描述，用于 help 信息
        """
        self.name = name
        self.description = description
    
    def handle(self, args: argparse.Namespace) -> None:
        """执行命令的逻辑
        
        子类必须实现此方法，处理命令的具体逻辑。
        
        Args:
            args: 命令行解析后的参数对象
        """
        raise NotImplementedError


class RunCommand(Command):
    """启动开发服务器命令
    
    使用 uvicorn 启动 FastAPI 应用，支持自定义端口和热重载。
    等同于直接运行 python main.py。
    """
    
    def __init__(self):
        super().__init__("run", "启动开发服务器")
    
    def handle(self, args: argparse.Namespace) -> None:
        """执行启动服务器命令
        
        Args:
            args: 包含 --host、--port、--no-reload 参数的命令行对象
        """
        import uvicorn
        from config.app import APP_CONFIG
        
        # 从命令行参数或配置中获取服务器设置
        host = getattr(args, "host", "0.0.0.0")
        port = getattr(args, "port", 8000)
        # 如果传入了 --no-reload 则关闭热重载，否则根据 debug 配置决定
        reload = getattr(args, "reload", APP_CONFIG["debug"])
        
        print(f"🚀 {APP_CONFIG['name']} v{APP_CONFIG['version']} 启动中...")
        print(f"📍 地址: http://{host}:{port}")
        print(f"📖 API文档: http://{host}:{port}/docs")
        
        uvicorn.run(
            "main:app",  # 应用模块路径
            host=host,
            port=port,
            reload=reload,  # 热重载：文件修改后自动重启
        )


class MakeControllerCommand(Command):
    """创建控制器文件命令
    
    根据提供的名称和模块，在对应的 controller 目录下生成
    包含基础 CRUD 路由的控制器模板文件。
    """
    
    def __init__(self):
        super().__init__("make-controller", "创建控制器文件")
    
    def handle(self, args: argparse.Namespace) -> None:
        """执行创建控制器命令
        
        Args:
            args: 包含 name 和 --module 参数的命令行对象
        """
        name = args.name
        module = getattr(args, "module", None)
        
        # 如果未指定模块，根据配置自动选择
        if not module:
            from config.app import APP_CONFIG
            if APP_CONFIG["module_mode"] == "multi":
                module = APP_CONFIG["default_module"]
            else:
                module = "single"
        
        # 创建控制器目录（如果不存在）
        controller_dir = BASE_DIR / "app" / module / "controller"
        controller_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名和路径
        file_name = f"{name.lower()}_controller.py"
        file_path = controller_dir / file_name
        
        # 检查文件是否已存在
        if file_path.exists():
            print(f"❌ 控制器已存在: {file_path}")
            return
        
        # 类名使用 PascalCase
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
    """创建数据模型文件命令
    
    在指定模块的 model 目录下生成 ORM 模型模板文件，
    继承 BaseModel 并包含基础字段定义。
    """
    
    def __init__(self):
        super().__init__("make-model", "创建数据模型文件")
    
    def handle(self, args: argparse.Namespace) -> None:
        """执行创建模型命令
        
        Args:
            args: 包含 name 和 --module 参数的命令行对象
        """
        name = args.name
        module = getattr(args, "module", None)
        
        # 如果未指定模块，根据配置自动选择
        if not module:
            from config.app import APP_CONFIG
            if APP_CONFIG["module_mode"] == "multi":
                module = APP_CONFIG["default_module"]
            else:
                module = "single"
        
        # 创建模型目录
        model_dir = BASE_DIR / "app" / module / "model"
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名（表名默认加 s 后缀，如 User -> users）
        file_name = f"{name.lower()}_model.py"
        file_path = model_dir / file_name
        
        if file_path.exists():
            print(f"❌ 模型已存在: {file_path}")
            return
        
        table_name = name.lower() + "s"  # 表名默认加复数后缀
        
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
    """创建服务文件命令
    
    在指定模块的 service 目录下生成继承 BaseService 的服务模板文件，
    包含基础 CRUD 方法骨架。
    """
    
    def __init__(self):
        super().__init__("make-service", "创建服务文件")
    
    def handle(self, args: argparse.Namespace) -> None:
        """执行创建服务命令
        
        Args:
            args: 包含 name 和 --module 参数的命令行对象
        """
        name = args.name
        module = getattr(args, "module", None)
        
        # 如果未指定模块，根据配置自动选择
        if not module:
            from config.app import APP_CONFIG
            if APP_CONFIG["module_mode"] == "multi":
                module = APP_CONFIG["default_module"]
            else:
                module = "single"
        
        # 创建服务目录
        service_dir = BASE_DIR / "app" / module / "service"
        service_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名
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


class MakeCrudCommand(Command):
    """根据数据库表结构一键生成 CRUD 三层代码
    
    连接数据库读取指定表的结构，自动生成：
    - Model: SQLAlchemy ORM 模型，包含字段定义、类型、注释
    - Controller: 包含完整 CRUD 路由 + Pydantic 请求模型
    - Service: 包含完整增删改查业务逻辑
    
    生成的代码可直接使用，开发者只需修改特定业务逻辑。
    """
    
    def __init__(self):
        super().__init__("make-crud", "根据数据库表生成 CRUD 代码")
    
    def handle(self, args: argparse.Namespace) -> None:
        """执行 CRUD 生成命令"""
        table_name = args.table.lower()
        module = getattr(args, "module", None)
        
        if not module:
            from config.app import APP_CONFIG
            if APP_CONFIG["module_mode"] == "multi":
                module = APP_CONFIG["default_module"]
            else:
                module = "single"
        
        # 确定输出目录
        model_dir = BASE_DIR / "app" / module / "model"
        controller_dir = BASE_DIR / "app" / module / "controller"
        service_dir = BASE_DIR / "app" / module / "service"
        
        for d in [model_dir, controller_dir, service_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        # 连接数据库读取表结构
        async def generate():
            from core.inspector import DatabaseInspector
            
            inspector = DatabaseInspector()
            await inspector.connect()
            
            # 检查表是否存在
            tables = await inspector.get_tables()
            if table_name not in tables:
                print(f"❌ 表 '{table_name}' 不存在于数据库中")
                print(f"   可用表: {', '.join(tables)}")
                await inspector.close()
                return False
            
            # 获取表结构
            table_info = await inspector.get_table_info(table_name)
            
            # 获取字段注释（MySQL）
            col_comments = await inspector.get_column_comments_mysql(table_name)
            for col in table_info.columns:
                if col.name in col_comments:
                    col.comment = col_comments[col.name]
            
            await inspector.close()
            
            # 生成类名
            class_name = self._to_pascal_case(table_name)
            model_name = f"{class_name}Model"
            service_name = f"{class_name}Service"
            controller_name = f"{class_name}Controller"
            request_name = f"{class_name}Request"
            update_name = f"{class_name}UpdateRequest"
            
            # 生成 Model
            self._generate_model(model_dir, model_name, table_info, class_name)
            
            # 生成 Controller
            self._generate_controller(
                controller_dir, controller_name, class_name, 
                request_name, update_name, table_info, module
            )
            
            # 生成 Service
            self._generate_service(
                service_dir, service_name, class_name, model_name, module, table_info
            )
            
            print(f"\n✅ CRUD 代码生成成功！")
            print(f"   Model:      {model_dir / f'{table_name}_model.py'}")
            print(f"   Controller: {controller_dir / f'{table_name.lower()}_controller.py'}")
            print(f"   Service:    {service_dir / f'{table_name.lower()}_service.py'}")
            print(f"\n💡 下一步: python think.py db-migrate")
            return True
        
        return asyncio.run(generate())
    
    def _to_pascal_case(self, name: str) -> str:
        """转换为 PascalCase"""
        parts = name.replace("_", " ").replace("-", " ").split()
        return "".join(p.capitalize() for p in parts)
    
    def _generate_model(self, model_dir: Path, model_name: str, table_info, class_name: str) -> None:
        """生成 Model 文件"""
        columns_code = []
        primary_key_col = None
        
        has_datetime_default = False
        
        for col in table_info.columns:
            if col.is_primary:
                primary_key_col = col.name
                continue  # 跳过主键（BaseModel 自带 id）
            
            # 构建 SQLAlchemy Column 定义
            col_type = self._build_sqlalchemy_type(col)
            nullable_str = f"nullable={str(col.nullable).lower()}" if col.nullable is not None else ""
            default_str = self._build_default(col)
            comment_str = f'comment="{col.comment}"' if col.comment else ""
            
            if "func.now()" in default_str:
                has_datetime_default = True
            
            parts = [col_type]
            if nullable_str:
                parts.append(nullable_str)
            if default_str:
                parts.append(default_str)
            if comment_str:
                parts.append(comment_str)
            
            columns_code.append(f"    {col.name} = Column({', '.join(parts)})")
        
        columns_str = "\n".join(columns_code)
        
        imports = "Column, String, Integer, Text, DateTime, Float, Boolean, Numeric, Date, Time, BigInteger, SmallInteger, LargeBinary, JSON"
        if has_datetime_default:
            imports += ", func"
        
        content = f'''"""
{class_name} 模型
"""
from sqlalchemy import {imports}
from core.base_model import BaseModel


class {model_name}(BaseModel):
    """{class_name}模型"""
    
    __tablename__ = "{table_info.name}"
    
{columns_str}
'''
        
        file_path = model_dir / f"{table_info.name}_model.py"
        file_path.write_text(content, encoding="utf-8")
    
    def _build_sqlalchemy_type(self, col) -> str:
        """构建 SQLAlchemy 类型定义"""
        sa_type = col.sqlalchemy_type
        
        if sa_type == "String" and col.max_length:
            return f"String({col.max_length})"
        elif sa_type == "Numeric":
            return "Numeric(10, 2)"
        
        return sa_type
    
    def _build_default(self, col) -> str:
        """构建默认值表达式"""
        if col.default is None:
            return ""
        
        default_val = str(col.default)
        
        # 处理特殊默认值
        if default_val.lower() in ("null",):
            return ""
        elif default_val.lower() == "current_timestamp":
            return "server_default=func.now()"
        elif default_val.startswith("nextval("):  # PostgreSQL 序列
            return ""
        
        # 尝试转换为 Python 类型
        try:
            if col.python_type == "int":
                return f"default={int(default_val)}"
            elif col.python_type == "float":
                return f"default={float(default_val)}"
            elif col.python_type == "bool":
                return f"default={default_val.lower() == 'true' or default_val == '1'}"
            else:
                return f"default='{default_val}'"
        except ValueError:
            return f"default='{default_val}'"
    
    def _generate_controller(
        self, controller_dir: Path, controller_name: str, class_name: str,
        request_name: str, update_name: str, table_info, module: str
    ) -> None:
        """生成 Controller 文件"""
        
        # 生成 Pydantic 请求字段
        create_fields = []
        update_fields = []
        
        needs_datetime = False
        needs_decimal = False
        needs_date = False
        needs_time = False
        
        for col in table_info.columns:
            if col.is_primary or col.is_auto_increment:
                continue
            
            py_type = self._to_python_type(col.python_type)
            
            # 跟踪需要的特殊导入
            if py_type == "datetime":
                needs_datetime = True
            elif py_type == "date":
                needs_date = True
            elif py_type == "time":
                needs_time = True
            elif py_type == "Decimal":
                needs_decimal = True
            
            is_required = not col.nullable and col.default is None
            field_def = self._build_pydantic_field(col, py_type, is_required)
            
            create_fields.append(f"    {col.name}: {py_type}{field_def}")
            update_fields.append(f"    {col.name}: Optional[{py_type}] = None")
        
        create_fields_str = "\n".join(create_fields)
        update_fields_str = "\n".join(update_fields)
        
        # 构建额外的类型导入
        extra_imports = []
        if needs_datetime:
            extra_imports.append("datetime")
        if needs_date:
            extra_imports.append("date")
        if needs_time:
            extra_imports.append("time")
        
        extra_import_line = ""
        if extra_imports:
            extra_import_line = f"from datetime import {', '.join(extra_imports)}\n"
        if needs_decimal:
            extra_import_line += "from decimal import Decimal\n"
        
        content = f'''"""
{class_name} 控制器
"""
from typing import Optional
from pydantic import BaseModel, Field
{extra_import_line}from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.base_controller import BaseController
from core.database import get_db
from app.{module}.service.{table_info.name.lower()}_service import {class_name}Service


class {request_name}(BaseModel):
    """创建{class_name}请求"""
{create_fields_str}


class {update_name}(BaseModel):
    """更新{class_name}请求"""
{update_fields_str}


class {controller_name}(BaseController):
    """{class_name}控制器"""
    
    def __init__(self):
        super().__init__()
        self._setup_routes()
    
    def _setup_routes(self):
        @self.router.get("/{table_info.name.lower()}/list", summary="{class_name}列表")
        async def get_list(
            page: int = 1, 
            page_size: int = 10, 
            db: AsyncSession = Depends(get_db)
        ):
            """获取{class_name}列表（分页）"""
            service = {class_name}Service(db)
            items, total = await service.get_list(page, page_size)
            return self.paginate(items, total, page, page_size)
        
        @self.router.get("/{table_info.name.lower()}/{{item_id}}", summary="{class_name}详情")
        async def get_detail(
            item_id: int, 
            db: AsyncSession = Depends(get_db)
        ):
            """获取{class_name}详情"""
            service = {class_name}Service(db)
            item = await service.get_detail(item_id)
            if not item:
                return self.error(f"{class_name} {{item_id}} 不存在", 404)
            return self.success(data=item)
        
        @self.router.post("/{table_info.name.lower()}", summary="创建{class_name}")
        async def create(
            request: {request_name}, 
            db: AsyncSession = Depends(get_db)
        ):
            """创建{class_name}"""
            service = {class_name}Service(db)
            item = await service.create(request.dict())
            return self.success(data=item, message="创建成功")
        
        @self.router.put("/{table_info.name.lower()}/{{item_id}}", summary="更新{class_name}")
        async def update(
            item_id: int, 
            request: {update_name}, 
            db: AsyncSession = Depends(get_db)
        ):
            """更新{class_name}"""
            service = {class_name}Service(db)
            item = await service.update(item_id, request.dict(exclude_unset=True))
            if not item:
                return self.error(f"{class_name} {{item_id}} 不存在", 404)
            return self.success(data=item, message="更新成功")
        
        @self.router.delete("/{table_info.name.lower()}/{{item_id}}", summary="删除{class_name}")
        async def delete(
            item_id: int, 
            db: AsyncSession = Depends(get_db)
        ):
            """删除{class_name}"""
            service = {class_name}Service(db)
            success = await service.delete(item_id)
            if not success:
                return self.error(f"{class_name} {{item_id}} 不存在", 404)
            return self.success(message="删除成功")
'''
        
        file_path = controller_dir / f"{table_info.name.lower()}_controller.py"
        file_path.write_text(content, encoding="utf-8")
    
    def _generate_service(
        self, service_dir: Path, service_name: str, class_name: str, 
        model_name: str, module: str, table_info
    ) -> None:
        """生成 Service 文件"""
        
        # 确定 Service 文件名（使用表名而非模型名推导）
        service_file_name = f"{table_info.name.lower()}_service"
        
        content = f'''"""
{class_name} 服务
"""
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.base_service import BaseService
from app.{module}.model.{table_info.name.lower()}_model import {model_name}


class {service_name}(BaseService):
    """{class_name}服务"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db)
        self.model_class = {model_name}
    
    async def get_list(self, page: int = 1, page_size: int = 10) -> tuple:
        """获取{class_name}列表"""
        offset = (page - 1) * page_size
        stmt = select(self.model_class).offset(offset).limit(page_size).order_by(self.model_class.id.desc())
        result = await self.db.execute(stmt)
        items = result.scalars().all()
        
        count_stmt = select(self.model_class)
        count_result = await self.db.execute(count_stmt)
        total = len(count_result.scalars().all())
        
        return [{k: v for k, v in item.__dict__.items() if not k.startswith('_') and k != 'id'} for item in items], total
    
    async def get_detail(self, item_id: int) -> Optional[Dict[str, Any]]:
        """获取{class_name}详情"""
        item = await self.db.get(self.model_class, item_id)
        if not item:
            return None
        return {k: v for k, v in item.__dict__.items() if not k.startswith('_') and k != 'id'}
    
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建{class_name}"""
        item = self.model_class(**data)
        self.db.add(item)
        await self.db.flush()
        await self.db.refresh(item)
        return {k: v for k, v in item.__dict__.items() if not k.startswith('_') and k != 'id'}
    
    async def update(self, item_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """更新{class_name}"""
        item = await self.db.get(self.model_class, item_id)
        if not item:
            return None
        for key, value in data.items():
            setattr(item, key, value)
        await self.db.flush()
        await self.db.refresh(item)
        return {k: v for k, v in item.__dict__.items() if not k.startswith('_') and k != 'id'}
    
    async def delete(self, item_id: int) -> bool:
        """删除{class_name}"""
        item = await self.db.get(self.model_class, item_id)
        if not item:
            return False
        await self.db.delete(item)
        await self.db.flush()
        return True
'''
        
        file_path = service_dir / f"{service_file_name}.py"
        file_path.write_text(content, encoding="utf-8")
    
    def _to_python_type(self, db_type: str) -> str:
        """数据库类型转 Python 类型"""
        type_map = {
            "int": "int",
            "str": "str",
            "float": "float",
            "bool": "bool",
            "datetime": "datetime",
            "date": "date",
            "time": "time",
            "dict": "dict",
            "bytes": "bytes",
            "Decimal": "Decimal",
        }
        return type_map.get(db_type, "str")
    
    def _build_pydantic_field(self, col, py_type: str, is_required: bool) -> str:
        """构建 Pydantic 字段定义"""
        comment_str = f', description="{col.comment}"' if col.comment else ""
        
        if is_required:
            if col.max_length and col.sqlalchemy_type == "String":
                return f" = Field(..., max_length={col.max_length}{comment_str})"
            return f" = Field(...{comment_str})"
        else:
            if col.max_length and col.sqlalchemy_type == "String":
                return f" = Field(None, max_length={col.max_length}{comment_str})"
            return f" = Field(None{comment_str})"


class MakeModuleCommand(Command):
    """创建模块命令
    
    在 app/ 目录下创建完整的模块结构（controller/service/model 目录 + __init__.py），
    并自动更新 .env 中的 ENABLED_MODULES 配置。
    """
    
    def __init__(self):
        super().__init__("make-module", "创建新模块")
    
    def handle(self, args: argparse.Namespace) -> None:
        """执行创建模块命令
        
        Args:
            args: 包含 name 参数的命令行对象
        """
        name = args.name.lower()  # 模块名统一小写
        module_dir = BASE_DIR / "app" / name
        
        if module_dir.exists():
            print(f"❌ 模块已存在: {module_dir}")
            return
        
        # 创建模块目录结构：controller/、service/、model/
        (module_dir / "controller").mkdir(parents=True)
        (module_dir / "service").mkdir(parents=True)
        (module_dir / "model").mkdir(parents=True)
        
        # 在每个目录下创建空的 __init__.py，使其成为 Python 包
        for d in [module_dir, module_dir / "controller", module_dir / "service", module_dir / "model"]:
            (d / "__init__.py").write_text("")
        
        # 更新 .env 文件，将新模块添加到 ENABLED_MODULES 配置中
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
    """数据库迁移命令
    
    支持两种迁移模式：
    1. 简单模式（默认）：使用 Base.metadata.create_all() 创建新表
       适用于首次初始化数据库，或小型项目
    
    2. Alembic 模式：使用 Alembic 进行版本化迁移
       适用于生产环境，支持：
       - 自动生成迁移脚本（检测模型变更）
       - 升级/降级数据库结构
       - 查看迁移历史
    
    使用方式:
        # 简单模式：创建所有模型对应的表
        python think.py db-migrate
        
        # Alembic 模式：自动生成迁移脚本（检测模型变更）
        python think.py db-migrate --auto -m "添加用户表"
        
        # Alembic 模式：执行所有未应用的迁移
        python think.py db-migrate --upgrade
        
        # Alembic 模式：回滚上一次迁移
        python think.py db-migrate --downgrade
        
        # Alembic 模式：查看迁移历史
        python think.py db-migrate --history
        
        # Alembic 模式：查看当前数据库版本
        python think.py db-migrate --current
    """
    
    def __init__(self):
        super().__init__("db-migrate", "执行数据库迁移")
    
    def handle(self, args: argparse.Namespace) -> None:
        """执行数据库迁移
        
        Args:
            args: 命令行参数对象
                --auto: 自动生成 Alembic 迁移脚本
                --upgrade: 执行所有未应用的 Alembic 迁移
                --downgrade: 回滚上一次 Alembic 迁移
                --history: 查看 Alembic 迁移历史
                --current: 查看当前数据库 Alembic 版本
                -m, --message: 迁移描述信息（与 --auto 配合使用）
        """
        # 判断是否使用 Alembic 模式
        use_alembic = any([
            getattr(args, "auto", False),
            getattr(args, "upgrade", False),
            getattr(args, "downgrade", False),
            getattr(args, "history", False),
            getattr(args, "current", False),
        ])
        
        if use_alembic:
            self._run_alembic(args)
        else:
            self._run_simple_migration()
    
    def _run_simple_migration(self):
        """简单模式：使用 create_all 创建表"""
        import asyncio
        from core.database import init_database, Base, engine
        
        async def run_migration():
            await init_database()
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("✅ 数据库迁移完成（简单模式：已创建所有模型对应的表）")
            print("💡 提示：如果需要版本化迁移，请使用 Alembic 模式：")
            print("   python think.py db-migrate --auto -m '描述'")
        
        try:
            asyncio.run(run_migration())
        except Exception as e:
            print(f"❌ 数据库迁移失败: {e}")
    
    def _run_alembic(self, args: argparse.Namespace):
        """Alembic 模式：使用 Alembic 进行版本化迁移"""
        try:
            from alembic.config import Config
            from alembic import command as alembic_command
        except ImportError:
            print("❌ Alembic 未安装，请先运行: pip install alembic")
            return
        
        alembic_ini = BASE_DIR / "alembic.ini"
        if not alembic_ini.exists():
            print("❌ alembic.ini 配置文件不存在")
            print("💡 提示：请确保 alembic/ 目录结构完整")
            return
        
        alembic_cfg = Config(str(alembic_ini))
        
        if getattr(args, "auto", False):
            # 自动生成迁移脚本
            message = getattr(args, "message", "auto migration")
            print(f"🔄 正在生成迁移脚本: {message}")
            try:
                alembic_command.revision(alembic_cfg, autogenerate=True, message=message)
                print("✅ 迁移脚本生成成功！")
                print("💡 下一步: python think.py db-migrate --upgrade")
            except Exception as e:
                print(f"❌ 生成迁移脚本失败: {e}")
        
        elif getattr(args, "upgrade", False):
            # 执行迁移（升级到最新版本）
            print("🔄 正在执行数据库迁移...")
            try:
                alembic_command.upgrade(alembic_cfg, "head")
                print("✅ 数据库迁移完成（Alembic 模式）")
            except Exception as e:
                print(f"❌ 数据库迁移失败: {e}")
        
        elif getattr(args, "downgrade", False):
            # 回滚上一次迁移
            print("🔄 正在回滚上一次迁移...")
            try:
                alembic_command.downgrade(alembic_cfg, "-1")
                print("✅ 数据库回滚成功")
            except Exception as e:
                print(f"❌ 数据库回滚失败: {e}")
        
        elif getattr(args, "history", False):
            # 查看迁移历史
            print("📋 迁移历史:")
            print("-" * 60)
            try:
                alembic_command.history(alembic_cfg)
            except Exception as e:
                print(f"❌ 查看历史失败: {e}")
        
        elif getattr(args, "current", False):
            # 查看当前数据库版本
            print("📍 当前数据库版本:")
            print("-" * 60)
            try:
                alembic_command.current(alembic_cfg)
            except Exception as e:
                print(f"❌ 查看版本失败: {e}")


class ListRoutesCommand(Command):
    """列出所有路由命令
    
    加载 FastAPI 应用并打印所有已注册的 HTTP 路由，
    包括请求方法、路径和描述信息。
    """
    
    def __init__(self):
        super().__init__("list-routes", "列出所有已注册的路由")
    
    def handle(self, args: argparse.Namespace) -> None:
        """执行列出路由命令
        
        Args:
            args: 命令行参数对象（此命令无需额外参数）
        """
        from main import app
        
        print(f"\n{'方法':<10} {'路径':<40} {'描述':<30}")
        print("-" * 80)
        
        for route in app.routes:
            if hasattr(route, "methods"):
                # 排除 HEAD 和 OPTIONS（FastAPI 自动生成的选项请求）
                methods = ", ".join(route.methods - {"HEAD", "OPTIONS"})
                path = route.path
                name = getattr(route, "name", "")
                summary = ""
                # 如果路由有 summary 属性（从 docstring 生成），则显示
                if hasattr(route, "summary") and route.summary:
                    summary = route.summary
                print(f"{methods:<10} {path:<40} {summary:<30}")
        
        # 统计路由总数（排除 HEAD/OPTIONS）
        print(f"\n共 {len([r for r in app.routes if hasattr(r, 'methods')])} 个路由\n")


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器
    
    配置所有可用命令及其参数：
    - run: 启动开发服务器
    - make-controller: 创建控制器文件
    - make-model: 创建数据模型文件
    - make-service: 创建服务文件
    - make-module: 创建完整模块
    - db-migrate: 执行数据库迁移
    - list-routes: 列出所有路由
    
    Returns:
        argparse.ArgumentParser: 配置好的命令行解析器
    """
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
    
    # make-crud 命令
    mc_parser = subparsers.add_parser("make-crud", help="根据数据库表生成 CRUD 代码")
    mc_parser.add_argument("table", help="数据库表名称")
    mc_parser.add_argument("--module", "-m", help="模块名称")
    
    # make-module 命令
    mm_parser = subparsers.add_parser("make-module", help="创建新模块")
    mm_parser.add_argument("name", help="模块名称")
    
    # db-migrate 命令
    db_parser = subparsers.add_parser("db-migrate", help="执行数据库迁移")
    db_parser.add_argument("--auto", action="store_true", help="自动生成 Alembic 迁移脚本")
    db_parser.add_argument("--upgrade", action="store_true", help="执行所有未应用的 Alembic 迁移")
    db_parser.add_argument("--downgrade", action="store_true", help="回滚上一次 Alembic 迁移")
    db_parser.add_argument("--history", action="store_true", help="查看 Alembic 迁移历史")
    db_parser.add_argument("--current", action="store_true", help="查看当前数据库 Alembic 版本")
    db_parser.add_argument("-m", "--message", default="auto migration", help="迁移描述信息")
    
    # list-routes 命令
    subparsers.add_parser("list-routes", help="列出所有路由")
    
    return parser


def main():
    """CLI 入口函数 - 解析命令行参数并执行对应命令"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        # 未指定命令时打印帮助信息
        parser.print_help()
        return
    
    # 命令映射表：命令名称 -> 命令类
    commands = {
        "run": RunCommand,
        "make-controller": MakeControllerCommand,
        "make-model": MakeModelCommand,
        "make-service": MakeServiceCommand,
        "make-crud": MakeCrudCommand,
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
