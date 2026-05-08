"""
ThinkPython 常用助手函数

本模块提供项目中频繁使用的通用工具函数，包括：
- generate_token(): 生成随机 Token
- md5() / sha256(): 哈希加密函数
- generate_order_no(): 生成唯一订单号
- format_time() / current_time(): 时间处理函数
- paginate(): 内存分页工具
- tree_data(): 列表转树形结构
- mask_string(): 字符串脱敏

这些函数不涉及框架依赖，是纯工具函数，可以在任何场景下使用。
"""
import hashlib
import random
import string
import time
from datetime import datetime
from typing import Any, Dict, List, Optional


def generate_token(length: int = 32) -> str:
    """生成随机 Token 字符串
    
    使用大小写字母和数字的组合生成指定长度的随机字符串，
    适用于生成 API Token、验证码、重置密码链接等场景。
    
    Args:
        length: Token 长度，默认 32 个字符
        
    Returns:
        str: 随机 Token 字符串
        
    使用示例:
        generate_token()  # 'aB3dEf7hJk2mNp5qRt8uVw1xYz4cG6iL'
        generate_token(16)  # 'xK9mP2rT5wA8bD3f'
    """
    # 从大小写字母和数字中随机选择指定数量的字符
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def md5(s: str) -> str:
    """计算字符串的 MD5 哈希值
    
    MD5 是一种广泛使用的哈希算法，生成 32 位十六进制字符串。
    适用于文件校验、简单加密等场景（注意：MD5 不适合密码加密，推荐使用 bcrypt）。
    
    Args:
        s: 需要加密的字符串
        
    Returns:
        str: 32 位十六进制 MD5 哈希值
        
    使用示例:
        md5("hello")  # '5d41402abc4b2a76b9719d911017c592'
    """
    return hashlib.md5(s.encode('utf-8')).hexdigest()


def sha256(s: str) -> str:
    """计算字符串的 SHA256 哈希值
    
    SHA256 是一种更安全的哈希算法，生成 64 位十六进制字符串。
    比 MD5 更安全，适用于对安全性要求较高的场景。
    
    Args:
        s: 需要加密的字符串
        
    Returns:
        str: 64 位十六进制 SHA256 哈希值
        
    使用示例:
        sha256("hello")  # '2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824'
    """
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def generate_order_no() -> str:
    """生成唯一订单号
    
    订单号格式：YYYYMMDDHHmmss + 6 位随机数字
    例如：20240101120000123456
    - 前 14 位是时间戳，保证时间递增性
    - 后 6 位是随机数，保证同一秒内的唯一性
    
    Returns:
        str: 20 位订单号字符串
        
    使用示例:
        generate_order_no()  # '20240101120000123456'
    """
    # 当前时间格式化到秒 + 6 位随机数字
    return datetime.now().strftime('%Y%m%d%H%M%S') + ''.join(random.choices(string.digits, k=6))


def format_time(timestamp: Optional[float] = None, fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
    """格式化时间戳为可读字符串
    
    将 Unix 时间戳转换为指定格式的日期时间字符串。
    
    Args:
        timestamp: Unix 时间戳（秒），不传则使用当前时间
        fmt: 时间格式化字符串，默认 '%Y-%m-%d %H:%M:%S'
        
    Returns:
        str: 格式化后的时间字符串
        
    使用示例:
        format_time()  # '2024-01-01 12:00:00'
        format_time(1704067200)  # '2024-01-01 00:00:00'
        format_time(1704067200, '%Y/%m/%d')  # '2024/01/01'
    """
    ts = timestamp or time.time()
    return datetime.fromtimestamp(ts).strftime(fmt)


def current_time() -> datetime:
    """获取当前本地时间
    
    Returns:
        datetime: 当前时间的 datetime 对象
        
    使用示例:
        now = current_time()
        print(now.year, now.month, now.day)
    """
    return datetime.now()


def paginate(items: List[Any], page: int = 1, page_size: int = 10) -> Dict:
    """对列表数据进行内存分页
    
    适用于已加载到内存的数据列表的分页处理，
    如缓存中的数据、API 聚合结果等。
    注意：对于数据库查询，建议使用 BaseService.get_all() 进行数据库层面的分页。
    
    Args:
        items: 需要分页的完整数据列表
        page: 当前页码，从 1 开始
        page_size: 每页条数
        
    Returns:
        Dict: 分页结果字典，包含：
            - items: 当前页的数据切片
            - total: 总条数
            - page: 当前页码
            - page_size: 每页条数
            - total_pages: 总页数
            
    使用示例:
        users = [{"id": 1}, {"id": 2}, ..., {"id": 100}]
        result = paginate(users, page=1, page_size=10)
        # result["items"] 包含前 10 个用户
        # result["total_pages"] = 10
    """
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "items": items[start:end],  # 切片获取当前页数据
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,  # 向上取整
    }


def tree_data(items: List[Dict], id_key: str = 'id', parent_key: str = 'parent_id', children_key: str = 'children') -> List[Dict]:
    """将扁平列表数据转换为树形结构
    
    常用于菜单、部门、分类等具有层级关系的数据转换。
    输入数据需要包含 id 和 parent_id 字段来标识层级关系。
    
    Args:
        items: 扁平列表，每个元素是一个字典
        id_key: 唯一标识字段名，默认 'id'
        parent_key: 父节点标识字段名，默认 'parent_id'
        children_key: 子节点数组字段名，默认 'children'
        
    Returns:
        List[Dict]: 树形结构的数据列表，根节点的 parent_id 为 None 或不存在
        
    使用示例:
        data = [
            {"id": 1, "name": "总公司", "parent_id": None},
            {"id": 2, "name": "技术部", "parent_id": 1},
            {"id": 3, "name": "前端组", "parent_id": 2},
        ]
        tree_data(data)
        # 返回:
        # [
        #     {
        #         "id": 1, "name": "总公司", "parent_id": None,
        #         "children": [
        #             {
        #                 "id": 2, "name": "技术部", "parent_id": 1,
        #                 "children": [
        #                     {"id": 3, "name": "前端组", "parent_id": 2}
        #                 ]
        #             }
        #         ]
        #     }
        # ]
    """
    tree = []
    # 先将所有项按 id 建立索引，方便快速查找父节点
    item_dict = {item[id_key]: item for item in items}
    
    for item in items:
        parent_id = item.get(parent_key)
        # 如果有父节点且父节点存在，则将当前项添加到父节点的 children 中
        if parent_id and parent_id in item_dict:
            parent = item_dict[parent_id]
            if children_key not in parent:
                parent[children_key] = []
            parent[children_key].append(item)
        else:
            # 没有父节点或父节点不存在，说明是根节点
            tree.append(item)
    
    return tree


def mask_string(s: str, start: int = 3, end: int = 4, mask_char: str = '*') -> str:
    """字符串脱敏处理
    
    保留字符串开头和结尾的指定字符，中间部分用掩码字符替换。
    常用于手机号、身份证号、邮箱等敏感信息的展示脱敏。
    
    Args:
        s: 需要脱敏的原始字符串
        start: 保留开头的字符数，默认 3
        end: 保留结尾的字符数，默认 4
        mask_char: 掩码字符，默认 '*'
        
    Returns:
        str: 脱敏后的字符串
        
    使用示例:
        mask_string("13812345678")  # '138****5678'
        mask_string("zhangsan@example.com", start=2, end=5)  # 'zh**********.com'
        mask_string("123")  # '***'  # 字符串太短，全部掩码
    """
    # 如果字符串长度不足以保留开头和结尾，则全部掩码
    if len(s) <= start + end:
        return mask_char * len(s)
    # 保留开头 + 中间掩码 + 保留结尾
    return s[:start] + mask_char * (len(s) - start - end) + s[-end:]
