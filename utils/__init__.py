"""
工具类
"""
from datetime import datetime
from typing import Any, Dict, List
import json


class JsonEncoder(json.JSONEncoder):
    """自定义JSON编码器"""
    
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        return super().default(obj)


def to_dict(obj: Any) -> Dict:
    """将对象转为字典"""
    if hasattr(obj, '__dict__'):
        return {key: value for key, value in obj.__dict__.items() if not key.startswith('_')}
    return {}


def to_json(obj: Any, **kwargs) -> str:
    """将对象转为JSON字符串"""
    return json.dumps(obj, cls=JsonEncoder, **kwargs)


def parse_json(json_str: str) -> Any:
    """解析JSON字符串"""
    return json.loads(json_str)
