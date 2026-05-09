# Excel 工具

ThinkPython 内置了 Excel 导入导出工具 `ExcelUtil`，支持读取、写入、列名映射、文件下载等功能。

## 安装依赖

```bash
pip install openpyxl
```

## 读取 Excel

### 从文件路径读取

```python
from utils.excel import ExcelUtil

# 默认第一行为表头，从第二行开始读取数据
data = ExcelUtil.read_excel("data.xlsx")
# 返回: [{"用户名": "张三", "邮箱": "zhang@example.com"}, ...]

# 读取指定工作表，自定义表头和数据起始行
data = ExcelUtil.read_excel("data.xlsx", sheet_name="用户", header_row=2, start_row=3)
```

### 从上传文件读取

```python
from fastapi import UploadFile, File
from utils.excel import ExcelUtil

@router.post("/import")
async def import_users(file: UploadFile = File(...)):
    data = await ExcelUtil.read_from_upload(file)
    
    # 批量创建用户
    for row in data:
        await user_service.create(row)
    
    return {"message": f"成功导入 {len(data)} 条数据"}
```

### 列名映射读取

将 Excel 中的中文列名映射为数据库字段名：

```python
@router.post("/import")
async def import_users(file: UploadFile = File(...)):
    mapping = {
        "姓名": "username",
        "邮箱": "email",
        "手机号": "mobile",
    }
    data = await ExcelUtil.read_with_mapping_from_upload(file, mapping)
    # 返回: [{"username": "张三", "email": "...", "mobile": "..."}, ...]
```

## 导出 Excel

### 写入文件

```python
from utils.excel import ExcelUtil

data = [
    {"username": "张三", "email": "zhang@example.com", "age": 25},
    {"username": "李四", "email": "li@example.com", "age": 30},
]

headers = {
    "username": "用户名",
    "email": "邮箱",
    "age": "年龄",
}

ExcelUtil.write_excel(data, headers, "output/用户列表.xlsx")
```

**可选参数：**

```python
ExcelUtil.write_excel(
    data=data,
    headers=headers,
    output_path="output.xlsx",
    sheet_name="用户数据",     # 工作表名称
    auto_width=True,          # 自动调整列宽
    zebra_stripe=True,        # 启用斑马纹
    title="用户数据导出",      # 标题行
)
```

### 创建下载响应

直接在接口中返回 Excel 文件供浏览器下载：

```python
from utils.excel import ExcelUtil

@router.get("/export/users", summary="导出用户列表")
async def export_users():
    users = await user_service.get_all()
    
    headers = {
        "username": "用户名",
        "email": "邮箱",
        "mobile": "手机号",
        "status": "状态",
        "created_at": "创建时间",
    }
    
    return ExcelUtil.create_download_response(
        data=users,
        headers=headers,
        filename="用户列表.xlsx",
        title="用户数据导出",
    )
```

浏览器会自动下载 `用户列表.xlsx` 文件。

## 数据统计摘要

导入前预览数据列的统计信息：

```python
data = ExcelUtil.read_excel("import.xlsx")
headers = {"姓名": "name", "年龄": "age"}

summary = ExcelUtil.get_column_summary(data, headers)
# 返回: {
#   "name": {"label": "用户名", "type": "string", "non_null": 100, "null": 0, "unique": 100},
#   "age": {"label": "年龄", "type": "number", "non_null": 98, "null": 2, "unique": 50}
# }
```

## 文件限制

- 支持格式：`.xlsx`, `.xls`
- 最大文件大小：10MB
- 自动清理临时文件

---

[← 返回首页](../README.md)
