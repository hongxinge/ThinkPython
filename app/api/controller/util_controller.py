"""
ThinkPython Excel 和文件工具示例控制器

本控制器演示框架内置的 Excel 导入导出和文件上传下载功能。
包含完整的示例代码，开发者可直接参考使用。

功能列表：
- Excel 导入（解析上传的 Excel 文件）
- Excel 导出（导出数据为 Excel 文件）
- 单文件上传（支持格式验证和大小限制）
- 多文件批量上传
- 文件下载
- 文件删除
- 文件信息查看

访问路径（多模块模式下带 /api 前缀）：
- POST /util/excel/import          - Excel 导入
- POST /util/excel/export          - Excel 导出
- POST /util/file/upload           - 单文件上传
- POST /util/file/upload-multiple  - 多文件上传
- GET  /util/file/download         - 文件下载
- DELETE /util/file/delete         - 文件删除
- GET  /util/file/info             - 文件信息

使用示例：
    # Excel 导入
    curl -X POST http://localhost:8000/api/util/excel/import \
      -F "file=@data.xlsx"

    # Excel 导出
    curl -X POST http://localhost:8000/api/util/excel/export \
      -o output.xlsx

    # 文件上传
    curl -X POST http://localhost:8000/api/util/file/upload \
      -F "file=@photo.jpg"
"""
from typing import List, Optional
from pathlib import Path

from fastapi import UploadFile, File, HTTPException, Query

from core.base_controller import BaseController
from utils.excel import ExcelUtil
from utils.file import FileUtil, IMAGE_EXTENSIONS, DOCUMENT_EXTENSIONS


class UtilController(BaseController):
    """工具类示例控制器 - 演示 Excel 和文件操作
    
    此控制器演示了 ThinkPython 框架内置的实用工具：
    - ExcelUtil: Excel 文件的读取、写入、下载响应
    - FileUtil: 文件上传、下载、删除、信息查询
    
    开发者可以参考这些示例在自己的项目中集成这些工具。
    """
    
    def __init__(self):
        # 调用父类构造函数，初始化 self.router
        super().__init__()
        # 注册路由
        self._setup_routes()
    
    def _setup_routes(self):
        """初始化路由配置"""
        
        # ==============================
        # Excel 相关接口
        # ==============================
        
        # Excel 导入
        @self.router.post("/util/excel/import", summary="Excel 导入")
        async def excel_import(file: UploadFile = File(...)):
            """从 Excel 文件导入数据
            
            解析上传的 Excel 文件，返回数据列表。
            支持 .xlsx 和 .xls 格式。
            
            Args:
                file: 上传的 Excel 文件
                
            Returns:
                Dict: 解析后的数据列表和统计信息
                
            使用示例：
                curl -X POST http://localhost:8000/api/util/excel/import \
                  -F "file=@users.xlsx"
            """
            try:
                # 从上传文件读取 Excel 数据
                data = await ExcelUtil.read_from_upload(file)
                
                return self.success(data={
                    "total": len(data),
                    "rows": data,
                })
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        # Excel 导入（带列名映射）
        @self.router.post("/util/excel/import-with-mapping", summary="Excel 导入（列名映射）")
        async def excel_import_with_mapping(
            file: UploadFile = File(...),
            column_mapping: Optional[str] = Query(
                None,
                description="列名映射 JSON，例如: {'姓名': 'name', '年龄': 'age'}"
            )
        ):
            """从 Excel 文件导入数据，并映射列名
            
            适用于 Excel 列名与数据库字段名不一致的场景。
            
            Args:
                file: 上传的 Excel 文件
                column_mapping: 列名映射 JSON 字符串
                
            Returns:
                Dict: 映射后的数据列表
            """
            try:
                import json
                
                mapping = json.loads(column_mapping) if column_mapping else None
                
                # 读取 Excel 数据并应用列名映射
                data = await ExcelUtil.read_with_mapping_from_upload(file, mapping)
                
                return self.success(data={
                    "total": len(data),
                    "rows": data,
                })
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"列名映射格式错误: {str(e)}")
        
        # Excel 导出
        @self.router.post("/util/excel/export", summary="Excel 导出")
        async def excel_export():
            """导出数据为 Excel 文件
            
            演示如何将数据导出为 Excel 文件供用户下载。
            支持自定义表头、样式、自动列宽等高级功能。
            
            Returns:
                Response: Excel 文件下载响应
                
            使用示例：
                curl -X POST http://localhost:8000/api/util/excel/export \
                  -o output.xlsx
            """
            # 模拟导出数据（实际使用时从数据库查询）
            headers = ["ID", "姓名", "邮箱", "年龄", "状态"]
            data = [
                [1, "张三", "zhangsan@example.com", 28, "启用"],
                [2, "李四", "lisi@example.com", 32, "启用"],
                [3, "王五", "wangwu@example.com", 25, "禁用"],
            ]
            
            # 创建 Excel 下载响应
            return ExcelUtil.create_download_response(
                data=data,
                headers=headers,
                filename="用户数据.xlsx",
                sheet_name="用户列表",
            )
        
        # ==============================
        # 文件上传相关接口
        # ==============================
        
        # 单文件上传
        @self.router.post("/util/file/upload", summary="单文件上传")
        async def upload_file(
            file: UploadFile = File(...),
            category: str = Query("files", description="文件分类: images/documents/files")
        ):
            """上传单个文件
            
            支持格式验证和大小限制，返回文件信息。
            
            Args:
                file: 要上传的文件
                category: 文件分类，用于组织目录结构
                
            Returns:
                Dict: 上传结果，包含文件路径和访问 URL
                
            使用示例：
                # 上传图片
                curl -X POST http://localhost:8000/api/util/file/upload?category=images \
                  -F "file=@photo.jpg"
                
                # 上传文档
                curl -X POST http://localhost:8000/api/util/file/upload?category=documents \
                  -F "file=@report.pdf"
            """
            try:
                # 根据分类设置允许的扩展名
                allowed_ext = None
                if category == "images":
                    allowed_ext = IMAGE_EXTENSIONS
                elif category == "documents":
                    allowed_ext = DOCUMENT_EXTENSIONS
                
                # 上传文件
                result = await FileUtil.upload(
                    file,
                    category=category,
                    allowed_extensions=allowed_ext,
                )
                
                return self.success(data=result)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        # 多文件上传
        @self.router.post("/util/file/upload-multiple", summary="多文件上传")
        async def upload_multiple_files(
            files: List[UploadFile] = File(...),
            category: str = Query("files", description="文件分类")
        ):
            """批量上传多个文件
            
            Args:
                files: 要上传的文件列表
                category: 文件分类
                
            Returns:
                Dict: 上传结果，包含每个文件的信息
                
            使用示例：
                curl -X POST http://localhost:8000/api/util/file/upload-multiple?category=images \
                  -F "files=@photo1.jpg" \
                  -F "files=@photo2.jpg" \
                  -F "files=@photo3.jpg"
            """
            results = await FileUtil.upload_multiple(files, category=category)
            
            success_count = sum(1 for r in results if "error" not in r)
            
            return self.success(data={
                "total": len(files),
                "success": success_count,
                "failed": len(files) - success_count,
                "files": results,
            })
        
        # ==============================
        # 文件下载相关接口
        # ==============================
        
        # 文件下载
        @self.router.get("/util/file/download", summary="文件下载")
        async def download_file(
            file_path: str = Query(..., description="文件相对路径")
        ):
            """下载已上传的文件
            
            Args:
                file_path: 文件的相对路径，例如: uploads/images/2024/01/01/abc123.jpg
                
            Returns:
                FileResponse: 文件下载响应
                
            使用示例：
                # 下载文件
                curl -O http://localhost:8000/api/util/file/download?file_path=uploads/images/test.jpg
                
                # 在线预览（图片/PDF）
                curl -O http://localhost:8000/api/util/file/download?file_path=uploads/images/test.jpg&inline=1
            """
            try:
                # 检查文件是否存在
                full_path = Path(file_path)
                if not full_path.is_absolute():
                    # 如果是相对路径，加上项目根目录
                    full_path = Path(__file__).parent.parent.parent.parent / file_path
                
                return FileUtil.create_download_response(full_path)
            except FileNotFoundError as e:
                raise HTTPException(status_code=404, detail=str(e))
        
        # 文件预览（inline 模式）
        @self.router.get("/util/file/preview", summary="文件在线预览")
        async def preview_file(
            file_path: str = Query(..., description="文件相对路径")
        ):
            """在线预览文件（图片/PDF 等）
            
            使用 inline 模式，浏览器会直接显示文件内容而不是下载。
            
            Args:
                file_path: 文件的相对路径
                
            Returns:
                FileResponse: 文件预览响应
            """
            try:
                full_path = Path(file_path)
                if not full_path.is_absolute():
                    full_path = Path(__file__).parent.parent.parent.parent / file_path
                
                return FileUtil.create_download_response(full_path, inline=True)
            except FileNotFoundError as e:
                raise HTTPException(status_code=404, detail=str(e))
        
        # ==============================
        # 文件管理相关接口
        # ==============================
        
        # 文件信息
        @self.router.get("/util/file/info", summary="获取文件信息")
        async def get_file_info(
            file_path: str = Query(..., description="文件路径")
        ):
            """获取文件详细信息
            
            Args:
                file_path: 文件路径
                
            Returns:
                Dict: 文件信息，包含大小、类型、创建时间等
            """
            full_path = Path(file_path)
            if not full_path.is_absolute():
                full_path = Path(__file__).parent.parent.parent.parent / file_path
            
            info = FileUtil.get_file_info(full_path)
            
            if not info.get("exists"):
                raise HTTPException(status_code=404, detail="文件不存在")
            
            return self.success(data=info)
        
        # 文件删除
        @self.router.delete("/util/file/delete", summary="删除文件")
        async def delete_file(
            file_path: str = Query(..., description="文件路径")
        ):
            """删除已上传的文件
            
            Args:
                file_path: 要删除的文件路径
                
            Returns:
                Dict: 操作结果
                
            使用示例：
                curl -X DELETE http://localhost:8000/api/util/file/delete?file_path=uploads/images/test.jpg
            """
            full_path = Path(file_path)
            if not full_path.is_absolute():
                full_path = Path(__file__).parent.parent.parent.parent / file_path
            
            if not full_path.exists():
                raise HTTPException(status_code=404, detail="文件不存在")
            
            try:
                FileUtil.delete_file(full_path)
                return self.success(message="文件删除成功")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")
