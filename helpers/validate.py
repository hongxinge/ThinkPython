"""
ThinkPython 参数验证工具

本模块提供常用的数据格式验证函数，包括：
- is_email(): 邮箱格式验证
- is_mobile(): 中国大陆手机号格式验证
- is_id_card(): 身份证号格式验证
- is_url(): URL 格式验证
- is_ip(): IP 地址格式验证
- validate_password(): 密码强度验证

所有验证函数都返回布尔值，通过正则表达式进行模式匹配。

使用示例:
    from helpers.validate import is_email, is_mobile, validate_password
    
    if is_email("user@example.com"):
        print("邮箱格式正确")
    
    passed, msg = validate_password("Abc12345")
    if passed:
        print(msg)  # "密码验证通过"
"""
import re
from typing import Optional


def is_email(email: str) -> bool:
    """验证邮箱地址格式是否正确
    
    使用正则表达式检查邮箱格式，要求：
    - 用户名部分：字母、数字、点、下划线、百分号、加号、减号
    - 域名部分：字母、数字、点、减号
    - 顶级域名：至少 2 个字母
    
    Args:
        email: 需要验证的邮箱地址字符串
        
    Returns:
        bool: 格式正确返回 True，否则返回 False
        
    使用示例:
        is_email("user@example.com")  # True
        is_email("invalid-email")     # False
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def is_mobile(mobile: str) -> bool:
    """验证中国大陆手机号格式是否正确
    
    中国大陆手机号规则：
    - 11 位数字
    - 以 1 开头
    - 第二位是 3-9（运营商号段）
    
    Args:
        mobile: 需要验证的手机号字符串
        
    Returns:
        bool: 格式正确返回 True，否则返回 False
        
    使用示例:
        is_mobile("13812345678")  # True
        is_mobile("12345678901")  # False
    """
    pattern = r'^1[3-9]\d{9}$'
    return bool(re.match(pattern, mobile))


def is_id_card(id_card: str) -> bool:
    """验证中国身份证号格式是否正确
    
    支持两种格式：
    - 18 位：17 位数字 + 1 位校验码（0-9 或 X/x）
    - 15 位：纯数字（旧版身份证）
    
    注意：此函数仅验证格式，不验证校验码的正确性和地区编码的合法性。
    
    Args:
        id_card: 需要验证的身份证号字符串
        
    Returns:
        bool: 格式正确返回 True，否则返回 False
        
    使用示例:
        is_id_card("110101199001011234")  # True (18 位)
        is_id_card("110101900101123")      # True (15 位)
    """
    pattern = r'^\d{17}[\dXx]$|^\d{15}$'
    return bool(re.match(pattern, id_card))


def is_url(url: str) -> bool:
    """验证 URL 格式是否正确
    
    支持 http 和 https 协议，要求：
    - 以 http:// 或 https:// 开头
    - 包含有效的域名
    - 可选包含端口号和路径
    
    Args:
        url: 需要验证的 URL 字符串
        
    Returns:
        bool: 格式正确返回 True，否则返回 False
        
    使用示例:
        is_url("https://www.example.com")         # True
        is_url("https://api.example.com:8080/v1") # True
        is_url("ftp://example.com")               # False (不支持 ftp)
    """
    pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(:\d+)?(/.*)?$'
    return bool(re.match(pattern, url))


def is_ip(ip: str) -> bool:
    """验证 IPv4 地址格式是否正确
    
    IPv4 地址规则：
    - 由 4 个 0-255 的数字组成
    - 数字之间用点号分隔
    
    Args:
        ip: 需要验证的 IP 地址字符串
        
    Returns:
        bool: 格式正确返回 True，否则返回 False
        
    使用示例:
        is_ip("192.168.1.1")   # True
        is_ip("256.1.1.1")     # False (256 超出范围)
        is_ip("10.0.0.1")      # True
    """
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(pattern, ip):
        return False
    # 进一步检查每段数字是否在 0-255 范围内
    return all(0 <= int(part) <= 255 for part in ip.split('.'))


def validate_password(password: str, min_length: int = 6) -> tuple:
    """验证密码强度
    
    检查密码是否满足以下要求：
    1. 长度不少于 min_length 位
    2. 包含至少一个大写字母（A-Z）
    3. 包含至少一个小写字母（a-z）
    4. 包含至少一个数字（0-9）
    
    Args:
        password: 需要验证的密码字符串
        min_length: 密码最小长度要求，默认 6 位
        
    Returns:
        tuple: (是否通过验证, 提示信息)
            - 通过时: (True, "密码验证通过")
            - 未通过时: (False, 具体错误原因)
        
    使用示例:
        validate_password("Abc123")
        # (True, "密码验证通过")
        
        validate_password("abc")
        # (False, "密码长度不能少于6位")
        
        validate_password("abcdef")
        # (False, "密码必须包含至少一个大写字母")
    """
    if len(password) < min_length:
        return False, f"密码长度不能少于{min_length}位"
    if not re.search(r'[A-Z]', password):
        return False, "密码必须包含至少一个大写字母"
    if not re.search(r'[a-z]', password):
        return False, "密码必须包含至少一个小写字母"
    if not re.search(r'\d', password):
        return False, "密码必须包含至少一个数字"
    return True, "密码验证通过"
