# ThinkPython 生产镜像
#
# 构建（在仓库根目录执行）：
#   docker build -f deploy/Dockerfile -t thinkpython:latest .
# 或使用 compose（推荐，会自动读取根级 .dockerignore）：
#   cd deploy && docker compose up -d --build
#
# 说明：
#   - 使用 gunicorn + UvicornWorker 管理多进程（requirements-prod.txt）
#   - 以非 root 用户运行，降低容器逃逸风险
#   - 敏感配置通过环境变量注入，镜像内不含 .env

# ==============================
# 阶段 1：构建依赖
# ==============================
FROM python:3.12-slim AS builder

WORKDIR /app

# 部分依赖需要编译（greenlet 等）；编译完成后运行阶段不再保留编译器
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-prod.txt ./
RUN pip install --no-cache-dir --prefix=/install \
        -r requirements.txt -r requirements-prod.txt

# ==============================
# 阶段 2：运行环境
# ==============================
FROM python:3.12-slim

WORKDIR /app

# 时区（日志与数据库时间统一按东八区）
ENV TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 非 root 运行
RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser

COPY --from=builder /install /usr/local

# 只复制运行必需内容（其余由根级 .dockerignore 排除）
COPY --chown=appuser:appuser . .

# 运行期目录（挂载数据卷时会被覆盖）
RUN mkdir -p logs uploads data && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# 健康检查：容器内直接请求 /health，失败即判定不健康
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).status == 200 else 1)"

# 生产启动：gunicorn 管理多 worker，每个 worker 跑 Uvicorn
CMD ["gunicorn", "-c", "deploy/gunicorn.conf.py", "main:app"]
