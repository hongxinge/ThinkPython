"""
Gunicorn 配置文件 - 生产环境部署示例

此文件为参考配置，用户可根据实际服务器性能调整。
Gunicorn 是一个 Python WSGI HTTP 服务器，适合在生产环境中运行 FastAPI 应用。

使用方式:
    gunicorn -c deploy/gunicorn.conf.py main:app -k uvicorn.workers.UvicornWorker

推荐配置（根据 CPU 核心数）：
    workers = (CPU 核心数 × 2) + 1
"""
import multiprocessing
import os

# ==============================
# 服务器绑定
# ==============================

# 绑定地址和端口
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")

# ==============================
# Worker 配置
# ==============================

# Worker 进程数（推荐公式：CPU 核心数 × 2 + 1）
workers = multiprocessing.cpu_count() * 2 + 1

# Worker 类型（FastAPI 必须使用 uvicorn worker）
worker_class = "uvicorn.workers.UvicornWorker"

# 单个 Worker 最大并发连接数
worker_connections = 1000

# ==============================
# 超时配置
# ==============================

# Worker 超时时间（秒），超过此时间未响应会被重启
timeout = 120

# Worker 优雅重启超时时间（秒）
graceful_timeout = 30

# Keep-Alive 超时时间（秒）
keepalive = 5

# ==============================
# 进程配置
# ==============================

# PID 文件路径（用于管理进程）
pidfile = os.getenv("GUNICORN_PIDFILE", "/tmp/thinkpython.pid")

# 后台运行（守护进程模式）
daemon = False

# ==============================
# 日志配置
# ==============================

# 访问日志格式
accesslog = os.getenv("GUNICORN_ACCESS_LOG", "-")  # "-" 表示输出到 stdout

# 错误日志文件路径
errorlog = os.getenv("GUNICORN_ERROR_LOG", "-")  # "-" 表示输出到 stderr

# 日志级别
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")

# 访问日志格式
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# ==============================
# 性能配置
# ==============================

# 单个 Worker 处理的最大请求数（超过后自动重启，防止内存泄漏）
max_requests = 2000

# 多个 Worker 同时重启的最大数量（防止所有 Worker 同时重启导致服务中断）
max_requests_jitter = 50

# 预加载应用（启动时加载所有代码，减少内存占用）
preload_app = True

# ==============================
# 安全配置
# ==============================

# 限制请求行最大长度
limit_request_line = 4094

# 限制请求头字段数量
limit_request_fields = 100

# 限制请求头字段最大长度
limit_request_field_size = 8190

# ==============================
# 钩子函数（可选）
# ==============================

def on_starting(server):
    """服务器启动前执行"""
    print("🚀 ThinkPython 正在启动...")

def when_ready(server):
    """服务器就绪后执行"""
    print("✅ ThinkPython 已就绪，监听: {}".format(server.address))

def worker_int(worker):
    """Worker 收到 SIGINT/SIGTERM 信号时执行"""
    print("⚠️  Worker {} 收到停止信号".format(worker.pid))

def worker_abort(worker):
    """Worker 超时被强制终止时执行"""
    print("❌ Worker {} 超时被终止".format(worker.pid))
