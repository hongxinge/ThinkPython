# 部署指南

本文档介绍如何将 ThinkPython 应用部署到生产环境。

---

## 生产部署前检查清单

在部署之前，请确保完成以下配置：

- [ ] 设置 `APP_DEBUG=False`
- [ ] 修改 `JWT_SECRET` 为强密钥
- [ ] 设置正确的 `CORS_ORIGINS`（限制允许的域名）
- [ ] 使用 MySQL/PostgreSQL 替代 SQLite
- [ ] 使用 Redis 替代内存缓存
- [ ] 设置合理的日志级别（`LOG_LEVEL=INFO` 或 `WARNING`）

---

## 方式一：使用 Uvicorn 直接运行

### 1. 安装生产依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件：

```env
APP_DEBUG=False
APP_NAME=MyApp
APP_VERSION=1.0.0

# 数据库
DB_TYPE=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=thinkpython
DB_USER=root
DB_PASSWORD=your_strong_password

# 缓存
CACHE_TYPE=redis
REDIS_HOST=127.0.0.1
REDIS_PORT=6379

# JWT
JWT_SECRET=your-super-secret-key-change-this
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24

# CORS
CORS_ORIGINS=https://yourdomain.com

# 日志
LOG_LEVEL=INFO
```

### 3. 启动服务

```bash
# 基本启动
uvicorn main:app --host 0.0.0.0 --port 8000

# 生产环境推荐配置（多worker）
uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level info
```

> ⚠️ **注意**：使用多worker时，内存缓存将不共享。生产环境务必使用Redis。

---

## 方式二：使用 Systemd 服务（Linux）

### 1. 创建服务文件

```bash
sudo nano /etc/systemd/system/thinkpython.service
```

### 2. 添加服务配置

```ini
[Unit]
Description=ThinkPython Application
After=network.target mysql.service redis.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/thinkpython
Environment=PATH=/var/www/thinkpython/venv/bin
ExecStart=/var/www/thinkpython/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4 --log-level info
Restart=always
RestartSec=5

# 日志
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 3. 启用并启动服务

```bash
# 重载systemd配置
sudo systemctl daemon-reload

# 启用服务（开机自启）
sudo systemctl enable thinkpython

# 启动服务
sudo systemctl start thinkpython

# 查看状态
sudo systemctl status thinkpython

# 查看日志
sudo journalctl -u thinkpython -f
```

---

## 方式三：使用 Docker

### 1. 创建 Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 创建logs目录
RUN mkdir -p logs

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 2. 创建 docker-compose.yml

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - APP_DEBUG=False
      - DB_TYPE=mysql
      - DB_HOST=db
      - DB_NAME=thinkpython
      - DB_USER=root
      - DB_PASSWORD=your_password
      - CACHE_TYPE=redis
      - REDIS_HOST=redis
    depends_on:
      - db
      - redis
    restart: always

  db:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=your_password
      - MYSQL_DATABASE=thinkpython
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    restart: always

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: always

volumes:
  mysql_data:
```

### 3. 构建并启动

```bash
docker-compose up -d
```

---

## 方式四：使用 Nginx 反向代理

### 1. 安装 Nginx

```bash
# Ubuntu/Debian
sudo apt install nginx

# CentOS/RHEL
sudo yum install nginx
```

### 2. 配置 Nginx

```bash
sudo nano /etc/nginx/sites-available/thinkpython
```

添加配置：

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket支持（如果需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 静态文件（如果有）
    location /static/ {
        alias /var/www/thinkpython/static/;
        expires 30d;
    }
}
```

### 3. 启用配置

```bash
# 创建软链接
sudo ln -s /etc/nginx/sites-available/thinkpython /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重载Nginx
sudo systemctl reload nginx
```

### 4. 配置 HTTPS（Let's Encrypt）

```bash
# 安装 certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d yourdomain.com

# 自动续期
sudo certbot renew --dry-run
```

---

## 性能优化建议

### 1. 使用 Gunicorn + Uvicorn Worker

```bash
pip install gunicorn

# 启动
gunicorn main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile - \
    --error-logfile -
```

### 2. 数据库连接池调优

```env
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
DB_POOL_RECYCLE=3600
DB_POOL_PRE_PING=True
```

### 3. 启用日志轮转

使用 loguru 自带的日志轮转功能，在 `main.py` 中配置：

```python
from loguru import logger

logger.add(
    "logs/app.log",
    rotation="10 MB",
    retention="30 days",
    level="INFO",
)
```

---

## 监控与运维

### 健康检查

访问 `/health` 端点：

```bash
curl http://localhost:8000/health
```

响应：
```json
{
  "code": 200,
  "message": "ok",
  "data": {
    "app": "ThinkPython",
    "version": "1.0.0",
    "debug": false
  }
}
```

### 日志查看

```bash
# 查看应用日志
tail -f logs/app.log

# 查看系统服务日志
sudo journalctl -u thinkpython -f
```

---

## 常见问题

### Q: 生产环境如何关闭API文档？

框架已自动处理，当 `APP_DEBUG=False` 时：
- `/docs` 不可访问
- `/redoc` 不可访问

### Q: 如何优雅重启服务？

```bash
# Systemd
sudo systemctl restart thinkpython

# Docker
docker-compose restart app

# Gunicorn
kill -HUP $(cat gunicorn.pid)
```

### Q: 如何查看当前运行的worker进程？

```bash
ps aux | grep uvicorn
```

---

## 下一步

- 🔧 查看 [配置说明](config.md) 了解所有配置项
- 📖 查看 [API 示例](api.md) 了解开发最佳实践
