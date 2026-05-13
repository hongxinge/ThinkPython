"""ThinkPython 文件工具测试"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from utils.file import FileUtil


# ============== 文件工具测试 ==============

class TestFileGenerateFilename:
    """文件名生成测试"""

    def test_generate_filename_uuid(self):
        """测试 UUID 命名"""
        original = FileUtil.NAMING_RULE
        try:
            FileUtil.NAMING_RULE = "uuid"
            filename = FileUtil.generate_filename("test.png")
            assert filename.endswith(".png")
            assert len(filename) == 32 + 4  # UUID hex (32) + extension (.png)
        finally:
            FileUtil.NAMING_RULE = original

    def test_generate_filename_timestamp(self):
        """测试时间戳命名"""
        original = FileUtil.NAMING_RULE
        try:
            FileUtil.NAMING_RULE = "timestamp"
            filename = FileUtil.generate_filename("test.jpg")
            assert filename.endswith(".jpg")
            # 格式: YYYYMMDDHHMMSS_XXXXXX.jpg
            assert len(filename) > 20
        finally:
            FileUtil.NAMING_RULE = original

    def test_generate_filename_original(self):
        """测试保留原始文件名"""
        original = FileUtil.NAMING_RULE
        try:
            FileUtil.NAMING_RULE = "original"
            filename = FileUtil.generate_filename("my_photo.png")
            assert filename == "my_photo.png"
        finally:
            FileUtil.NAMING_RULE = original

    def test_generate_filename_unsafe_characters(self):
        """测试不安全字符过滤"""
        original = FileUtil.NAMING_RULE
        try:
            FileUtil.NAMING_RULE = "original"
            filename = FileUtil.generate_filename("test@#$%^&.doc")
            assert "@" not in filename
            assert "#" not in filename
            assert "$" not in filename
        finally:
            FileUtil.NAMING_RULE = original

    def test_generate_filename_unknown_rule(self):
        """测试未知命名规则"""
        original = FileUtil.NAMING_RULE
        try:
            FileUtil.NAMING_RULE = "unknown"
            filename = FileUtil.generate_filename("test.txt")
            assert filename.endswith(".txt")
        finally:
            FileUtil.NAMING_RULE = original


class TestFileGenerateSubdir:
    """子目录生成测试"""

    def test_generate_subdir_default(self):
        """测试默认子目录"""
        subdir = FileUtil.generate_subdir()
        assert subdir.startswith("files/")

    def test_generate_subdir_images(self):
        """测试图片子目录"""
        subdir = FileUtil.generate_subdir("images")
        assert subdir.startswith("images/")

    def test_generate_subdir_documents(self):
        """测试文档子目录"""
        subdir = FileUtil.generate_subdir("documents")
        assert subdir.startswith("documents/")

    def test_generate_subdir_format(self):
        """测试子目录格式"""
        subdir = FileUtil.generate_subdir("test")
        parts = subdir.split("/")
        assert len(parts) == 4  # test/YYYY/MM/DD
        assert parts[0] == "test"
        assert len(parts[1]) == 4  # year
        assert len(parts[2]) == 2  # month
        assert len(parts[3]) == 2  # day


class TestFileValidate:
    """文件验证测试"""

    @pytest.mark.asyncio
    async def test_validate_file_success(self):
        """测试文件验证成功"""
        mock_file = AsyncMock()
        mock_file.filename = "test.jpg"
        mock_file.content_type = "image/jpeg"
        mock_file.read.return_value = b"fake content"
        mock_file.seek.return_value = None

        result = await FileUtil.validate_file(mock_file)
        assert result["valid"] is True
        assert result["extension"] == ".jpg"
        assert result["mime_type"] == "image/jpeg"

    @pytest.mark.asyncio
    async def test_validate_file_no_filename(self):
        """测试无文件名"""
        mock_file = AsyncMock()
        mock_file.filename = None

        with pytest.raises(ValueError, match="未选择文件"):
            await FileUtil.validate_file(mock_file)

    @pytest.mark.asyncio
    async def test_validate_file_extension_restricted(self):
        """测试扩展名限制"""
        mock_file = AsyncMock()
        mock_file.filename = "test.txt"
        mock_file.content_type = "text/plain"
        mock_file.read.return_value = b"fake content"
        mock_file.seek.return_value = None

        with pytest.raises(ValueError, match="不支持的文件格式"):
            await FileUtil.validate_file(mock_file, allowed_extensions={".jpg", ".png"})

    @pytest.mark.asyncio
    async def test_validate_file_mime_restricted(self):
        """测试 MIME 类型限制"""
        mock_file = AsyncMock()
        mock_file.filename = "test.jpg"
        mock_file.content_type = "text/plain"
        mock_file.read.return_value = b"fake content"
        mock_file.seek.return_value = None

        with pytest.raises(ValueError, match="不支持的文件类型"):
            await FileUtil.validate_file(mock_file, allowed_mime_types={"image/jpeg"})

    @pytest.mark.asyncio
    async def test_validate_file_size_limit(self):
        """测试文件大小限制"""
        mock_file = AsyncMock()
        mock_file.filename = "test.jpg"
        mock_file.content_type = "image/jpeg"
        mock_file.read.return_value = b"x" * 1000
        mock_file.seek.return_value = None

        with pytest.raises(ValueError, match="文件大小超过限制"):
            await FileUtil.validate_file(mock_file, max_size=500)


class TestFileUpload:
    """文件上传测试"""

    @pytest.mark.asyncio
    async def test_upload_single_file(self):
        original = FileUtil.NAMING_RULE
        try:
            FileUtil.NAMING_RULE = "uuid"
            with tempfile.TemporaryDirectory() as tmpdir:
                FileUtil.DEFAULT_UPLOAD_DIR = tmpdir

                content = b"test content"
                read_count = 0

                mock_file = AsyncMock()
                mock_file.filename = "test.jpg"
                mock_file.content_type = "image/jpeg"

                async def mock_read(size=-1):
                    nonlocal read_count
                    read_count += 1
                    if read_count <= 2:
                        return content
                    return b""

                mock_file.read.side_effect = mock_read
                mock_file.seek.return_value = None

                result = await FileUtil.upload(mock_file)

                assert "filename" in result
                assert "original_filename" in result
                assert "file_path" in result
                assert "url" in result
                assert result["original_filename"] == "test.jpg"
                assert result["file_size"] == len(content)
        finally:
            FileUtil.NAMING_RULE = original

    @pytest.mark.asyncio
    async def test_upload_with_custom_filename(self):
        """测试使用自定义文件名"""
        original = FileUtil.NAMING_RULE
        try:
            FileUtil.NAMING_RULE = "uuid"
            with tempfile.TemporaryDirectory() as tmpdir:
                FileUtil.DEFAULT_UPLOAD_DIR = tmpdir

                mock_file = AsyncMock()
                mock_file.filename = "test.jpg"
                mock_file.content_type = "image/jpeg"
                mock_file.read.side_effect = [b"test", b""]
                mock_file.seek.return_value = None

                result = await FileUtil.upload(mock_file, custom_filename="my_file")

                assert result["filename"].startswith("my_file")
                assert result["filename"].endswith(".jpg")
        finally:
            FileUtil.NAMING_RULE = original

    @pytest.mark.asyncio
    async def test_upload_with_extension_filter(self):
        """测试带扩展名过滤的上传"""
        with tempfile.TemporaryDirectory() as tmpdir:
            FileUtil.DEFAULT_UPLOAD_DIR = tmpdir

            mock_file = AsyncMock()
            mock_file.filename = "test.txt"
            mock_file.content_type = "text/plain"
            mock_file.read.return_value = b"content"
            mock_file.seek.return_value = None

            with pytest.raises(ValueError):
                await FileUtil.upload(mock_file, allowed_extensions={".jpg", ".png"})


class TestFileUploadMultiple:
    """批量上传测试"""

    @pytest.mark.asyncio
    async def test_upload_multiple_files(self):
        """测试批量上传"""
        with tempfile.TemporaryDirectory() as tmpdir:
            FileUtil.DEFAULT_UPLOAD_DIR = tmpdir
            original = FileUtil.NAMING_RULE
            try:
                FileUtil.NAMING_RULE = "uuid"
                files = []
                for i in range(3):
                    mock_file = AsyncMock()
                    mock_file.filename = f"test{i}.jpg"
                    mock_file.content_type = "image/jpeg"
                    mock_file.read.side_effect = [f"content{i}".encode(), b""]
                    mock_file.seek.return_value = None
                    files.append(mock_file)

                results = await FileUtil.upload_multiple(files)
                assert len(results) == 3
                for result in results:
                    assert "error" not in result
            finally:
                FileUtil.NAMING_RULE = original

    @pytest.mark.asyncio
    async def test_upload_multiple_with_errors(self):
        """测试批量上传包含错误"""
        with tempfile.TemporaryDirectory() as tmpdir:
            FileUtil.DEFAULT_UPLOAD_DIR = tmpdir

            mock_file1 = AsyncMock()
            mock_file1.filename = "test.jpg"
            mock_file1.content_type = "image/jpeg"
            mock_file1.read.side_effect = [b"content", b""]
            mock_file1.seek.return_value = None

            mock_file2 = AsyncMock()
            mock_file2.filename = None
            mock_file2.content_type = None

            results = await FileUtil.upload_multiple([mock_file1, mock_file2])
            assert len(results) == 2
            assert "error" in results[1]


class TestFileDownload:
    def test_create_download_response_existing_file(self):
        tmp_path = tempfile.mktemp(suffix=".jpg")
        Path(tmp_path).write_bytes(b"test content")
        try:
            response = FileUtil.create_download_response(tmp_path, filename="photo.jpg")
            assert response is not None
        finally:
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()

    def test_create_download_response_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            FileUtil.create_download_response("nonexistent.jpg", filename="test.jpg")

    def test_create_download_response_inline(self):
        tmp_path = tempfile.mktemp(suffix=".pdf")
        Path(tmp_path).touch()
        try:
            response = FileUtil.create_download_response(tmp_path, inline=True)
            assert response.headers["Content-Disposition"].startswith("inline")
        finally:
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()


class TestFileDelete:
    def test_delete_existing_file(self):
        tmp_path = tempfile.mktemp()
        Path(tmp_path).write_bytes(b"test content")
        result = FileUtil.delete_file(tmp_path)
        assert result is True
        assert not Path(tmp_path).exists()

    def test_delete_nonexistent_file(self):
        result = FileUtil.delete_file("nonexistent.txt")
        assert result is False

    def test_delete_file_permission_error(self):
        pass


class TestFileInfo:
    def test_get_file_info_existing(self):
        tmp_path = tempfile.mktemp(suffix=".txt")
        Path(tmp_path).write_bytes(b"test content")
        try:
            info = FileUtil.get_file_info(tmp_path)
            assert info["exists"] is True
            assert info["filename"].endswith(".txt")
            assert info["file_size"] > 0
            assert "mime_type" in info
            assert "created_at" in info
            assert "updated_at" in info
        finally:
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()

    def test_get_file_info_nonexistent(self):
        info = FileUtil.get_file_info("nonexistent.txt")
        assert info["exists"] is False
        assert info["filename"] == "nonexistent.txt"


class TestFileHash:
    def test_calculate_hash_md5(self):
        tmp_path = tempfile.mktemp()
        Path(tmp_path).write_bytes(b"hello world")
        try:
            hash1 = FileUtil.calculate_hash(tmp_path, "md5")
            hash2 = FileUtil.calculate_hash(tmp_path, "md5")
            assert hash1 == hash2
            assert len(hash1) == 32
        finally:
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()

    def test_calculate_hash_sha256(self):
        tmp_path = tempfile.mktemp()
        Path(tmp_path).write_bytes(b"hello world")
        try:
            hash1 = FileUtil.calculate_hash(tmp_path, "sha256")
            assert len(hash1) == 64
        finally:
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()

    def test_calculate_hash_different_content(self):
        tmp1 = tempfile.mktemp()
        tmp2 = tempfile.mktemp()
        Path(tmp1).write_bytes(b"hello")
        Path(tmp2).write_bytes(b"world")
        try:
            hash1 = FileUtil.calculate_hash(tmp1)
            hash2 = FileUtil.calculate_hash(tmp2)
            assert hash1 != hash2
        finally:
            if Path(tmp1).exists():
                Path(tmp1).unlink()
            if Path(tmp2).exists():
                Path(tmp2).unlink()


class TestFileUploadDir:
    def test_get_upload_dir(self):
        upload_dir = FileUtil.get_upload_dir()
        assert os.path.isabs(upload_dir)

    def test_get_upload_dir_with_category(self):
        upload_dir = FileUtil.get_upload_dir("images")
        assert "images" in upload_dir


class TestFileCleanEmptyDirs:
    """清理空目录测试"""

    def test_clean_empty_dirs(self):
        """测试清理空目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_dir = Path(tmpdir) / "empty" / "nested"
            empty_dir.mkdir(parents=True)

            count = FileUtil.clean_empty_dirs(tmpdir)
            assert count >= 1

    def test_clean_empty_dirs_nonexistent(self):
        """测试清理不存在的目录"""
        count = FileUtil.clean_empty_dirs("nonexistent/path")
        assert count == 0

    def test_clean_empty_dirs_with_content(self):
        """测试不清理有内容的目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_with_content = Path(tmpdir) / "with_content"
            dir_with_content.mkdir()
            (dir_with_content / "file.txt").write_text("content")

            count = FileUtil.clean_empty_dirs(tmpdir)
            assert count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
