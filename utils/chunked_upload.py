"""分片上传管理器

解决两个真实场景：

1. **大文件**：单次 ``multipart/form-data`` 上传 500MB 视频，一旦网络抖动就从头再来；
2. **弱网**：移动端在地铁、电梯里上传，重试成本必须可控。

把文件切成固定大小的分片，逐片上传，服务端记录已收到的分片，客户端断线后
只补缺失的部分。最后服务端按序合并成完整文件。

存储布局（全部落在上传根目录内，便于统一清理与备份）::

    uploads/
      .chunks/
        <upload_id>/
          meta.json     会话信息与已接收分片索引
          0.part        分片文件
          1.part
          ...

为什么用文件而不是缓存存 meta：
    缓存重启会丢，而分片文件还在磁盘上——两者不一致会留下永远删不掉的
    残片。meta 与分片同目录，删除会话即删目录，不存在孤儿。

并发说明：
    同一 ``upload_id`` 的分片写入是"写临时文件 + 原子替换"，重复上传同一分片
    是幂等的。但 ``complete`` 未加跨进程锁，同一会话被并发 complete 时可能
    都执行合并。客户端应避免并发 complete（重试前先查 status），强一致场景
    可在外层加分布式锁。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import UploadFile

from config.upload import UPLOAD_CONFIG
from utils.file import FileUtil

# upload_id 由服务端生成，只允许 32 位十六进制（不接受客户端构造）
_UPLOAD_ID_RE = re.compile(r"^[0-9a-f]{32}$")

# 流式写入分片时的单次读取大小
_IO_BLOCK = 1024 * 1024

# meta 文件名
_META_NAME = "meta.json"


class ChunkedUploadError(ValueError):
    """分片上传的业务异常

    控制器捕获后转成 4xx，而不是 500——这些是客户端可修正的错误
    （分片大小不对、序号越界、会话过期等）。
    """


def _chunked_config() -> Dict[str, Any]:
    """读取分片上传配置（带默认值，避免环境模板缺项时崩溃）"""
    cfg = UPLOAD_CONFIG
    return {
        "enabled": cfg.get("chunked_upload_enabled", True),
        "preferred_size": cfg.get("chunked_preferred_size", 2 * 1024 * 1024),
        "max_chunk_size": cfg.get("chunked_max_chunk_size", 8 * 1024 * 1024),
        "max_total_size": cfg.get("chunked_max_total_size", 2 * 1024 * 1024 * 1024),
        "max_chunks": cfg.get("chunked_max_chunks", 10000),
        "session_ttl": cfg.get("chunked_session_ttl", 24 * 3600),
    }


class ChunkedUploadManager:
    """分片上传会话管理

    所有方法都是类方法，无状态——会话信息全部写在磁盘上，
    因此多 worker 部署下各进程看到的是同一份数据。
    """

    CHUNK_DIR_NAME = ".chunks"

    # ------------------------------------------------------------------
    # 路径与元信息
    # ------------------------------------------------------------------

    @classmethod
    def _chunk_root(cls) -> Path:
        """分片临时目录（每次调用重算，支持测试注入上传目录）"""
        return FileUtil.get_upload_root() / cls.CHUNK_DIR_NAME

    @classmethod
    def _session_dir(cls, upload_id: str) -> Path:
        return cls._chunk_root() / upload_id

    @classmethod
    def _meta_path(cls, upload_id: str) -> Path:
        return cls._session_dir(upload_id) / _META_NAME

    @classmethod
    def _read_meta(cls, upload_id: str) -> Optional[Dict[str, Any]]:
        if not _UPLOAD_ID_RE.match(upload_id):
            return None
        path = cls._meta_path(upload_id)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    @classmethod
    def _write_meta(cls, upload_id: str, meta: Dict[str, Any]) -> None:
        """原子写入 meta，避免中断留下半个 JSON"""
        path = cls._meta_path(upload_id)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)

    @classmethod
    def _require_session(cls, upload_id: str) -> Dict[str, Any]:
        """取会话，不存在或已过期则报错"""
        meta = cls._read_meta(upload_id)
        if meta is None:
            raise ChunkedUploadError("上传会话不存在或已过期，请重新初始化")

        ttl = _chunked_config()["session_ttl"]
        if time.time() - float(meta.get("created_at", 0)) > ttl:
            cls._destroy(upload_id)
            raise ChunkedUploadError("上传会话已过期，请重新初始化")

        return meta

    @classmethod
    def _destroy(cls, upload_id: str) -> None:
        """删除会话目录（meta + 所有分片）"""
        if not _UPLOAD_ID_RE.match(upload_id):
            return
        shutil.rmtree(cls._session_dir(upload_id), ignore_errors=True)

    @classmethod
    def _cleanup_expired(cls) -> int:
        """清理过期会话，返回清理数量

        在 init 时顺带执行：客户端放弃上传后不会留下永久残片，
        也不需要额外的定时任务（一人公司场景，少一个运维组件就少一处故障点）。
        """
        root = cls._chunk_root()
        if not root.exists():
            return 0

        ttl = _chunked_config()["session_ttl"]
        now = time.time()
        removed = 0
        for entry in root.iterdir():
            if not entry.is_dir():
                continue
            meta_file = entry / _META_NAME
            try:
                if meta_file.exists():
                    created = float(
                        json.loads(meta_file.read_text(encoding="utf-8")).get("created_at", 0)
                    )
                else:
                    # 没有 meta 的目录只能是中断残留，按目录时间判断
                    created = entry.stat().st_mtime
                if now - created > ttl:
                    shutil.rmtree(entry, ignore_errors=True)
                    removed += 1
            except (OSError, ValueError):
                continue
        return removed

    # ------------------------------------------------------------------
    # 会话生命周期
    # ------------------------------------------------------------------

    @classmethod
    def init(
        cls,
        filename: str,
        total_size: int,
        chunk_size: Optional[int] = None,
        category: str = "files",
    ) -> Dict[str, Any]:
        """初始化分片上传会话

        Args:
            filename: 原始文件名（只用于取扩展名与回显，最终文件名会被重写）
            total_size: 文件总字节数
            chunk_size: 客户端计划使用的分片大小；不传则用服务端推荐值
            category: 上传分类（images / documents / files / videos 或自定义合法值）

        Returns:
            Dict: 含 upload_id、chunk_size、total_chunks、expires_in

        Raises:
            ChunkedUploadError: 参数非法或超出限制
        """
        cfg = _chunked_config()
        if not cfg["enabled"]:
            raise ChunkedUploadError("服务端未启用分片上传，请使用普通上传接口")

        try:
            total_size = int(total_size)
        except (TypeError, ValueError) as exc:
            raise ChunkedUploadError("total_size 必须是整数") from exc

        if total_size <= 0:
            raise ChunkedUploadError("total_size 必须大于 0")
        if total_size > cfg["max_total_size"]:
            limit_mb = cfg["max_total_size"] / 1024 / 1024
            raise ChunkedUploadError(f"文件超过分片上传上限 {limit_mb:.0f}MB")

        size = int(chunk_size or cfg["preferred_size"])
        if size <= 0 or size > cfg["max_chunk_size"]:
            raise ChunkedUploadError(
                f"chunk_size 必须在 1~{cfg['max_chunk_size']} 字节之间"
            )

        total_chunks = (total_size + size - 1) // size
        if total_chunks > cfg["max_chunks"]:
            raise ChunkedUploadError(
                f"分片数量 {total_chunks} 超过上限 {cfg['max_chunks']}，请增大 chunk_size"
            )

        # 扩展名校验复用普通上传的配置，避免两套规则不一致
        ext = Path(filename or "").suffix.lower()
        allowed = UPLOAD_CONFIG.get("allowed_extensions")
        if allowed and ext not in allowed:
            raise ChunkedUploadError(f"不支持的文件类型: {ext or '(无扩展名)'}")

        # 分类校验复用 FileUtil 的规则（防路径穿越）
        category = FileUtil.normalize_category(category)

        cls._cleanup_expired()

        upload_id = uuid.uuid4().hex
        session_dir = cls._session_dir(upload_id)
        session_dir.mkdir(parents=True, exist_ok=True)

        meta = {
            "upload_id": upload_id,
            "filename": Path(filename or "unnamed").name,
            "total_size": total_size,
            "chunk_size": size,
            "total_chunks": total_chunks,
            "category": category,
            "created_at": time.time(),
            "received": [],
        }
        cls._write_meta(upload_id, meta)

        return {
            "upload_id": upload_id,
            "chunk_size": size,
            "total_chunks": total_chunks,
            "expires_in": cfg["session_ttl"],
            "received": [],
        }

    @classmethod
    def status(cls, upload_id: str) -> Dict[str, Any]:
        """查询会话状态，用于断点续传：客户端据此只补缺失分片"""
        meta = cls._require_session(upload_id)
        received = sorted(int(i) for i in meta.get("received", []))
        missing = [i for i in range(meta["total_chunks"]) if i not in set(received)]
        return {
            "upload_id": upload_id,
            "filename": meta["filename"],
            "total_size": meta["total_size"],
            "chunk_size": meta["chunk_size"],
            "total_chunks": meta["total_chunks"],
            "received": received,
            "missing": missing,
            "completed": False,
        }

    @classmethod
    async def save_chunk(
        cls,
        upload_id: str,
        index: int,
        file: UploadFile,
    ) -> Dict[str, Any]:
        """保存单个分片

        同一分片重复上传是幂等的（覆盖写），客户端重试无需特殊处理。

        Args:
            upload_id: 会话 ID
            index: 分片序号，从 0 开始
            file: 分片内容

        Returns:
            Dict: 进度信息

        Raises:
            ChunkedUploadError: 会话无效、序号越界或分片大小不符
        """
        meta = cls._require_session(upload_id)

        try:
            index = int(index)
        except (TypeError, ValueError) as exc:
            raise ChunkedUploadError("index 必须是整数") from exc

        total_chunks = meta["total_chunks"]
        if index < 0 or index >= total_chunks:
            raise ChunkedUploadError(f"index 必须在 0~{total_chunks - 1} 之间")

        expected = cls._expected_size(meta, index)
        chunk_path = cls._session_dir(upload_id) / f"{index}.part"
        tmp_path = chunk_path.with_suffix(".part.tmp")

        written = 0
        try:
            with open(tmp_path, "wb") as out:
                while True:
                    block = await file.read(_IO_BLOCK)
                    if not block:
                        break
                    written += len(block)
                    # 提前拦截超大分片，避免恶意客户端把磁盘写满
                    if written > expected:
                        raise ChunkedUploadError(
                            f"分片 {index} 超出预期大小 {expected} 字节"
                        )
                    out.write(block)
        except ChunkedUploadError:
            tmp_path.unlink(missing_ok=True)
            raise
        except OSError as exc:
            tmp_path.unlink(missing_ok=True)
            raise ChunkedUploadError(f"分片写入失败: {exc}") from exc

        if written != expected:
            tmp_path.unlink(missing_ok=True)
            raise ChunkedUploadError(
                f"分片 {index} 大小不符：期望 {expected} 字节，实际 {written} 字节"
            )

        os.replace(tmp_path, chunk_path)

        received = {int(i) for i in meta.get("received", [])}
        received.add(index)
        meta["received"] = sorted(received)
        cls._write_meta(upload_id, meta)

        return {
            "upload_id": upload_id,
            "index": index,
            "received": meta["received"],
            "received_count": len(meta["received"]),
            "total_chunks": total_chunks,
            "completed": len(meta["received"]) == total_chunks,
        }

    @classmethod
    def complete(cls, upload_id: str) -> Dict[str, Any]:
        """合并所有分片为最终文件

        合并走流式拷贝，内存占用与文件大小无关；合并完成后删除整个会话目录。

        Returns:
            Dict: 与 ``FileUtil.upload`` 一致的结构，客户端处理方式无需区分

        Raises:
            ChunkedUploadError: 会话无效或分片缺失
        """
        meta = cls._require_session(upload_id)
        total_chunks = meta["total_chunks"]

        missing = [
            i
            for i in range(total_chunks)
            if not (cls._session_dir(upload_id) / f"{i}.part").exists()
        ]
        if missing:
            preview = missing[:10]
            suffix = "…" if len(missing) > 10 else ""
            raise ChunkedUploadError(
                f"还有 {len(missing)} 个分片未上传：{preview}{suffix}"
            )

        filename = FileUtil.generate_filename(meta["filename"])
        subdir = FileUtil.generate_subdir(meta["category"])
        target_dir = FileUtil.get_upload_root() / subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / filename
        # 先写到临时名再原子替换：中途失败不会留下"看起来完整"的半个文件
        merging = target.with_name(target.name + ".merging")

        total_written = 0
        try:
            with open(merging, "wb") as out:
                for i in range(total_chunks):
                    part = cls._session_dir(upload_id) / f"{i}.part"
                    with open(part, "rb") as src:
                        shutil.copyfileobj(src, out, _IO_BLOCK)
                    total_written += part.stat().st_size
        except OSError as exc:
            merging.unlink(missing_ok=True)
            raise ChunkedUploadError(f"合并失败: {exc}") from exc

        if total_written != meta["total_size"]:
            merging.unlink(missing_ok=True)
            raise ChunkedUploadError(
                f"合并后大小不符：期望 {meta['total_size']} 字节，实际 {total_written} 字节"
            )

        os.replace(merging, target)

        try:
            relative_path = target.relative_to(FileUtil.PROJECT_ROOT).as_posix()
        except ValueError:
            # 上传目录位于项目外（独立数据盘）时返回绝对路径
            relative_path = target.as_posix()

        result = {
            "filename": filename,
            "original_filename": meta["filename"],
            "file_path": relative_path,
            "absolute_path": str(target),
            "file_size": total_written,
            "mime_type": FileUtil.get_mime_type(filename),
            "extension": Path(filename).suffix.lower(),
            # URL 与磁盘位置解耦，目录在项目外时也不会暴露绝对路径
            "url": FileUtil.build_url(subdir, filename),
        }

        cls._destroy(upload_id)
        return result

    @classmethod
    def abort(cls, upload_id: str) -> None:
        """取消上传并清理已上传分片"""
        cls._require_session(upload_id)
        cls._destroy(upload_id)

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    @staticmethod
    def _expected_size(meta: Dict[str, Any], index: int) -> int:
        """计算某个分片的预期字节数（最后一片通常小于 chunk_size）"""
        chunk_size = meta["chunk_size"]
        total_size = meta["total_size"]
        total_chunks = meta["total_chunks"]
        if index < total_chunks - 1:
            return chunk_size
        return total_size - chunk_size * (total_chunks - 1)
