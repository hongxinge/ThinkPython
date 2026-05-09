"""
ThinkPython 文件上传下载工具类

本模块提供完整的文件处理功能，包括：
- 文件上传（带格式验证、大小限制、文件名防重复）
- 文件下载（支持流式下载）
- 文件删除
- 文件信息获取
- 生成文件访问 URL

使用场景：
    1. 头像上传：用户上传头像图片
    2. 文档上传：上传合同、报告等文档文件
    3. 批量附件上传：上传多个附件文件
    4. 文件下载：用户下载已上传的文件

配置说明：
    文件上传配置通过 config/upload.py 管理，包括：
    - 上传目录路径
    - 允许的文件类型
    - 文件大小限制
    - 文件命名规则

依赖安装：
    pip install python-multipart  # FastAPI 文件上传支持

使用示例：
    from utils.file import FileUtil
    
    # 上传文件
    @router.post("/upload")
    async def upload_file(file: UploadFile = File(...)):
        result = await FileUtil.upload(file, "uploads/images")
        return {"url": result["url"], "filename": result["filename"]}
    
    # 下载文件
    @router.get("/download/{file_id}")
    async def download_file(file_id: int):
        file_info = await get_file_info(file_id)
        return FileUtil.create_download_response(file_info["path"])
"""
import os
import uuid
import hashlib
import mimetypes
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from datetime import datetime

from fastapi import UploadFile
from fastapi.responses import FileResponse, Response

try:
    from config.upload import UPLOAD_CONFIG
except ImportError:
    # 如果上传配置不存在，使用默认配置
    UPLOAD_CONFIG = {
        "upload_dir": "uploads",
        "max_file_size": 10 * 1024 * 1024,  # 10MB
        "allowed_extensions": None,  # None 表示不限制
        "allowed_mime_types": None,  # None 表示不限制
        "naming_rule": "uuid",  # uuid / timestamp / original
        "chunk_size": 8192,  # 8KB
    }


# ==============================
# 文件类型常量定义
# ==============================

# 图片文件
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".ico"}
IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp", "image/svg+xml"}

# 文档文件
DOCUMENT_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".csv"}
DOCUMENT_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/plain",
    "text/csv",
}

# 压缩文件
ARCHIVE_EXTENSIONS = {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"}

# 音频文件
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma"}

# 视频文件
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv", ".webm"}


class FileUtil:
    """文件上传下载工具类
    
    提供完整的文件处理功能，包括上传、下载、删除、信息获取等。
    
    文件命名规则（通过 UPLOAD_CONFIG["naming_rule"] 配置）：
    - "uuid": 使用 UUID 命名，避免文件名冲突（推荐）
    - "timestamp": 使用时间戳 + 随机字符串命名
    - "original": 保留原始文件名（可能冲突，不推荐）
    
    Attributes:
        DEFAULT_UPLOAD_DIR: 默认上传目录
        DEFAULT_MAX_SIZE: 默认最大文件大小（10MB）
        CHUNK_SIZE: 文件读写块大小（8KB）
    """
    
    # 默认上传目录（相对于项目根目录）
    DEFAULT_UPLOAD_DIR = UPLOAD_CONFIG.get("upload_dir", "uploads")
    
    # 默认最大文件大小（字节），默认 10MB
    DEFAULT_MAX_SIZE = UPLOAD_CONFIG.get("max_file_size", 10 * 1024 * 1024)
    
    # 文件读写块大小（字节），流式传输时使用
    CHUNK_SIZE = UPLOAD_CONFIG.get("chunk_size", 8192)
    
    # 文件命名规则：uuid / timestamp / original
    NAMING_RULE = UPLOAD_CONFIG.get("naming_rule", "uuid")
    
    @classmethod
    def generate_filename(cls, original_filename: str) -> str:
        """生成安全的文件名
        
        根据配置的命名规则生成新的文件名，避免文件名冲突和路径穿越攻击。
        
        Args:
            original_filename: 原始文件名
            
        Returns:
            str: 生成的安全文件名（包含扩展名）
            
        示例:
            >>> FileUtil.generate_filename("头像.png")
            "a1b2c3d4e5f67890abcdef1234567890.png"  # uuid 模式
        """
        # 提取文件扩展名
        ext = Path(original_filename).suffix.lower() if original_filename else ""
        
        if cls.NAMING_RULE == "uuid":
            # UUID 命名：a1b2c3d4e5f67890abcdef1234567890.ext
            return f"{uuid.uuid4().hex}{ext}"
        
        elif cls.NAMING_RULE == "timestamp":
            # 时间戳 + 随机字符串命名：20240101120000_abc123.ext
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            random_str = uuid.uuid4().hex[:6]
            return f"{timestamp}_{random_str}{ext}"
        
        elif cls.NAMING_RULE == "original":
            # 保留原始文件名，但进行安全处理
            safe_name = "".join(c for c in original_filename if c.isalnum() or c in "._-")
            return safe_name
        
        else:
            # 默认使用 UUID
            return f"{uuid.uuid4().hex}{ext}"
    
    @classmethod
    def generate_subdir(cls, category: str = "files") -> str:
        """生成子目录路径
        
        按日期组织文件目录结构，便于管理和清理。
        
        Args:
            category: 文件分类（images / documents / videos / files）
            
        Returns:
            str: 子目录路径，格式为 "category/YYYY/MM/DD"
            
        示例:
            >>> FileUtil.generate_subdir("images")
            "images/2024/01/01"
        """
        now = datetime.now()
        return f"{category}/{now.strftime('%Y/%m/%d')}"
    
    @classmethod
    async def validate_file(
        cls,
        file: UploadFile,
        allowed_extensions: Optional[set] = None,
        allowed_mime_types: Optional[set] = None,
        max_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """验证上传文件是否符合要求
        
        检查文件格式、MIME 类型、文件大小是否满足限制条件。
        
        Args:
            file: FastAPI 上传的文件对象
            allowed_extensions: 允许的文件扩展名集合，None 表示不限制
                例如: {".jpg", ".png", ".gif"}
            allowed_mime_types: 允许的 MIME 类型集合，None 表示不限制
                例如: {"image/jpeg", "image/png"}
            max_size: 最大文件大小（字节），None 表示使用默认限制
            
        Returns:
            Dict[str, Any]: 验证结果
            {
                "valid": True,
                "extension": ".jpg",
                "mime_type": "image/jpeg",
                "size": 102400
            }
            
        Raises:
            ValueError: 文件验证失败时抛出详细异常信息
        """
        if not file or not file.filename:
            raise ValueError("未选择文件")
        
        # 获取文件扩展名
        ext = Path(file.filename).suffix.lower()
        
        # 获取 MIME 类型
        mime_type = file.content_type or mimetypes.guess_type(file.filename)[0] or ""
        
        # 验证扩展名
        if allowed_extensions and ext not in allowed_extensions:
            ext_list = ", ".join(sorted(allowed_extensions))
            raise ValueError(f"不支持的文件格式: {ext}，仅支持: {ext_list}")
        
        # 验证 MIME 类型
        if allowed_mime_types and mime_type not in allowed_mime_types:
            raise ValueError(f"不支持的文件类型: {mime_type}")
        
        # 验证文件大小
        max_size = max_size or cls.DEFAULT_MAX_SIZE
        
        # 读取文件内容并检查大小
        content = await file.read()
        file_size = len(content)
        
        if file_size > max_size:
            max_mb = max_size / 1024 / 1024
            raise ValueError(f"文件大小超过限制: {max_mb:.1f}MB")
        
        # 将文件指针重置到开头，以便后续读取
        await file.seek(0)
        
        return {
            "valid": True,
            "extension": ext,
            "mime_type": mime_type,
            "size": file_size,
        }
    
    @classmethod
    async def upload(
        cls,
        file: UploadFile,
        upload_dir: Optional[str] = None,
        category: str = "files",
        allowed_extensions: Optional[set] = None,
        max_size: Optional[int] = None,
        custom_filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """上传文件
        
        将上传的文件保存到服务器，返回文件信息字典。
        
        Args:
            file: FastAPI 上传的文件对象
            upload_dir: 上传目录（相对于项目根目录），None 则使用默认目录
            category: 文件分类（images / documents / videos / files），用于生成子目录
            allowed_extensions: 允许的文件扩展名集合
                快捷方式：传入 "image" 自动使用 IMAGE_EXTENSIONS
                例如: {".jpg", ".png", ".gif"} 或 "image"
            max_size: 最大文件大小（字节）
            custom_filename: 自定义文件名（不传则自动生成）
            
        Returns:
            Dict[str, Any]: 文件信息字典
            {
                "filename": "a1b2c3d4.ext",           # 保存的文件名
                "original_filename": "头像.png",      # 原始文件名
                "file_path": "uploads/images/2024/01/01/a1b2c3d4.ext",  # 相对路径
                "absolute_path": "/absolute/path/to/file",  # 绝对路径
                "file_size": 102400,                 # 文件大小（字节）
                "mime_type": "image/png",            # MIME 类型
                "extension": ".png",                 # 扩展名
                "url": "/uploads/images/2024/01/01/a1b2c3d4.ext"  # 访问 URL
            }
            
        Raises:
            ValueError: 文件验证失败时抛出异常
            
        使用示例:
            # 上传图片
            result = await FileUtil.upload(
                file, 
                upload_dir="uploads/avatars",
                allowed_extensions=IMAGE_EXTENSIONS,
                max_size=2 * 1024 * 1024,  # 2MB
            )
            
            # 使用快捷分类
            result = await FileUtil.upload(file, category="image")
            
            # 限制文档类型
            result = await FileUtil.upload(
                file,
                category="documents",
                allowed_extensions=DOCUMENT_EXTENSIONS,
            )
        """
        # 解析 allowed_extensions 快捷方式
        if isinstance(allowed_extensions, str):
            shortcut_map = {
                "image": IMAGE_EXTENSIONS,
                "document": DOCUMENT_EXTENSIONS,
                "audio": AUDIO_EXTENSIONS,
                "video": VIDEO_EXTENSIONS,
            }
            allowed_extensions = shortcut_map.get(allowed_extensions.lower(), allowed_extensions)
        
        # 使用配置的默认限制
        if allowed_extensions is None and UPLOAD_CONFIG.get("allowed_extensions"):
            allowed_extensions = set(UPLOAD_CONFIG["allowed_extensions"])
        if max_size is None and UPLOAD_CONFIG.get("max_file_size"):
            max_size = UPLOAD_CONFIG["max_file_size"]
        
        # 验证文件
        validation = await cls.validate_file(file, allowed_extensions, max_size=max_size)
        
        # 确定上传目录
        if upload_dir is None:
            subdir = cls.generate_subdir(category)
            upload_dir = os.path.join(cls.DEFAULT_UPLOAD_DIR, subdir)
        
        # 确保目录存在
        os.makedirs(upload_dir, exist_ok=True)
        
        # 生成文件名
        if custom_filename:
            # 使用自定义文件名，但保留原扩展名
            ext = Path(file.filename).suffix.lower() if file.filename else ""
            filename = custom_filename + ext
        else:
            filename = cls.generate_filename(file.filename)
        
        # 保存文件路径
        file_path = os.path.join(upload_dir, filename)
        absolute_path = os.path.abspath(file_path)
        
        # 保存文件（流式写入，避免大文件占用过多内存）
        file_size = 0
        with open(absolute_path, "wb") as f:
            while True:
                chunk = await file.read(cls.CHUNK_SIZE)
                if not chunk:
                    break
                f.write(chunk)
                file_size += len(chunk)
        
        # 将文件指针重置到开头
        await file.seek(0)
        
        # 生成访问 URL（将路径转换为 URL 格式）
        url = "/" + file_path.replace(os.sep, "/").lstrip("/")
        
        return {
            "filename": filename,
            "original_filename": file.filename,
            "file_path": file_path,
            "absolute_path": absolute_path,
            "file_size": file_size,
            "mime_type": validation["mime_type"],
            "extension": validation["extension"],
            "url": url,
        }
    
    @classmethod
    async def upload_multiple(
        cls,
        files: List[UploadFile],
        upload_dir: Optional[str] = None,
        category: str = "files",
        allowed_extensions: Optional[set] = None,
        max_size: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """批量上传多个文件
        
        Args:
            files: 上传的文件列表
            upload_dir: 上传目录
            category: 文件分类
            allowed_extensions: 允许的文件扩展名
            max_size: 每个文件的最大大小
            
        Returns:
            List[Dict[str, Any]]: 每个文件的信息列表
            
        使用示例:
            @router.post("/upload-multiple")
            async def upload_multiple_files(files: List[UploadFile] = File(...)):
                results = await FileUtil.upload_multiple(files, category="images")
                return {"count": len(results), "files": results}
        """
        results = []
        for file in files:
            try:
                result = await cls.upload(
                    file,
                    upload_dir=upload_dir,
                    category=category,
                    allowed_extensions=allowed_extensions,
                    max_size=max_size,
                )
                results.append(result)
            except ValueError as e:
                results.append({
                    "filename": file.filename,
                    "error": str(e),
                })
        return results
    
    @classmethod
    def create_download_response(
        cls,
        file_path: Union[str, Path],
        filename: Optional[str] = None,
        inline: bool = False,
    ) -> FileResponse:
        """创建文件下载响应
        
        生成 FastAPI FileResponse，支持下载和在线预览两种模式。
        
        Args:
            file_path: 文件路径（绝对路径或相对于项目根目录）
            filename: 下载时显示的文件名，不传则使用原文件名
            inline: 是否内联显示（True = 浏览器直接预览，False = 下载文件）
            
        Returns:
            FileResponse: FastAPI 文件下载响应
            
        Raises:
            FileNotFoundError: 文件不存在
            
        使用示例:
            # 下载文件（浏览器弹出下载对话框）
            @router.get("/download/{file_id}")
            async def download(file_id: int):
                file_info = await get_file(file_id)
                return FileUtil.create_download_response(file_info["absolute_path"])
            
            # 在线预览图片/PDF
            @router.get("/preview/{file_id}")
            async def preview(file_id: int):
                file_info = await get_file(file_id)
                return FileUtil.create_download_response(
                    file_info["absolute_path"],
                    inline=True
                )
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 确定文件名
        if filename is None:
            filename = file_path.name
        
        # 确定媒体类型
        media_type, _ = mimetypes.guess_type(str(file_path))
        if media_type is None:
            media_type = "application/octet-stream"
        
        # 创建响应
        disposition = "inline" if inline else "attachment"
        
        response = FileResponse(
            path=str(file_path),
            filename=filename,
            media_type=media_type,
        )
        response.headers["Content-Disposition"] = f"{disposition}; filename={filename}"
        
        return response
    
    @classmethod
    def delete_file(cls, file_path: Union[str, Path]) -> bool:
        """删除文件
        
        Args:
            file_path: 要删除的文件路径
            
        Returns:
            bool: 删除成功返回 True，文件不存在返回 False
            
        Raises:
            PermissionError: 文件被占用无法删除
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return False
        
        try:
            file_path.unlink()
            return True
        except PermissionError:
            raise PermissionError(f"文件被占用，无法删除: {file_path}")
        except OSError as e:
            raise OSError(f"删除文件失败: {file_path}, 错误: {e}")
    
    @classmethod
    def get_file_info(cls, file_path: Union[str, Path]) -> Dict[str, Any]:
        """获取文件详细信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict[str, Any]: 文件信息
            {
                "filename": "example.jpg",
                "file_size": 102400,
                "mime_type": "image/jpeg",
                "extension": ".jpg",
                "created_at": "2024-01-01 12:00:00",
                "updated_at": "2024-01-01 12:00:00",
                "exists": True
            }
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {
                "filename": file_path.name,
                "exists": False,
            }
        
        stat = file_path.stat()
        mime_type, _ = mimetypes.guess_type(str(file_path))
        
        return {
            "filename": file_path.name,
            "file_size": stat.st_size,
            "mime_type": mime_type or "application/octet-stream",
            "extension": file_path.suffix.lower(),
            "created_at": datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "exists": True,
        }
    
    @classmethod
    def calculate_hash(cls, file_path: Union[str, Path], algorithm: str = "md5") -> str:
        """计算文件哈希值
        
        用于文件去重、完整性校验等场景。
        
        Args:
            file_path: 文件路径
            algorithm: 哈希算法（md5 / sha1 / sha256）
            
        Returns:
            str: 文件哈希值（十六进制字符串）
            
        使用示例:
            >>> FileUtil.calculate_hash("image.jpg")
            "d41d8cd98f00b204e9800998ecf8427e"
        """
        hash_func = hashlib.new(algorithm)
        
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(cls.CHUNK_SIZE)
                if not chunk:
                    break
                hash_func.update(chunk)
        
        return hash_func.hexdigest()
    
    @classmethod
    def get_upload_dir(cls, category: str = None) -> str:
        """获取上传目录的绝对路径
        
        Args:
            category: 文件分类（images / documents / files）
            
        Returns:
            str: 上传目录的绝对路径
        """
        if category:
            return os.path.abspath(os.path.join(cls.DEFAULT_UPLOAD_DIR, category))
        return os.path.abspath(cls.DEFAULT_UPLOAD_DIR)
    
    @classmethod
    def clean_empty_dirs(cls, base_dir: Optional[str] = None) -> int:
        """清理空目录
        
        递归删除指定目录下的所有空子目录。
        
        Args:
            base_dir: 要清理的目录路径，None 则使用默认上传目录
            
        Returns:
            int: 删除的空目录数量
        """
        if base_dir is None:
            base_dir = cls.get_upload_dir()
        
        base_dir = Path(base_dir)
        if not base_dir.exists():
            return 0
        
        deleted_count = 0
        
        # 从最深层开始向上清理
        for dir_path in sorted(base_dir.rglob("*"), reverse=True):
            if dir_path.is_dir():
                try:
                    if not any(dir_path.iterdir()):
                        dir_path.rmdir()
                        deleted_count += 1
                except OSError:
                    pass
        
        return deleted_count
