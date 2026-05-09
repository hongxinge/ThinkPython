"""
ThinkPython Excel 导入导出工具类

本模块提供完整的 Excel 文件处理功能，包括：
- 读取 Excel 文件为字典列表
- 将数据导出为 Excel 文件
- 支持自定义表头映射和样式
- 支持从 FastAPI 上传的文件对象直接读取
- 生成 FastAPI 下载响应

使用场景：
    1. 批量导入数据：用户上传 Excel 文件，解析后批量写入数据库
    2. 报表导出：将数据库查询结果导出为 Excel 供用户下载
    3. 数据备份：定期导出系统数据为 Excel 文件

依赖安装：
    pip install openpyxl

使用示例：
    # 读取 Excel
    from utils.excel import ExcelUtil
    
    # 从文件路径读取
    data = ExcelUtil.read_excel("data.xlsx")
    
    # 从上传的文件对象读取（FastAPI 控制器中）
    @router.post("/import")
    async def import_data(file: UploadFile = File(...)):
        data = await ExcelUtil.read_from_upload(file)
        for row in data:
            print(row["name"], row["age"])
    
    # 导出 Excel 并返回下载响应
    @router.get("/export")
    async def export_data():
        data = [
            {"username": "张三", "email": "zhang@example.com"},
            {"username": "李四", "email": "li@example.com"},
        ]
        headers = {"username": "用户名", "email": "邮箱"}
        return ExcelUtil.create_download_response(data, headers, "用户列表.xlsx")
"""
import os
import tempfile
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from datetime import datetime

from fastapi import UploadFile
from fastapi.responses import FileResponse

try:
    from openpyxl import Workbook, load_workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
except ImportError:
    raise ImportError(
        "openpyxl 未安装，请运行: pip install openpyxl"
    )


class ExcelUtil:
    """Excel 导入导出工具类
    
    提供完整的 Excel 文件读写功能，包括：
    - 从文件路径/上传文件读取数据
    - 导出数据为带格式的 Excel 文件
    - 生成 FastAPI 下载响应
    
    Attributes:
        DEFAULT_SHEET_NAME: 默认工作表名称
        MAX_FILE_SIZE: 最大文件大小（10MB）
        ALLOWED_EXTENSIONS: 允许的文件扩展名
    """
    
    # 默认工作表名称
    DEFAULT_SHEET_NAME = "Sheet1"
    
    # 最大文件大小限制（字节），默认 10MB
    MAX_FILE_SIZE = 10 * 1024 * 1024
    
    # 允许的 Excel 文件扩展名
    ALLOWED_EXTENSIONS = {".xlsx", ".xls"}
    
    # 默认表头样式配置
    HEADER_STYLE = {
        "font": Font(name="微软雅黑", size=11, bold=True, color="FFFFFF"),
        "fill": PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid"),
        "alignment": Alignment(horizontal="center", vertical="center"),
    }
    
    # 默认数据行样式配置
    DATA_STYLE = {
        "font": Font(name="微软雅黑", size=10),
        "alignment": Alignment(horizontal="left", vertical="center"),
    }
    
    # 斑马纹填充颜色
    EVEN_ROW_FILL = PatternFill(start_color="D9E2F3", end_color="D9E2F3", fill_type="solid")
    ODD_ROW_FILL = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    
    # 默认边框样式
    BORDER = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )
    
    # 默认列宽
    DEFAULT_COLUMN_WIDTH = 18
    
    @classmethod
    def validate_file(cls, file_path: Union[str, Path]) -> bool:
        """验证 Excel 文件是否有效
        
        检查文件是否存在、扩展名是否正确。
        
        Args:
            file_path: Excel 文件路径
            
        Returns:
            bool: 文件有效返回 True，否则抛出异常
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式不支持
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        if file_path.suffix.lower() not in cls.ALLOWED_EXTENSIONS:
            raise ValueError(
                f"不支持的文件格式: {file_path.suffix}，"
                f"仅支持: {', '.join(cls.ALLOWED_EXTENSIONS)}"
            )
        
        return True
    
    @classmethod
    async def validate_upload_file(cls, file: UploadFile) -> bool:
        """验证上传的 Excel 文件是否有效
        
        Args:
            file: FastAPI 上传的文件对象
            
        Returns:
            bool: 文件有效返回 True
            
        Raises:
            ValueError: 文件格式不支持或文件大小超限
        """
        file_ext = Path(file.filename).suffix.lower() if file.filename else ""
        
        if file_ext not in cls.ALLOWED_EXTENSIONS:
            raise ValueError(
                f"不支持的文件格式: {file_ext}，"
                f"仅支持: {', '.join(cls.ALLOWED_EXTENSIONS)}"
            )
        
        # 检查文件大小
        content = await file.read()
        file_size = len(content)
        await file.seek(0)
        
        if file_size > cls.MAX_FILE_SIZE:
            max_mb = cls.MAX_FILE_SIZE / 1024 / 1024
            raise ValueError(f"文件大小超过限制: {max_mb}MB")
        
        return True
    
    @classmethod
    def read_excel(
        cls,
        file_path: Union[str, Path],
        sheet_name: Optional[str] = None,
        header_row: int = 1,
        start_row: int = 2,
    ) -> List[Dict[str, Any]]:
        """从文件路径读取 Excel 文件，返回字典列表
        
        将 Excel 表格数据转换为 Python 字典列表，每行对应一个字典。
        默认第一行为表头，从第二行开始读取数据。
        
        Args:
            file_path: Excel 文件路径
            sheet_name: 工作表名称，不传则读取第一个工作表
            header_row: 表头所在行号（从 1 开始），默认第 1 行
            start_row: 数据开始行号（从 1 开始），默认第 2 行
            
        Returns:
            List[Dict[str, Any]]: 数据列表，每个元素为一行数据的字典
            例如: [{"姓名": "张三", "年龄": 25}, {"姓名": "李四", "年龄": 30}]
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式不支持
            
        使用示例:
            >>> data = ExcelUtil.read_excel("users.xlsx")
            >>> print(data[0])
            {"username": "admin", "email": "admin@example.com"}
            
            >>> # 读取指定工作表，表头在第2行，数据从第3行开始
            >>> data = ExcelUtil.read_excel("data.xlsx", sheet_name="用户", 
            ...                             header_row=2, start_row=3)
        """
        cls.validate_file(file_path)
        
        wb = load_workbook(filename=str(file_path), read_only=True)
        
        # 选择工作表
        if sheet_name:
            ws = wb[sheet_name]
        else:
            ws = wb.active
        
        # 读取表头
        headers = []
        for cell in list(ws.rows)[header_row - 1]:
            headers.append(str(cell.value).strip() if cell.value else "")
        
        # 读取数据行
        data = []
        for row in list(ws.rows)[start_row - 1:]:
            row_data = {}
            for i, cell in enumerate(row):
                if i < len(headers) and headers[i]:
                    row_data[headers[i]] = cell.value
            # 跳过全空行
            if any(v is not None for v in row_data.values()):
                data.append(row_data)
        
        wb.close()
        return data
    
    @classmethod
    async def read_from_upload(
        cls,
        file: UploadFile,
        sheet_name: Optional[str] = None,
        header_row: int = 1,
        start_row: int = 2,
    ) -> List[Dict[str, Any]]:
        """从 FastAPI 上传的文件对象读取 Excel 数据
        
        直接读取上传的文件内容，无需先保存到本地。
        
        Args:
            file: FastAPI 上传的文件对象
            sheet_name: 工作表名称
            header_row: 表头所在行号
            start_row: 数据开始行号
            
        Returns:
            List[Dict[str, Any]]: 数据字典列表
            
        Raises:
            ValueError: 文件格式不支持或文件大小超限
            
        使用示例:
            @router.post("/import")
            async def import_users(file: UploadFile = File(...)):
                data = await ExcelUtil.read_from_upload(file)
                for row in data:
                    await user_service.create(row)
                return {"message": f"导入 {len(data)} 条数据"}
        """
        await cls.validate_upload_file(file)
        
        # 将上传的文件内容读取到临时文件
        content = await file.read()
        
        with tempfile.NamedTemporaryFile(
            suffix=Path(file.filename).suffix if file.filename else ".xlsx",
            delete=False,
        ) as tmp_file:
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            return cls.read_excel(tmp_file_path, sheet_name, header_row, start_row)
        finally:
            # 清理临时文件
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
    
    @classmethod
    async def read_with_mapping_from_upload(
        cls,
        file: UploadFile,
        column_mapping: Dict[str, str],
        sheet_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """从上传的文件读取 Excel 并映射列名
        
        将 Excel 中的列名映射为自定义的键名，便于与数据库字段对应。
        
        Args:
            file: FastAPI 上传的文件对象
            column_mapping: 列名映射字典，格式为 {"Excel列名": "目标键名"}
            sheet_name: 工作表名称
            
        Returns:
            List[Dict[str, Any]]: 映射后的数据字典列表
            
        使用示例:
            @router.post("/import")
            async def import_users(file: UploadFile = File(...)):
                mapping = {"姓名": "name", "年龄": "age"}
                data = await ExcelUtil.read_with_mapping_from_upload(file, mapping)
        """
        await cls.validate_upload_file(file)
        
        # 将上传的文件内容读取到临时文件
        content = await file.read()
        
        with tempfile.NamedTemporaryFile(
            suffix=Path(file.filename).suffix if file.filename else ".xlsx",
            delete=False,
        ) as tmp_file:
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            return cls.read_with_mapping(tmp_file_path, column_mapping, sheet_name)
        finally:
            # 清理临时文件
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
    
    @classmethod
    def read_with_mapping(
        cls,
        file_path: Union[str, Path],
        column_mapping: Dict[str, str],
        sheet_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """读取 Excel 并映射列名
        
        将 Excel 中的列名映射为自定义的键名，便于与数据库字段对应。
        
        Args:
            file_path: Excel 文件路径
            column_mapping: 列名映射字典，格式为 {"Excel列名": "目标键名"}
            sheet_name: 工作表名称
            
        Returns:
            List[Dict[str, Any]]: 映射后的数据字典列表
            
        使用示例:
            >>> mapping = {"姓名": "name", "年龄": "age", "邮箱": "email"}
            >>> data = ExcelUtil.read_with_mapping("users.xlsx", mapping)
            >>> print(data[0])
            {"name": "张三", "age": 25, "email": "zhang@example.com"}
        """
        raw_data = cls.read_excel(file_path, sheet_name)
        
        mapped_data = []
        for row in raw_data:
            mapped_row = {}
            for excel_col, target_key in column_mapping.items():
                if excel_col in row:
                    mapped_row[target_key] = row[excel_col]
            mapped_data.append(mapped_row)
        
        return mapped_data
    
    @classmethod
    def write_excel(
        cls,
        data: List[Dict[str, Any]],
        headers: Dict[str, str],
        output_path: Union[str, Path],
        sheet_name: str = DEFAULT_SHEET_NAME,
        auto_width: bool = True,
        zebra_stripe: bool = True,
        title: Optional[str] = None,
    ) -> str:
        """将数据导出为 Excel 文件
        
        支持自定义表头、样式、斑马纹、标题行等功能。
        
        Args:
            data: 数据列表，每个元素为包含键值对的字典
            headers: 表头映射字典，格式为 {"字段名": "Excel列名"}
                例如: {"username": "用户名", "email": "邮箱"}
            output_path: 输出文件路径
            sheet_name: 工作表名称
            auto_width: 是否自动调整列宽
            zebra_stripe: 是否启用斑马纹（隔行变色）
            title: 标题行文字（可选，添加在表头上方）
            
        Returns:
            str: 生成的文件路径
            
        Raises:
            ValueError: 数据为空
            
        使用示例:
            >>> data = [
            ...     {"username": "admin", "email": "admin@example.com"},
            ...     {"username": "user1", "email": "user1@example.com"},
            ... ]
            >>> headers = {"username": "用户名", "email": "邮箱"}
            >>> ExcelUtil.write_excel(data, headers, "output.xlsx")
        """
        if not data:
            raise ValueError("导出数据不能为空")
        
        wb = Workbook()
        ws = wb.active
        ws.title = sheet_name
        
        current_row = 1
        
        # 添加标题行
        if title:
            ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
            title_cell = ws.cell(row=1, column=1, value=title)
            title_cell.font = Font(name="微软雅黑", size=14, bold=True)
            title_cell.alignment = Alignment(horizontal="center", vertical="center")
            current_row = 2
        
        # 写入表头
        header_columns = list(headers.keys())
        for col_idx, header_key in enumerate(header_columns, 1):
            cell = ws.cell(row=current_row, column=col_idx, value=headers[header_key])
            cell.font = cls.HEADER_STYLE["font"]
            cell.fill = cls.HEADER_STYLE["fill"]
            cell.alignment = cls.HEADER_STYLE["alignment"]
            cell.border = cls.BORDER
        
        # 写入数据行
        for row_idx, row_data in enumerate(data, current_row + 1):
            for col_idx, header_key in enumerate(header_columns, 1):
                value = row_data.get(header_key, "")
                # 处理 None 值
                if value is None:
                    value = ""
                # 处理日期类型
                if isinstance(value, datetime):
                    value = value.strftime("%Y-%m-%d %H:%M:%S")
                
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                cell.font = cls.DATA_STYLE["font"]
                cell.alignment = cls.DATA_STYLE["alignment"]
                cell.border = cls.BORDER
                
                # 斑马纹效果
                if zebra_stripe:
                    if (row_idx - current_row) % 2 == 0:
                        cell.fill = cls.EVEN_ROW_FILL
                    else:
                        cell.fill = cls.ODD_ROW_FILL
        
        # 自动调整列宽
        if auto_width:
            for col_idx in range(1, len(header_columns) + 1):
                max_length = 0
                column_letter = get_column_letter(col_idx)
                for row in ws.rows:
                    cell = row[col_idx - 1]
                    if cell.value:
                        cell_length = len(str(cell.value))
                        max_length = max(max_length, cell_length)
                # 设置列宽，最小 10，最大 50
                adjusted_width = min(max(max_length + 2, 10), 50)
                ws.column_dimensions[column_letter].width = adjusted_width
        else:
            for col_idx in range(1, len(header_columns) + 1):
                column_letter = get_column_letter(col_idx)
                ws.column_dimensions[column_letter].width = cls.DEFAULT_COLUMN_WIDTH
        
        # 冻结首行（标题行或表头行）
        freeze_row = 2 if title else 1
        ws.freeze_panes = ws.cell(row=freeze_row + 1, column=1)
        
        # 确保输出目录存在
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        wb.save(str(output_path))
        wb.close()
        
        return str(output_path)
    
    @classmethod
    def create_download_response(
        cls,
        data: List[Dict[str, Any]],
        headers: Dict[str, str],
        filename: str,
        sheet_name: str = DEFAULT_SHEET_NAME,
        auto_width: bool = True,
        zebra_stripe: bool = True,
        title: Optional[str] = None,
    ) -> FileResponse:
        """创建 Excel 下载响应（用于 FastAPI 接口返回）
        
        将数据导出为 Excel 文件并生成下载响应，浏览器会自动下载文件。
        
        Args:
            data: 数据列表
            headers: 表头映射字典 {"字段名": "Excel列名"}
            filename: 下载文件名（应包含 .xlsx 扩展名）
            sheet_name: 工作表名称
            auto_width: 是否自动调整列宽
            zebra_stripe: 是否启用斑马纹
            title: 标题行文字
            
        Returns:
            FileResponse: FastAPI 文件下载响应
            
        使用示例:
            @router.get("/export")
            async def export_users():
                users = await user_service.get_all()
                headers = {"username": "用户名", "email": "邮箱"}
                return ExcelUtil.create_download_response(
                    users, headers, "用户列表.xlsx",
                    title="用户数据导出"
                )
        """
        # 确保文件名有 .xlsx 扩展名
        if not filename.lower().endswith(".xlsx"):
            filename += ".xlsx"
        
        # 生成到临时文件
        temp_dir = Path(tempfile.gettempdir())
        output_path = temp_dir / f"temp_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        
        cls.write_excel(
            data=data,
            headers=headers,
            output_path=output_path,
            sheet_name=sheet_name,
            auto_width=auto_width,
            zebra_stripe=zebra_stripe,
            title=title,
        )
        
        # 创建下载响应（媒体类型设为 Excel 格式）
        response = FileResponse(
            path=str(output_path),
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        
        # 在响应完成后删除临时文件
        async def cleanup():
            """下载完成后清理临时文件"""
            if os.path.exists(output_path):
                os.unlink(output_path)
        
        response.background = cleanup
        
        return response
    
    @classmethod
    def get_column_summary(
        cls,
        data: List[Dict[str, Any]],
        headers: Dict[str, str],
    ) -> Dict[str, Dict[str, Any]]:
        """获取 Excel 列的统计摘要信息
        
        用于导入前预览数据，返回每列的数据类型、空值数量等统计信息。
        
        Args:
            data: 数据列表
            headers: 表头映射字典
            
        Returns:
            Dict[str, Dict]: 每列的统计信息
            例如: {
                "username": {"type": "str", "non_null": 100, "null": 0, "unique": 100},
                "age": {"type": "int", "non_null": 98, "null": 2, "unique": 50}
            }
        """
        summary = {}
        
        for field_key in headers.keys():
            values = [row.get(field_key) for row in data]
            non_null = sum(1 for v in values if v is not None)
            null_count = len(values) - non_null
            unique_values = len(set(str(v) for v in values if v is not None))
            
            # 判断数据类型
            sample_values = [v for v in values if v is not None][:10]
            if all(isinstance(v, (int, float)) for v in sample_values):
                col_type = "number"
            elif all(isinstance(v, datetime) for v in sample_values):
                col_type = "datetime"
            else:
                col_type = "string"
            
            summary[field_key] = {
                "label": headers[field_key],
                "type": col_type,
                "non_null": non_null,
                "null": null_count,
                "unique": unique_values,
            }
        
        return summary
