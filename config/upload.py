"""
ThinkPython 上传配置文件

集中管理文件上传相关配置项，包括：
- 上传目录路径
- 允许的文件类型（扩展名和 MIME 类型）
- 文件大小限制
- 文件命名规则
- 分块传输大小

使用方式：
    直接在代码中导入使用：
    from config.upload import UPLOAD_CONFIG

注意事项：
    - 上传目录路径相对于项目根目录
    - 命名规则推荐使用 "uuid"，避免文件名冲突
    - 文件大小限制单位为字节
"""
import os

# 上传配置字典
UPLOAD_CONFIG = {
    # 上传目录（相对于项目根目录）
    "upload_dir": os.getenv("UPLOAD_DIR", "uploads"),
    
    # 最大文件大小（字节），默认 10MB
    "max_file_size": int(os.getenv("UPLOAD_MAX_FILE_SIZE", 10 * 1024 * 1024)),
    
    # 允许的文件扩展名，None 表示不限制
    # 如果需要限制，可以设置为集合：{".jpg", ".png", ".pdf"}
    "allowed_extensions": None,
    
    # 允许的 MIME 类型，None 表示不限制
    # 如果需要限制，可以设置为集合：{"image/jpeg", "image/png"}
    "allowed_mime_types": None,
    
    # 文件命名规则：
    # - "uuid": 使用 UUID 命名，完全避免冲突（推荐）
    # - "timestamp": 使用时间戳 + 随机字符串
    # - "original": 保留原始文件名（可能冲突，不推荐用于生产环境）
    "naming_rule": os.getenv("UPLOAD_NAMING_RULE", "uuid"),
    
    # 文件读写块大小（字节），流式传输时使用
    "chunk_size": 8192,  # 8KB
}
