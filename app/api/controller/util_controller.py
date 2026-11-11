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
from pydantic import BaseModel, ConfigDict, Field

from core.base_controller import BaseController
from core.schema import ApiResponse, EmptyData
from utils.chunked_upload import ChunkedUploadError, ChunkedUploadManager
from utils.excel import ExcelUtil
from utils.file import FileUtil, IMAGE_EXTENSIONS, DOCUMENT_EXTENSIONS


# ==============================
# 分片上传请求/响应模型
# ==============================

class ChunkedInitRequest(BaseModel):
    """初始化分片上传请求体"""

    filename: str = Field(
        ..., description="原始文件名，用于取扩展名与回显", min_length=1, max_length=255
    )
    total_size: int = Field(..., gt=0, description="文件总字节数")
    chunk_size: Optional[int] = Field(
        None, gt=0, description="分片大小；不传则用服务端推荐值"
    )
    category: str = Field("files", description="文件分类：images/documents/files/videos")


class ChunkedInitData(BaseModel):
    """初始化结果"""

    upload_id: str = Field(..., description="会话 ID，后续所有接口都要带上")
    chunk_size: int = Field(..., description="分片大小（字节）")
    total_chunks: int = Field(..., description="分片总数")
    expires_in: int = Field(..., description="会话有效期（秒）")
    received: List[int] = Field(default_factory=list, description="已接收的分片序号")


class ChunkedStatusData(BaseModel):
    """会话状态（用于断点续传）"""

    upload_id: str = Field(..., description="会话 ID")
    filename: str = Field(..., description="原始文件名")
    total_size: int = Field(..., description="文件总字节数")
    chunk_size: int = Field(..., description="分片大小")
    total_chunks: int = Field(..., description="分片总数")
    received: List[int] = Field(default_factory=list, description="已接收的分片序号")
    missing: List[int] = Field(default_factory=list, description="仍缺失的分片序号")
    completed: bool = Field(False, description="是否已可合并")


class ChunkedChunkData(BaseModel):
    """单个分片的上传结果"""

    upload_id: str = Field(..., description="会话 ID")
    index: int = Field(..., description="本次上传的分片序号")
    received: List[int] = Field(default_factory=list, description="累计已接收的分片序号")
    received_count: int = Field(..., description="已接收分片数量")
    total_chunks: int = Field(..., description="分片总数")
    completed: bool = Field(..., description="是否所有分片都已到齐")


class ChunkedCompleteData(BaseModel):
    """合并结果，字段与普通上传接口一致"""

    filename: str = Field(..., description="服务端生成的文件名")
    original_filename: str = Field(..., description="客户端原始文件名")
    file_path: str = Field(..., description="相对项目根的文件路径")
    absolute_path: str = Field(..., description="绝对路径（服务端使用）")
    file_size: int = Field(..., description="文件字节数")
    mime_type: str = Field(..., description="MIME 类型")
    extension: str = Field(..., description="扩展名（含点）")
    url: str = Field(..., description="可直接访问的 URL 路径")


class ChunkedAbortData(BaseModel):
    """取消上传结果"""

    upload_id: str = Field(..., description="会话 ID")
    aborted: bool = Field(..., description="是否已清理")


class UploadResultItem(BaseModel):
    """批量上传中的单个结果；成功项含文件信息，失败项只有 filename 与 error"""

    model_config = ConfigDict(extra="allow")

    filename: str = Field(..., description="原始文件名")
    original_filename: Optional[str] = Field(None, description="服务端保存名")
    file_path: Optional[str] = Field(None, description="相对路径")
    absolute_path: Optional[str] = Field(None, description="服务端绝对路径")
    file_size: Optional[int] = Field(None, description="文件字节数")
    mime_type: Optional[str] = Field(None, description="MIME 类型")
    extension: Optional[str] = Field(None, description="扩展名")
    url: Optional[str] = Field(None, description="访问 URL")
    error: Optional[str] = Field(None, description="失败原因；成功时为 null")


class MultiUploadData(BaseModel):
    """批量上传汇总"""
    total: int = Field(..., description="提交文件数")
    success: int = Field(..., description="成功数")
    failed: int = Field(..., description="失败数")
    files: List[UploadResultItem] = Field(default_factory=list, description="逐文件结果")


class FileInfoData(BaseModel):
    """文件信息（GET /util/file/info）"""
    filename: str = Field(..., description="文件名")
    exists: bool = Field(..., description="文件是否存在")
    file_size: Optional[int] = Field(None, description="文件字节数")
    mime_type: Optional[str] = Field(None, description="MIME 类型")
    extension: Optional[str] = Field(None, description="扩展名")
    created_at: Optional[str] = Field(None, description="创建时间")
    updated_at: Optional[str] = Field(None, description="修改时间")


def _resolve_upload_path(file_path: str) -> Path:
    """解析并校验上传文件路径。

    客户端只允许访问上传根目录内的文件，越界或非法路径统一返回 403，
    避免通过绝对路径读取任意文件。
    """
    try:
        return FileUtil.resolve_upload_path(file_path)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


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
            headers = {
                "id": "ID",
                "name": "姓名",
                "email": "邮箱",
                "age": "年龄",
                "status": "状态",
            }
            data = [
                {"id": 1, "name": "张三", "email": "zhangsan@example.com", "age": 28, "status": "启用"},
                {"id": 2, "name": "李四", "email": "lisi@example.com", "age": 32, "status": "启用"},
                {"id": 3, "name": "王五", "email": "wangwu@example.com", "age": 25, "status": "禁用"},
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
        @self.router.post("/util/file/upload", summary="单文件上传", response_model=ApiResponse[ChunkedCompleteData])
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
        @self.router.post("/util/file/upload-multiple", summary="多文件上传", response_model=ApiResponse[MultiUploadData])
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
            try:
                results = await FileUtil.upload_multiple(files, category=category)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            
            success_count = sum(1 for r in results if "error" not in r)
            
            return self.success(data={
                "total": len(files),
                "success": success_count,
                "failed": len(files) - success_count,
                "files": results,
            })
        
        # ==============================
        # 分片上传接口（大文件 / 弱网断点续传）
        # ==============================
        # 流程：
        #   1. POST .../chunked/init      告诉服务端文件大小，拿到 upload_id 与分片规划
        #   2. POST .../chunked/chunk     逐片上传（可并发、可乱序、可重传）
        #   3. GET  .../chunked/status    断线后查询缺哪些分片（可选）
        #   4. POST .../chunked/complete  合并，返回与普通上传一致的字段
        #   放弃时 DELETE .../chunked/{upload_id} 立即释放磁盘

        @self.router.post(
            "/util/file/chunked/init",
            summary="初始化分片上传",
            response_model=ApiResponse[ChunkedInitData],
        )
        async def chunked_init(data: ChunkedInitRequest):
            """创建分片上传会话

            服务端返回 ``upload_id`` 与建议的分片规划。客户端按 ``chunk_size``
            切片，逐片调用 chunk 接口即可。若客户端已有更优的分片大小，
            可在请求里指定 ``chunk_size``。

            重复调用会创建新会话；断点续传请用同一个 ``upload_id`` 调 status。
            """
            try:
                result = ChunkedUploadManager.init(
                    filename=data.filename,
                    total_size=data.total_size,
                    chunk_size=data.chunk_size,
                    category=data.category,
                )
            except ChunkedUploadError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

            return self.success(data=result)

        @self.router.get(
            "/util/file/chunked/status",
            summary="查询分片上传状态",
            response_model=ApiResponse[ChunkedStatusData],
        )
        async def chunked_status(
            upload_id: str = Query(..., description="init 返回的 upload_id")
        ):
            """返回已接收与缺失的分片序号

            客户端断线重连后先调本接口，只补 ``missing`` 里的分片，
            不必从头重传。
            """
            try:
                return self.success(data=ChunkedUploadManager.status(upload_id))
            except ChunkedUploadError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc

        @self.router.post(
            "/util/file/chunked/chunk",
            summary="上传分片",
            response_model=ApiResponse[ChunkedChunkData],
        )
        async def chunked_upload_chunk(
            file: UploadFile = File(...),
            upload_id: str = Query(..., description="init 返回的 upload_id"),
            index: int = Query(..., ge=0, description="分片序号，从 0 开始"),
        ):
            """上传单个分片

            同一分片重复上传是幂等的（覆盖写），客户端重试无需特殊处理。
            分片可以乱序、可以并发；服务端按 index 落盘，合并时按序拼接。
            """
            try:
                result = await ChunkedUploadManager.save_chunk(upload_id, index, file)
            except ChunkedUploadError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

            return self.success(data=result)

        @self.router.post(
            "/util/file/chunked/complete",
            summary="合并分片",
            response_model=ApiResponse[ChunkedCompleteData],
        )
        async def chunked_complete(
            upload_id: str = Query(..., description="init 返回的 upload_id")
        ):
            """合并所有分片为最终文件

            返回结构与普通上传接口完全一致，客户端处理方式无需区分。
            合并成功后会删除临时分片；分片缺失时返回 400 并列出缺口，
            客户端补传后重试即可。
            """
            try:
                result = ChunkedUploadManager.complete(upload_id)
            except ChunkedUploadError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

            return self.success(data=result, message="上传完成")

        @self.router.delete(
            "/util/file/chunked/{upload_id}",
            summary="取消分片上传",
            response_model=ApiResponse[ChunkedAbortData],
        )
        async def chunked_abort(upload_id: str):
            """取消上传并立即释放已占用的磁盘空间"""
            try:
                ChunkedUploadManager.abort(upload_id)
            except ChunkedUploadError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc

            return self.success(data={"upload_id": upload_id, "aborted": True})

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
                full_path = _resolve_upload_path(file_path)
                
                return FileUtil.create_download_response(full_path, inline=True)
            except FileNotFoundError as e:
                raise HTTPException(status_code=404, detail=str(e))
        
        # ==============================
        # 文件管理相关接口
        # ==============================
        
        # 文件信息
        @self.router.get("/util/file/info", summary="获取文件信息", response_model=ApiResponse[FileInfoData])
        async def get_file_info(
            file_path: str = Query(..., description="文件路径")
        ):
            """获取文件详细信息
            
            Args:
                file_path: 文件路径
                
            Returns:
                Dict: 文件信息，包含大小、类型、创建时间等
            """
            full_path = _resolve_upload_path(file_path)
            
            info = FileUtil.get_file_info(full_path)
            
            if not info.get("exists"):
                raise HTTPException(status_code=404, detail="文件不存在")
            
            return self.success(data=info)
        
        # 文件删除
        @self.router.delete("/util/file/delete", summary="删除文件", response_model=ApiResponse[EmptyData])
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
            full_path = _resolve_upload_path(file_path)
            
            if not full_path.exists():
                raise HTTPException(status_code=404, detail="文件不存在")
            
            try:
                FileUtil.delete_file(full_path)
                return self.success(message="文件删除成功")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")
