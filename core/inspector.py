"""
ThinkPython 数据库表结构读取器

本模块用于连接数据库并读取表结构信息，支持：
- 获取所有表名
- 获取指定表的字段信息（名称、类型、是否必填、默认值、注释、是否主键等）
- 将表结构映射为 Python/SQLAlchemy 类型

主要用于 CLI 的 make-crud 命令，根据数据库表结构自动生成 CRUD 三层代码。

支持的数据库类型：MySQL, PostgreSQL, SQLite, MSSQL

使用示例:
    from core.inspector import DatabaseInspector
    
    inspector = DatabaseInspector()
    await inspector.connect()
    
    # 获取所有表
    tables = await inspector.get_tables()
    
    # 获取指定表的字段信息
    columns = await inspector.get_columns("user")
    
    await inspector.close()
"""
import asyncio
from typing import List, Dict, Any, Optional
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine


class ColumnInfo:
    """字段信息数据结构
    
    存储数据库中单个字段的元数据信息。
    
    Attributes:
        name: 字段名称
        type: 字段类型（SQL 类型，如 VARCHAR, INTEGER）
        python_type: 对应的 Python 类型（如 str, int）
        nullable: 是否允许为空
        default: 默认值
        comment: 字段注释
        is_primary: 是否为主键
        is_auto_increment: 是否自增
        max_length: 最大长度（字符串类型有效）
    """
    
    def __init__(
        self,
        name: str,
        type: str = "VARCHAR",
        python_type: str = "str",
        sqlalchemy_type: str = "String",
        nullable: bool = True,
        default: Optional[str] = None,
        comment: Optional[str] = None,
        is_primary: bool = False,
        is_auto_increment: bool = False,
        max_length: Optional[int] = None,
    ):
        self.name = name
        self.type = type.upper()
        self.python_type = python_type
        self.sqlalchemy_type = sqlalchemy_type
        self.nullable = nullable
        self.default = default
        self.comment = comment
        self.is_primary = is_primary
        self.is_auto_increment = is_auto_increment
        self.max_length = max_length
    
    def __repr__(self) -> str:
        return f"ColumnInfo(name='{self.name}', type='{self.type}')"


class TableInfo:
    """表信息数据结构
    
    存储数据库中单个表的元数据信息。
    
    Attributes:
        name: 表名称
        comment: 表注释
        columns: 字段列表（ColumnInfo 对象）
        primary_keys: 主键字段名列表
    """
    
    def __init__(self, name: str, comment: Optional[str] = None):
        self.name = name
        self.comment = comment
        self.columns: List[ColumnInfo] = []
        self.primary_keys: List[str] = []
    
    def add_column(self, column: ColumnInfo) -> None:
        """添加字段信息"""
        self.columns.append(column)
    
    def __repr__(self) -> str:
        return f"TableInfo(name='{self.name}', columns={len(self.columns)})"


# SQL 类型到 Python/SQLAlchemy 类型的映射
TYPE_MAP = {
    # 整数类型
    "TINYINT": {"python": "int", "sqlalchemy": "Integer"},
    "SMALLINT": {"python": "int", "sqlalchemy": "SmallInteger"},
    "MEDIUMINT": {"python": "int", "sqlalchemy": "Integer"},
    "INT": {"python": "int", "sqlalchemy": "Integer"},
    "INTEGER": {"python": "int", "sqlalchemy": "Integer"},
    "BIGINT": {"python": "int", "sqlalchemy": "BigInteger"},
    
    # 浮点类型
    "FLOAT": {"python": "float", "sqlalchemy": "Float"},
    "DOUBLE": {"python": "float", "sqlalchemy": "Float"},
    "DECIMAL": {"python": "Decimal", "sqlalchemy": "Numeric"},
    "NUMERIC": {"python": "Decimal", "sqlalchemy": "Numeric"},
    
    # 字符串类型
    "CHAR": {"python": "str", "sqlalchemy": "String"},
    "VARCHAR": {"python": "str", "sqlalchemy": "String"},
    "TINYTEXT": {"python": "str", "sqlalchemy": "Text"},
    "TEXT": {"python": "str", "sqlalchemy": "Text"},
    "MEDIUMTEXT": {"python": "str", "sqlalchemy": "Text"},
    "LONGTEXT": {"python": "str", "sqlalchemy": "Text"},
    
    # 时间类型
    "DATE": {"python": "date", "sqlalchemy": "Date"},
    "TIME": {"python": "time", "sqlalchemy": "Time"},
    "DATETIME": {"python": "datetime", "sqlalchemy": "DateTime"},
    "TIMESTAMP": {"python": "datetime", "sqlalchemy": "DateTime"},
    
    # 布尔类型
    "BOOLEAN": {"python": "bool", "sqlalchemy": "Boolean"},
    "BOOL": {"python": "bool", "sqlalchemy": "Boolean"},
    
    # 二进制类型
    "BLOB": {"python": "bytes", "sqlalchemy": "LargeBinary"},
    "BINARY": {"python": "bytes", "sqlalchemy": "LargeBinary"},
    
    # JSON 类型
    "JSON": {"python": "dict", "sqlalchemy": "JSON"},
    
    # PostgreSQL 特有类型
    "UUID": {"python": "str", "sqlalchemy": "String"},
    "INET": {"python": "str", "sqlalchemy": "String"},
    
    # SQLite 特有类型
    "REAL": {"python": "float", "sqlalchemy": "Float"},
    "NONE": {"python": "str", "sqlalchemy": "Text"},
    
    # MSSQL 特有类型
    "NVARCHAR": {"python": "str", "sqlalchemy": "String"},
    "NTEXT": {"python": "str", "sqlalchemy": "Text"},
    "UNIQUEIDENTIFIER": {"python": "str", "sqlalchemy": "String"},
}


class DatabaseInspector:
    """数据库表结构读取器
    
    连接数据库并读取表结构信息，支持 MySQL、PostgreSQL、SQLite、MSSQL。
    
    使用示例:
        inspector = DatabaseInspector()
        await inspector.connect()
        
        tables = await inspector.get_tables()
        print(f"数据库中有 {len(tables)} 个表")
        
        table = await inspector.get_table_info("user")
        for col in table.columns:
            print(f"  {col.name}: {col.type}")
        
        await inspector.close()
    """
    
    def __init__(self, db_url: Optional[str] = None):
        """初始化检测器
        
        Args:
            db_url: 数据库连接 URL，为 None 时自动从配置读取
        """
        self.db_url = db_url
        self.engine = None
        self._inspector = None
    
    async def connect(self) -> None:
        """连接数据库并初始化检测器"""
        if self.db_url is None:
            from config.database import get_database_url
            self.db_url = get_database_url()
        
        self.engine = create_async_engine(self.db_url, echo=False)
        sync_engine = self.engine.sync_engine
        self._inspector = inspect(sync_engine)
    
    async def close(self) -> None:
        """关闭数据库连接"""
        if self.engine:
            await self.engine.dispose()
    
    async def get_tables(self) -> List[str]:
        """获取所有表名
        
        Returns:
            List[str]: 数据库中的所有表名列表
        """
        return list(self._inspector.get_table_names())
    
    async def get_table_info(self, table_name: str) -> TableInfo:
        """获取指定表的完整信息
        
        Args:
            table_name: 表名称
            
        Returns:
            TableInfo: 表的结构信息，包含字段列表、主键等
        """
        table = TableInfo(table_name)
        
        # 获取主键
        pk_constraints = self._inspector.get_pk_constraint(table_name)
        table.primary_keys = pk_constraints.get("constrained_columns", [])
        
        # 获取字段信息
        columns = self._inspector.get_columns(table_name)
        
        for col in columns:
            col_name = col["name"]
            col_type = col["type"]
            
            # 提取类型名称（去除长度信息，如 VARCHAR(50) -> VARCHAR）
            type_str = str(col_type).split("(")[0].upper()
            
            # 提取长度信息
            max_length = None
            type_match = str(col_type)
            if "(" in type_match and ")" in type_match:
                try:
                    length_str = type_match.split("(")[1].split(")")[0]
                    max_length = int(length_str.split(",")[0])
                except (ValueError, IndexError):
                    pass
            
            # 映射 Python 和 SQLAlchemy 类型
            type_info = TYPE_MAP.get(type_str, {"python": "str", "sqlalchemy": "String"})
            
            # 检测自增
            is_auto = col.get("autoincrement", False)
            
            # 检测默认值
            default = col.get("default")
            if default is not None:
                default = str(default)
            
            # 检测注释（MySQL/PostgreSQL 支持）
            comment = col.get("comment")
            
            column_info = ColumnInfo(
                name=col_name,
                type=type_str,
                python_type=type_info["python"],
                sqlalchemy_type=type_info["sqlalchemy"],
                nullable=col.get("nullable", True),
                default=default,
                comment=comment,
                is_primary=col_name in table.primary_keys,
                is_auto_increment=is_auto,
                max_length=max_length,
            )
            table.add_column(column_info)
        
        # 尝试获取表注释
        try:
            table.comment = await self._get_table_comment(table_name)
        except Exception:
            pass
        
        return table
    
    async def _get_table_comment(self, table_name: str) -> Optional[str]:
        """获取表注释（仅 MySQL 支持）
        
        Args:
            table_name: 表名称
            
        Returns:
            Optional[str]: 表注释，不支持则返回 None
        """
        if "mysql" in self.db_url.lower():
            async with self.engine.connect() as conn:
                result = await conn.execute(text(
                    f"SELECT TABLE_COMMENT FROM information_schema.TABLES "
                    f"WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{table_name}'"
                ))
                row = result.fetchone()
                if row and row[0]:
                    return row[0]
        return None
    
    async def get_column_comments_mysql(self, table_name: str) -> Dict[str, str]:
        """获取 MySQL 表的字段注释
        
        Args:
            table_name: 表名称
            
        Returns:
            Dict[str, str]: {字段名: 注释} 字典
        """
        comments = {}
        if "mysql" in self.db_url.lower():
            async with self.engine.connect() as conn:
                result = await conn.execute(text(
                    f"SELECT COLUMN_NAME, COLUMN_COMMENT FROM information_schema.COLUMNS "
                    f"WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{table_name}'"
                ))
                for row in result.fetchall():
                    if row[1]:
                        comments[row[0]] = row[1]
        return comments
