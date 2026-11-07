"""幂等键配置

背景：
    客户端在弱网下会重试，或用户连点提交按钮，导致同一笔业务重复执行。
    HTTP 本身只保证 GET 的幂等性，POST 需要业务侧辅助。

方案：
    客户端为「一次业务操作」生成唯一的 ``Idempotency-Key``，
    服务端把首次成功的响应缓存起来，相同 key 的后续请求直接回放该响应。

适用范围：
    仅对写操作（POST / PUT / PATCH / DELETE）生效；GET 天然幂等，不做处理。

局限（明确说明，避免误用）：
    1. 缓存基于「用户 + key」隔离，匿名请求共用 anon 作用域，可能互相干扰，
       因此幂等键主要用于已登录接口；
    2. 未实现并发锁——同一 key 的两个请求**同时**到达时，仍可能都执行一次。
       对支付等强一致场景，必须在数据库层加唯一约束兜底；
    3. 只缓存 2xx 响应，错误响应不固化，便于客户端修正后重试。
"""
import os

# 是否启用幂等键处理
IDEMPOTENCY_ENABLED = os.getenv("IDEMPOTENCY_ENABLED", "true").lower() == "true"

# 幂等结果缓存时长（秒），默认 24 小时
IDEMPOTENCY_TTL = int(os.getenv("IDEMPOTENCY_TTL", "86400"))

# 请求头名称
IDEMPOTENCY_HEADER = "Idempotency-Key"

# 参与幂等的 HTTP 方法
IDEMPOTENCY_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# key 长度上限与允许字符（UUID / 雪花 ID / 业务单号都满足）
IDEMPOTENCY_MAX_KEY_LENGTH = 128
IDEMPOTENCY_SAFE_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
)
