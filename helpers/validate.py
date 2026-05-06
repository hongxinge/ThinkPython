"""
助手函数 - 验证工具
"""
import re
from typing import Optional


def is_email(email: str) -> bool:
    """验证邮箱格式"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def is_mobile(mobile: str) -> bool:
    """验证手机号格式 (中国大陆)"""
    pattern = r'^1[3-9]\d{9}$'
    return bool(re.match(pattern, mobile))


def is_id_card(id_card: str) -> bool:
    """验证身份证号格式"""
    pattern = r'^\d{17}[\dXx]$|^\d{15}$'
    return bool(re.match(pattern, id_card))


def is_url(url: str) -> bool:
    """验证URL格式"""
    pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(:\d+)?(/.*)?$'
    return bool(re.match(pattern, url))


def is_ip(ip: str) -> bool:
    """验证IP地址格式"""
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(pattern, ip):
        return False
    return all(0 <= int(part) <= 255 for part in ip.split('.'))


def validate_password(password: str, min_length: int = 6) -> tuple:
    """验证密码强度
    返回 (是否通过, 错误信息)
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
