"""ThinkPython 数据验证模块测试"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from helpers.validate import is_email, is_mobile, is_id_card, is_url, is_ip, validate_password


# ============== 数据验证测试 ==============

class TestEmailValidation:
    """邮箱验证测试"""

    def test_valid_email(self):
        """测试有效邮箱"""
        assert is_email("user@example.com") is True

    def test_valid_email_with_subdomain(self):
        """测试带子域名的邮箱"""
        assert is_email("user@mail.example.com") is True

    def test_valid_email_with_plus(self):
        """测试带加号的邮箱"""
        assert is_email("user+tag@example.com") is True

    def test_valid_email_with_underscore(self):
        """测试带下划线的邮箱"""
        assert is_email("user_name@example.com") is True

    def test_valid_email_with_dot(self):
        """测试带点的用户名"""
        assert is_email("first.last@example.com") is True

    def test_invalid_email_no_at(self):
        """测试无 @ 符号"""
        assert is_email("userexample.com") is False

    def test_invalid_email_no_domain(self):
        """测试无域名"""
        assert is_email("user@") is False

    def test_invalid_email_no_tld(self):
        """测试无顶级域名"""
        assert is_email("user@example") is False

    def test_empty_email(self):
        """测试空邮箱"""
        assert is_email("") is False


class TestMobileValidation:
    """手机号验证测试"""

    def test_valid_mobile_138(self):
        """测试 138 号段"""
        assert is_mobile("13812345678") is True

    def test_valid_mobile_139(self):
        """测试 139 号段"""
        assert is_mobile("13912345678") is True

    def test_valid_mobile_150(self):
        """测试 150 号段"""
        assert is_mobile("15012345678") is True

    def test_valid_mobile_186(self):
        """测试 186 号段"""
        assert is_mobile("18612345678") is True

    def test_valid_mobile_170(self):
        """测试 170 号段"""
        assert is_mobile("17012345678") is True

    def test_valid_mobile_191(self):
        """测试 191 号段"""
        assert is_mobile("19112345678") is True

    def test_invalid_mobile_wrong_length(self):
        """测试错误长度"""
        assert is_mobile("1381234567") is False

    def test_invalid_mobile_wrong_start(self):
        """测试非 1 开头"""
        assert is_mobile("23812345678") is False

    def test_invalid_mobile_second_digit(self):
        """测试第二位数字不符合"""
        assert is_mobile("12012345678") is False

    def test_invalid_mobile_letters(self):
        """测试包含字母"""
        assert is_mobile("1381234abcd") is False


class TestIdCardValidation:
    """身份证验证测试"""

    def test_valid_18_digit(self):
        """测试 18 位身份证"""
        assert is_id_card("110101199001011234") is True

    def test_valid_18_digit_with_x(self):
        """测试 18 位身份证带 X"""
        assert is_id_card("11010119900101123X") is True

    def test_valid_18_digit_with_lowercase_x(self):
        """测试 18 位身份证带小写 x"""
        assert is_id_card("11010119900101123x") is True

    def test_valid_15_digit(self):
        """测试 15 位旧身份证"""
        assert is_id_card("110101900101123") is True

    def test_invalid_id_card_wrong_length(self):
        """测试错误长度"""
        assert is_id_card("1101011990") is False

    def test_invalid_id_card_letters(self):
        """测试非校验位含字母"""
        assert is_id_card("A10101199001011234") is False


class TestUrlValidation:
    """URL 验证测试"""

    def test_valid_http_url(self):
        """测试 HTTP URL"""
        assert is_url("http://example.com") is True

    def test_valid_https_url(self):
        """测试 HTTPS URL"""
        assert is_url("https://example.com") is True

    def test_valid_url_with_path(self):
        """测试带路径的 URL"""
        assert is_url("https://example.com/path/to/page") is True

    def test_valid_url_with_port(self):
        """测试带端口的 URL"""
        assert is_url("https://api.example.com:8080/v1") is True

    def test_valid_url_with_subdomain(self):
        """测试带子域名的 URL"""
        assert is_url("https://www.example.com") is True

    def test_invalid_url_ftp(self):
        """测试 FTP 协议"""
        assert is_url("ftp://example.com") is False

    def test_invalid_url_no_protocol(self):
        """测试无协议"""
        assert is_url("example.com") is False

    def test_invalid_url_empty(self):
        """测试空 URL"""
        assert is_url("") is False


class TestIpValidation:
    """IP 地址验证测试"""

    def test_valid_ip_localhost(self):
        """测试本地地址"""
        assert is_ip("127.0.0.1") is True

    def test_valid_ip_private(self):
        """测试私有地址"""
        assert is_ip("192.168.1.1") is True

    def test_valid_ip_public(self):
        """测试公网地址"""
        assert is_ip("8.8.8.8") is True

    def test_valid_ip_zero(self):
        """测试 0.0.0.0"""
        assert is_ip("0.0.0.0") is True

    def test_valid_ip_max(self):
        """测试 255.255.255.255"""
        assert is_ip("255.255.255.255") is True

    def test_invalid_ip_out_of_range(self):
        """测试超出范围"""
        assert is_ip("256.1.1.1") is False

    def test_invalid_ip_too_few_octets(self):
        """测试段数不足"""
        assert is_ip("192.168.1") is False

    def test_invalid_ip_too_many_octets(self):
        """测试段数过多"""
        assert is_ip("192.168.1.1.1") is False

    def test_invalid_ip_letters(self):
        """测试包含字母"""
        assert is_ip("192.168.1.a") is False


class TestPasswordValidation:
    """密码强度验证测试"""

    def test_valid_password(self):
        """测试有效密码"""
        passed, msg = validate_password("Abc123")
        assert passed is True
        assert "验证通过" in msg

    def test_valid_password_longer(self):
        """测试较长有效密码"""
        passed, msg = validate_password("Password123!")
        assert passed is True

    def test_invalid_password_too_short(self):
        """测试密码太短"""
        passed, msg = validate_password("Ab1")
        assert passed is False
        assert "长度" in msg

    def test_invalid_password_no_uppercase(self):
        """测试无大写字母"""
        passed, msg = validate_password("abc123")
        assert passed is False
        assert "大写" in msg

    def test_invalid_password_no_lowercase(self):
        """测试无小写字母"""
        passed, msg = validate_password("ABC123")
        assert passed is False
        assert "小写" in msg

    def test_invalid_password_no_digit(self):
        """测试无数字"""
        passed, msg = validate_password("Abcdef")
        assert passed is False
        assert "数字" in msg

    def test_custom_min_length(self):
        """测试自定义最小长度"""
        passed, msg = validate_password("Ab1234", min_length=8)
        assert passed is False
        assert "长度" in msg

    def test_custom_min_length_pass(self):
        """测试自定义最小长度通过"""
        passed, msg = validate_password("Abcdef12", min_length=8)
        assert passed is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
