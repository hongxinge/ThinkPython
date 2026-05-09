# 文件工具

ThinkPython 内置了文件上传下载工具 `FileUtil`，支持文件上传、批量上传、下载、删除、文件信息获取等功能。

## 安装依赖

```bash
pip install python-multipart
```

## 上传文件

### 单个文件上传

```python
from fastapi import UploadFile, File
from utils.file import FileUtil

@router.post("/upload/avatar")
async def upload_avatar(file: UploadFile = File(...)):
    result = await FileUtil.upload(
        file,
        category="images",                    # 文件分类，自动按日期生成子目录
        allowed_extensions={".jpg", ".png"},   # 允许的文件格式
        max_size=2 * 1024 * 1024,              # 最大 2MB
    )
    return result
```

返回结果：

```json
{
  "filename": "a1b2c3d4e5f67890.png",
  "original_filename": "头像.png",
  "file_path": "uploads/images/2024/01/15/a1b2c3d4e5f67890.png",
  "absolute_path": "/path/to/project/uploads/images/2024/01/15/a1b2c3d4e5f67890.png",
  "file_size": 51200,
  "mime_type": "image/png",
  "extension": ".png",
  "url": "/uploads/images/2024/01/15/a1b2c3d4e5f67890.png"
}
```

### 快捷上传

`allowed_extensions` 支持字符串快捷方式：

```python
# 快捷方式：传入 "image" 自动使用 IMAGE_EXTENSIONS
result = await FileUtil.upload(file, allowed_extensions="image")

# 其他快捷方式
result = await FileUtil.upload(file, allowed_extensions="document")  # 文档类
result = await FileUtil.upload(file, allowed_extensions="audio")     # 音频类
result = await FileUtil.upload(file, allowed_extensions="video")     # 视频类
```

### 自定义上传目录

```python
result = await FileUtil.upload(
    file,
    upload_dir="uploads/avatars",   # 指定固定目录
)
```

### 批量上传

```python
from typing import List

@router.post("/upload/multiple")
async def upload_files(files: List[UploadFile] = File(...)):
    results = await FileUtil.upload_multiple(
        files,
        category="documents",
        allowed_extensions={".pdf", ".doc", ".docx"},
    )
    return {"count": len(results), "files": results}
```

## 下载文件

### 下载（弹出保存对话框）

```python
@router.get("/download/{file_id}")
async def download_file(file_id: int):
    file_info = await get_file_info_from_db(file_id)
    return FileUtil.create_download_response(
        file_path=file_info["absolute_path"],
        filename=file_info["original_name"],
    )
```

### 在线预览

```python
@router.get("/preview/{file_id}")
async def preview_file(file_id: int):
    file_info = await get_file_info_from_db(file_id)
    return FileUtil.create_download_response(
        file_path=file_info["absolute_path"],
        inline=True,   # True = 浏览器直接预览
    )
```

## 删除文件

```python
success = FileUtil.delete_file("uploads/images/2024/01/15/a1b2c3d4.png")
if success:
    print("删除成功")
```

## 获取文件信息

```python
info = FileUtil.get_file_info("uploads/images/2024/01/15/a1b2c3d4.png")
# 返回:
# {
#   "filename": "a1b2c3d4.png",
#   "file_size": 51200,
#   "mime_type": "image/png",
#   "extension": ".png",
#   "created_at": "2024-01-15 12:00:00",
#   "updated_at": "2024-01-15 12:00:00",
#   "exists": True
# }
```

## 计算文件哈希值

```python
hash_value = FileUtil.calculate_hash("uploads/file.pdf", algorithm="md5")
# 可用于文件去重、完整性校验
```

## 清理空目录

```python
deleted_count = FileUtil.clean_empty_dirs()
# 递归删除 uploads/ 目录下所有空子目录
```

## 文件名命名规则

通过 `config/upload.py` 配置：

```python
UPLOAD_CONFIG = {
    "naming_rule": "uuid",      # uuid / timestamp / original
    "upload_dir": "uploads",
    "max_file_size": 10 * 1024 * 1024,  # 10MB
}
```

- `uuid`：`a1b2c3d4e5f67890abcdef1234567890.png`（推荐）
- `timestamp`：`20240115120000_abc123.png`
- `original`：保留原始文件名（可能冲突）

## 文件类型常量

```python
from utils.file import (
    IMAGE_EXTENSIONS,      # 图片格式
    DOCUMENT_EXTENSIONS,   # 文档格式
    AUDIO_EXTENSIONS,      # 音频格式
    VIDEO_EXTENSIONS,      # 视频格式
    ARCHIVE_EXTENSIONS,    # 压缩格式
)
```

---

[← 返回首页](../README.md)
