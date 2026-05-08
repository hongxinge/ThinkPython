"""
ThinkPython 工具类模块

本模块提供通用的工具类和辅助函数，包括：
- JsonEncoder: 自定义 JSON 编码器，支持 datetime 等特殊类型的序列化
- to_dict(): 将对象实例转换为字典
- to_json(): 将对象转换为 JSON 字符串（支持自定义编码器）
- parse_json(): 解析 JSON 字符串为 Python 对象

这些工具类在 API 响应、日志记录、数据转换等场景中使用。

使用示例:
    from utils import to_dict, to_json, parse_json, JsonEncoder
    
    # 对象转字典
    user_dict = to_dict(user_instance)
    
    # 对象转 JSON（自动处理 datetime）
    user_json = to_json({"created_at": datetime.now()})
    
    # JSON 字符串解析
    data = parse_json('{"name": "张三"}')
"""
from datetime import datetime
from typing import Any, Dict, List
import json


class JsonEncoder(json.JSONEncoder):
    """自定义 JSON 编码器 - 扩展标准 JSONEncoder 以支持更多数据类型
    
    标准 json.dumps() 无法直接序列化 datetime 等对象，
    此编码器通过重写 default() 方法，自动将 datetime 对象格式化为字符串。
    
    使用示例:
        import json
        from utils import JsonEncoder
        
        data = {"created_at": datetime(2024, 1, 1, 12, 0, 0)}
        json_str = json.dumps(data, cls=JsonEncoder)
        # 结果: {"created_at": "2024-01-01 12:00:00"}
    """
    
    def default(self, obj):
        """重写默认序列化方法，处理标准 JSONEncoder 不支持的类型
        
        Args:
            obj: 需要序列化的对象
            
        Returns:
            序列化后的值。如果是 datetime 对象则返回格式化字符串，
            否则调用父类的 default() 方法（会抛出 TypeError）
        """
        if isinstance(obj, datetime):
            # 将 datetime 对象格式化为 "年-月-日 时:分:秒" 字符串
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        return super().default(obj)


def to_dict(obj: Any) -> Dict:
    """将对象实例转换为字典
    
    通过读取对象的 __dict__ 属性获取所有实例变量，
    并过滤掉以 _ 开头的私有/受保护属性。
    
    注意：此方法只转换对象的一层属性，不会递归转换嵌套对象。
    
    Args:
        obj: 需要转换的对象，必须有 __dict__ 属性
        
    Returns:
        Dict: 转换后的字典，如果对象没有 __dict__ 则返回空字典
        
    使用示例:
        class User:
            def __init__(self):
                self.name = "张三"
                self._password = "123456"
        
        user = User()
        to_dict(user)  # 返回: {"name": "张三"}  # _password 被过滤
    """
    if hasattr(obj, '__dict__'):
        # 过滤掉以 _ 开头的私有属性（如 _password, __secret）
        return {key: value for key, value in obj.__dict__.items() if not key.startswith('_')}
    return {}


def to_json(obj: Any, **kwargs) -> str:
    """将对象转换为 JSON 字符串
    
    使用自定义的 JsonEncoder 编码器，自动处理 datetime 等特殊类型。
    额外的关键字参数会传递给 json.dumps()。
    
    Args:
        obj: 需要序列化的对象
        **kwargs: 传递给 json.dumps() 的额外参数，如 indent=2（格式化输出）
        
    Returns:
        str: JSON 格式的字符串
        
    使用示例:
        data = {"name": "张三", "created_at": datetime.now()}
        to_json(data)  # 返回: '{"name": "张三", "created_at": "2024-01-01 12:00:00"}'
        to_json(data, indent=2)  # 格式化输出，带缩进
    """
    return json.dumps(obj, cls=JsonEncoder, **kwargs)


def parse_json(json_str: str) -> Any:
    """解析 JSON 字符串为 Python 对象
    
    将 JSON 格式的字符串反序列化为对应的 Python 对象（dict、list、str、int 等）。
    
    Args:
        json_str: JSON 格式的字符串
        
    Returns:
        Any: 解析后的 Python 对象
        
    Raises:
        json.JSONDecodeError: 当字符串不是有效的 JSON 格式时抛出
        
    使用示例:
        parse_json('{"name": "张三", "age": 25}')
        # 返回: {"name": "张三", "age": 25}
        
        parse_json('[1, 2, 3]')
        # 返回: [1, 2, 3]
    """
    return json.loads(json_str)
