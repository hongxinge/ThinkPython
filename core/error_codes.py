"""业务错误码定义（客户端契约）

为什么需要独立的业务码：
    HTTP 状态码只有几十个，无法表达「用户名已存在」与「邮箱已存在」这类差异。
    客户端（尤其 App）需要**稳定的、可枚举的**错误码来决定 UI 行为
    （提示文案、是否跳登录页、是否允许重试），而不是解析中文 message。

编码规则：
    - 400/401/403/404/409/429/500/503 段与 HTTP 语义一致，便于网关与客户端统一处理；
    - 1000-1999：认证与账号
    - 2000-2999：用户与权限
    - 3000-3999：文件与上传
    - 4000-4999：参数与业务校验

兼容性约定（1.x 内不得变更）：
    1. 已发布的 code 数值不得复用或改变语义；
    2. 新增错误只能追加新 code；
    3. 删除错误时保留 code 并标注 deprecated，至少保留一个次版本。

使用方式::

    from core.error_codes import ErrorCode
    from core.exception import AppException

    raise AppException("用户名已存在", code=ErrorCode.USER_EXISTS, status_code=409)
"""
from typing import Dict


class ErrorCode:
    """业务错误码常量

    说明：``SUCCESS`` 为 0 而非 200，是为了让客户端用 ``if (code !== 0)``
    统一判断失败；成功响应的 body.code 仍沿用 200 以兼容既有前端。
    """

    # ---------- 通用 ----------
    SUCCESS = 0
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    PAYLOAD_TOO_LARGE = 413
    UNSUPPORTED_MEDIA_TYPE = 415
    TOO_MANY_REQUESTS = 429
    INTERNAL_ERROR = 500
    SERVICE_UNAVAILABLE = 503

    # ---------- 1xxx 认证与账号 ----------
    TOKEN_MISSING = 1001          # 未携带 Authorization
    TOKEN_MALFORMED = 1002        # 不是 Bearer 格式
    TOKEN_INVALID = 1003          # 签名错误 / 类型不符
    TOKEN_EXPIRED = 1004          # 已过期，客户端应走刷新流程
    TOKEN_REVOKED = 1005          # 已登出 / 改密后失效，必须重新登录
    INVALID_CREDENTIALS = 1006    # 用户名或密码错误
    ACCOUNT_DISABLED = 1007       # 账号被禁用
    ACCOUNT_LOCKED = 1008         # 连续失败被临时锁定
    REFRESH_TOKEN_INVALID = 1009  # 刷新令牌无效
    PERMISSION_DENIED = 1010      # 已登录但角色权限不足

    # ---------- 2xxx 用户 ----------
    USER_EXISTS = 2001
    EMAIL_EXISTS = 2002
    USER_NOT_FOUND = 2003
    PASSWORD_MISMATCH = 2004      # 旧密码不正确

    # ---------- 3xxx 文件 ----------
    FILE_TOO_LARGE = 3001
    FILE_TYPE_NOT_ALLOWED = 3002
    FILE_NOT_FOUND = 3003
    PATH_NOT_ALLOWED = 3004

    # ---------- 4xxx 参数与业务 ----------
    VALIDATION_ERROR = 4000
    BUSINESS_ERROR = 4001


# 错误码 -> 建议的 HTTP 状态码
# 客户端与服务端共用同一份映射，避免两边对不上
ERROR_HTTP_STATUS: Dict[int, int] = {
    ErrorCode.BAD_REQUEST: 400,
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.METHOD_NOT_ALLOWED: 405,
    ErrorCode.CONFLICT: 409,
    ErrorCode.PAYLOAD_TOO_LARGE: 413,
    ErrorCode.UNSUPPORTED_MEDIA_TYPE: 415,
    ErrorCode.TOO_MANY_REQUESTS: 429,
    ErrorCode.INTERNAL_ERROR: 500,
    ErrorCode.SERVICE_UNAVAILABLE: 503,
    # 认证
    ErrorCode.TOKEN_MISSING: 401,
    ErrorCode.TOKEN_MALFORMED: 401,
    ErrorCode.TOKEN_INVALID: 401,
    ErrorCode.TOKEN_EXPIRED: 401,
    ErrorCode.TOKEN_REVOKED: 401,
    ErrorCode.INVALID_CREDENTIALS: 401,
    ErrorCode.ACCOUNT_DISABLED: 403,
    ErrorCode.ACCOUNT_LOCKED: 423,
    ErrorCode.REFRESH_TOKEN_INVALID: 401,
    ErrorCode.PERMISSION_DENIED: 403,
    # 用户
    ErrorCode.USER_EXISTS: 409,
    ErrorCode.EMAIL_EXISTS: 409,
    ErrorCode.USER_NOT_FOUND: 404,
    ErrorCode.PASSWORD_MISMATCH: 400,
    # 文件
    ErrorCode.FILE_TOO_LARGE: 413,
    ErrorCode.FILE_TYPE_NOT_ALLOWED: 415,
    ErrorCode.FILE_NOT_FOUND: 404,
    ErrorCode.PATH_NOT_ALLOWED: 403,
    # 参数
    ErrorCode.VALIDATION_ERROR: 422,
    ErrorCode.BUSINESS_ERROR: 400,
}


def http_status_of(code: int, default: int = 500) -> int:
    """把业务码映射为建议的 HTTP 状态码

    未登记的码（例如自定义业务码 40001）回落到 ``default``，
    避免把非法数值直接写进 HTTP 状态行导致响应无法解析。

    Args:
        code: 业务错误码
        default: 未登记时的默认状态码

    Returns:
        int: HTTP 状态码
    """
    if code in ERROR_HTTP_STATUS:
        return ERROR_HTTP_STATUS[code]
    # 兼容直接传 HTTP 状态码的旧写法（400/401/403/404/409/422/429/500/503）
    if 400 <= code <= 599:
        return code
    return default
