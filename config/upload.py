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

    # 对外访问的 URL 前缀
    # 上传接口返回的 url 由此前缀 + 分类 + 日期 + 文件名拼接，
    # 与磁盘真实位置解耦：容器里 UPLOAD_DIR 可能是 /data/uploads（挂载卷），
    # 但对外仍应暴露为 /uploads/...，由 Nginx 映射到该目录。
    # 若由对象存储/CDN 提供访问，把它改成对应域名即可。
    "url_prefix": os.getenv("UPLOAD_URL_PREFIX", "/uploads"),
    
    # 最大文件大小（字节），默认 10MB
    "max_file_size": int(os.getenv("UPLOAD_MAX_FILE_SIZE", 10 * 1024 * 1024)),
    
    # 允许的文件扩展名，None 表示不限制
    # 如果需要限制，可以设置为集合：{".jpg", ".png", ".pdf"}
    # 生产环境强烈建议设置，避免上传 .php/.jsp/.exe 等可执行或脚本文件
    "allowed_extensions": None,
    
    # 允许的 MIME 类型，None 表示不限制
    # 如果需要限制，可以设置为集合：{"image/jpeg", "image/png"}
    # 校验在 FileUtil.validate_file 中执行，FileUtil.upload 会自动读取此项
    "allowed_mime_types": None,
    
    # 文件命名规则：
    # - "uuid": 使用 UUID 命名，完全避免冲突（推荐）
    # - "timestamp": 使用时间戳 + 随机字符串
    # - "original": 保留原始文件名（可能冲突，不推荐用于生产环境）
    "naming_rule": os.getenv("UPLOAD_NAMING_RULE", "uuid"),
    
    # 文件读写块大小（字节），流式传输时使用
    "chunk_size": 8192,  # 8KB

    # ---- 分片上传（大文件 / 弱网断点续传）----
    # 是否启用分片上传接口
    "chunked_upload_enabled": os.getenv("UPLOAD_CHUNKED_ENABLED", "true").lower() == "true",

    # 服务端推荐的分片大小（客户端未指定时使用），默认 2MB
    "chunked_preferred_size": int(os.getenv("UPLOAD_CHUNKED_PREFERRED_SIZE", 2 * 1024 * 1024)),

    # 单个分片允许的最大字节数，防止恶意客户端用超大"分片"塞满磁盘
    "chunked_max_chunk_size": int(os.getenv("UPLOAD_CHUNKED_MAX_CHUNK_SIZE", 8 * 1024 * 1024)),

    # 单个文件允许的最大总字节数，默认 2GB（不受 max_file_size 的 10MB 限制）
    "chunked_max_total_size": int(os.getenv("UPLOAD_CHUNKED_MAX_TOTAL_SIZE", 2 * 1024 * 1024 * 1024)),

    # 分片数量上限：避免 chunk_size 极小导致海量小文件拖垮文件系统
    "chunked_max_chunks": int(os.getenv("UPLOAD_CHUNKED_MAX_CHUNKS", 10000)),

    # 上传会话有效期（秒），过期后自动清理临时分片，默认 24 小时
    "chunked_session_ttl": int(os.getenv("UPLOAD_CHUNKED_SESSION_TTL", 24 * 3600)),
}
