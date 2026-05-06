"""
助手函数 - 常用工具
"""
import hashlib
import random
import string
import time
from datetime import datetime
from typing import Any, Dict, List, Optional


def generate_token(length: int = 32) -> str:
    """生成随机token"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def md5(s: str) -> str:
    """MD5加密"""
    return hashlib.md5(s.encode('utf-8')).hexdigest()


def sha256(s: str) -> str:
    """SHA256加密"""
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def generate_order_no() -> str:
    """生成订单号"""
    return datetime.now().strftime('%Y%m%d%H%M%S') + ''.join(random.choices(string.digits, k=6))


def format_time(timestamp: Optional[float] = None, fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
    """格式化时间戳"""
    ts = timestamp or time.time()
    return datetime.fromtimestamp(ts).strftime(fmt)


def current_time() -> datetime:
    """获取当前时间"""
    return datetime.now()


def paginate(items: List[Any], page: int = 1, page_size: int = 10) -> Dict:
    """分页工具函数"""
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "items": items[start:end],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


def tree_data(items: List[Dict], id_key: str = 'id', parent_key: str = 'parent_id', children_key: str = 'children') -> List[Dict]:
    """将列表数据转为树形结构"""
    tree = []
    item_dict = {item[id_key]: item for item in items}
    
    for item in items:
        parent_id = item.get(parent_key)
        if parent_id and parent_id in item_dict:
            parent = item_dict[parent_id]
            if children_key not in parent:
                parent[children_key] = []
            parent[children_key].append(item)
        else:
            tree.append(item)
    
    return tree


def mask_string(s: str, start: int = 3, end: int = 4, mask_char: str = '*') -> str:
    """字符串脱敏"""
    if len(s) <= start + end:
        return mask_char * len(s)
    return s[:start] + mask_char * (len(s) - start - end) + s[-end:]
