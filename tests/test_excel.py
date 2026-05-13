"""ThinkPython Excel 工具测试"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from utils.excel import ExcelUtil


class TestExcelConstants:
    def test_default_sheet_name(self):
        assert ExcelUtil.DEFAULT_SHEET_NAME == "Sheet1"

    def test_max_file_size(self):
        assert ExcelUtil.MAX_FILE_SIZE == 10 * 1024 * 1024

    def test_allowed_extensions(self):
        assert ".xlsx" in ExcelUtil.ALLOWED_EXTENSIONS
        assert ".xls" in ExcelUtil.ALLOWED_EXTENSIONS

    def test_header_style_structure(self):
        assert "font" in ExcelUtil.HEADER_STYLE
        assert "fill" in ExcelUtil.HEADER_STYLE
        assert "alignment" in ExcelUtil.HEADER_STYLE

    def test_default_column_width(self):
        assert ExcelUtil.DEFAULT_COLUMN_WIDTH == 18


class TestExcelValidateFile:
    def test_validate_existing_excel_file(self):
        tmp_path = tempfile.mktemp(suffix=".xlsx")
        Path(tmp_path).touch()
        try:
            result = ExcelUtil.validate_file(tmp_path)
            assert result is True
        finally:
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()

    def test_validate_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            ExcelUtil.validate_file("nonexistent.xlsx")

    def test_validate_invalid_extension(self):
        tmp_path = tempfile.mktemp(suffix=".txt")
        Path(tmp_path).touch()
        try:
            with pytest.raises(ValueError):
                ExcelUtil.validate_file(tmp_path)
        finally:
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()

    def test_validate_xls_extension(self):
        tmp_path = tempfile.mktemp(suffix=".xls")
        Path(tmp_path).touch()
        try:
            result = ExcelUtil.validate_file(tmp_path)
            assert result is True
        finally:
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()


class TestExcelWrite:
    def test_write_excel_basic(self):
        data = [
            {"username": "admin", "email": "admin@example.com"},
            {"username": "user1", "email": "user1@example.com"},
        ]
        headers = {"username": "用户名", "email": "邮箱"}
        tmp_path = tempfile.mktemp(suffix=".xlsx")
        try:
            output_path = ExcelUtil.write_excel(data, headers, tmp_path)
            assert Path(output_path).exists()
        finally:
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()

    def test_write_excel_empty_data(self):
        headers = {"username": "用户名"}
        tmp_path = tempfile.mktemp(suffix=".xlsx")
        try:
            with pytest.raises(ValueError, match="导出数据不能为空"):
                ExcelUtil.write_excel([], headers, tmp_path)
        finally:
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()

    def test_write_excel_with_title(self):
        data = [{"name": "张三"}]
        headers = {"name": "姓名"}
        tmp_path = tempfile.mktemp(suffix=".xlsx")
        try:
            output_path = ExcelUtil.write_excel(data, headers, tmp_path, title="测试标题")
            assert Path(output_path).exists()
        finally:
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()

    def test_write_excel_zebra_stripe_off(self):
        data = [{"name": "张三"}, {"name": "李四"}]
        headers = {"name": "姓名"}
        tmp_path = tempfile.mktemp(suffix=".xlsx")
        try:
            output_path = ExcelUtil.write_excel(data, headers, tmp_path, zebra_stripe=False)
            assert Path(output_path).exists()
        finally:
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()

    def test_write_excel_auto_width_off(self):
        data = [{"name": "张三"}]
        headers = {"name": "姓名"}
        tmp_path = tempfile.mktemp(suffix=".xlsx")
        try:
            output_path = ExcelUtil.write_excel(data, headers, tmp_path, auto_width=False)
            assert Path(output_path).exists()
        finally:
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()

    def test_write_excel_custom_sheet(self):
        data = [{"name": "张三"}]
        headers = {"name": "姓名"}
        tmp_path = tempfile.mktemp(suffix=".xlsx")
        try:
            output_path = ExcelUtil.write_excel(data, headers, tmp_path, sheet_name="用户数据")
            assert Path(output_path).exists()
        finally:
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()


class TestExcelRead:
    def test_read_excel_basic(self):
        data = [
            {"姓名": "张三", "年龄": 25},
            {"姓名": "李四", "年龄": 30},
        ]
        headers = {"姓名": "姓名", "年龄": "年龄"}
        tmp_path = tempfile.mktemp(suffix=".xlsx")
        try:
            ExcelUtil.write_excel(data, headers, tmp_path)
            result = ExcelUtil.read_excel(tmp_path)
            assert len(result) == 2
            assert result[0]["姓名"] == "张三"
            assert result[1]["年龄"] == 30
        finally:
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()

    def test_read_excel_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            ExcelUtil.read_excel("nonexistent.xlsx")

    def test_read_excel_invalid_extension(self):
        tmp_path = tempfile.mktemp(suffix=".txt")
        Path(tmp_path).touch()
        try:
            with pytest.raises(ValueError):
                ExcelUtil.read_excel(tmp_path)
        finally:
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()


class TestExcelReadWriteRoundtrip:
    def test_write_and_read_roundtrip(self):
        original_data = [
            {"name": "张三", "age": 25, "email": "zhang@example.com"},
            {"name": "李四", "age": 30, "email": "li@example.com"},
        ]
        headers = {"name": "name", "age": "age", "email": "email"}
        tmp_path = tempfile.mktemp(suffix=".xlsx")
        try:
            ExcelUtil.write_excel(original_data, headers, tmp_path)
            result = ExcelUtil.read_excel(tmp_path)
            assert len(result) == len(original_data)
            for orig, read_row in zip(original_data, result):
                for key in orig:
                    assert read_row[key] == orig[key]
        finally:
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()


class TestExcelColumnMapping:
    def test_read_with_mapping(self):
        data = [{"姓名": "张三", "年龄": 25}]
        headers = {"姓名": "姓名", "年龄": "年龄"}
        tmp_path = tempfile.mktemp(suffix=".xlsx")
        try:
            ExcelUtil.write_excel(data, headers, tmp_path)
            mapping = {"姓名": "name", "年龄": "age"}
            result = ExcelUtil.read_with_mapping(tmp_path, mapping)
            assert len(result) == 1
            assert result[0]["name"] == "张三"
            assert result[0]["age"] == 25
        finally:
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()

    def test_read_with_mapping_missing_column(self):
        data = [{"姓名": "张三"}]
        headers = {"姓名": "姓名"}
        tmp_path = tempfile.mktemp(suffix=".xlsx")
        try:
            ExcelUtil.write_excel(data, headers, tmp_path)
            mapping = {"姓名": "name", "不存在": "missing"}
            result = ExcelUtil.read_with_mapping(tmp_path, mapping)
            assert "name" in result[0]
            assert "missing" not in result[0]
        finally:
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()


class TestExcelColumnSummary:
    def test_get_column_summary_basic(self):
        data = [
            {"name": "张三", "age": 25},
            {"name": "李四", "age": 30},
            {"name": "王五", "age": 25},
        ]
        headers = {"name": "姓名", "age": "年龄"}
        summary = ExcelUtil.get_column_summary(data, headers)
        assert "name" in summary
        assert "age" in summary
        assert summary["name"]["non_null"] == 3
        assert summary["name"]["null"] == 0
        assert summary["name"]["unique"] == 3

    def test_get_column_summary_with_nulls(self):
        data = [
            {"name": "张三", "age": 25},
            {"name": None, "age": 30},
        ]
        headers = {"name": "姓名", "age": "年龄"}
        summary = ExcelUtil.get_column_summary(data, headers)
        assert summary["name"]["non_null"] == 1
        assert summary["name"]["null"] == 1

    def test_get_column_summary_number_type(self):
        data = [
            {"value": 10},
            {"value": 20},
            {"value": 30},
        ]
        headers = {"value": "值"}
        summary = ExcelUtil.get_column_summary(data, headers)
        assert summary["value"]["type"] == "number"

    def test_get_column_summary_string_type(self):
        data = [
            {"name": "张三"},
            {"name": "李四"},
        ]
        headers = {"name": "姓名"}
        summary = ExcelUtil.get_column_summary(data, headers)
        assert summary["name"]["type"] == "string"


class TestExcelDownloadResponse:
    def test_create_download_response(self):
        data = [{"name": "张三"}]
        headers = {"name": "姓名"}
        response = ExcelUtil.create_download_response(data, headers, "测试.xlsx")
        assert response is not None
        assert hasattr(response, "path")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
