# ThinkPython Dockerfile - 生产环境部署示例
# 此文件为参考配置，用户可根据实际需求调整

# ==============================
# 阶段 1: 构建依赖
# ==============================
FROM python:3.12-slim AS builder

WORKDIR /app

# 安装构建依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ==============================
# 阶段 2: 运行环境
# ==============================
FROM python:3.12-slim

WORKDIR /app

# 创建非 root 用户（安全最佳实践）
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 从构建阶段复制安装的依赖
COPY --from=builder /install /usr/local

# 复制项目文件
COPY . .

# 创建必要的目录
RUN mkdir -p logs uploads && \
    chown -R appuser:appuser /app

# 切换到非 root 用户
USER appuser

# 环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_DEBUG=false \
    AUTH_ENABLED=true

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# 启动命令（使用 uvicorn）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
