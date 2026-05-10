# ThinkPython 部署指南

本目录包含生产环境部署的配置示例，用户可根据实际需求选择部署方式。

## 📁 目录结构

```
deploy/
├── Dockerfile              # Docker 镜像构建文件
├── docker-compose.yml      # Docker Compose 完整环境配置
├── .dockerignore           # Docker 忽略文件
├── gunicorn.conf.py        # Gunicorn 生产服务器配置
├── nginx.conf              # Nginx 反向代理配置
└── README.md               # 本文件
```

## 🚀 部署方式选择

ThinkPython 支持多种部署方式，请根据项目规模选择：

| 部署方式 | 适用场景 | 配置复杂度 | 性能 |
|---------|---------|-----------|------|
| 直接运行 | 开发/测试 | ⭐ | 低 |
| Uvicorn | 小型项目 | ⭐⭐ | 中 |
| Gunicorn | 中型项目 | ⭐⭐⭐ | 高 |
| Docker | 任何环境 | ⭐⭐⭐⭐ | 高 |
| Docker Compose | 完整生产环境 | ⭐⭐⭐⭐⭐ | 最高 |

---

## 方式一：直接运行（开发环境）

```bash
# 安装依赖
pip install -r requirements.txt

# 启动开发服务器
python think.py run
```

**适用场景**: 本地开发、功能测试

---

## 方式二：Uvicorn（小型项目）

```bash
# 安装 uvicorn
pip install uvicorn

# 启动生产服务器
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
```

**适用场景**: 日访问量 < 1 万的小型项目

---

## 方式三：Gunicorn + Uvicorn Workers（中型项目）

```bash
# 安装依赖
pip install gunicorn uvicorn

# 使用配置文件启动
gunicorn -c deploy/gunicorn.conf.py main:app -k uvicorn.workers.UvicornWorker
```

**推荐 Worker 数**: `(CPU 核心数 × 2) + 1`

**适用场景**: 日访问量 1-10 万的中型项目

---

## 方式四：Docker 部署

### 4.1 构建镜像

```bash
# 构建 Docker 镜像
docker build -f deploy/Dockerfile -t thinkpython:latest .

# 运行容器
docker run -d \
  --name thinkpython \
  -p 8000:8000 \
  -e DB_TYPE=sqlite \
  -e APP_DEBUG=false \
  thinkpython:latest
```

### 4.2 使用 Docker Compose（完整环境）

```bash
# 进入 deploy 目录
cd deploy

# 启动完整环境（App + MySQL + Redis + Nginx）
docker-compose up -d

# 查看日志
docker-compose logs -f app

# 停止服务
docker-compose down
```

**环境变量配置**:
```bash
# 创建 .env 文件（在 deploy/ 目录下）
DB_PASSWORD=your_secure_password
JWT_SECRET=your_secure_jwt_secret
REDIS_PASSWORD=your_redis_password
```

**适用场景**: 任何环境，推荐生产部署

---

## 方式五：完整生产环境（推荐）

使用 `docker-compose.yml` 部署完整环境，包括：

- **ThinkPython 应用** - FastAPI + Uvicorn
- **MySQL 8.0** - 关系型数据库
- **Redis 7** - 缓存 + 限流
- **Nginx** - 反向代理 + SSL

### 步骤

1. 准备环境变量文件
```bash
cd deploy
cp .env.example .env
# 编辑 .env 文件，修改密码和密钥
```

2. 启动服务
```bash
docker-compose up -d
```

3. 执行数据库迁移
```bash
docker-compose exec app python think.py db-migrate
```

4. 访问应用
```
http://your_domain.com
http://your_domain.com/docs  # API 文档
```

---

## SSL 证书配置

### 使用 Let's Encrypt 免费证书

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your_domain.com -d www.your_domain.com

# 自动续期
sudo certbot renew --dry-run
```

### 手动配置证书

1. 将证书文件放到 `deploy/ssl/` 目录：
   - `fullchain.pem` - 证书链
   - `privkey.pem` - 私钥

2. 取消注释 `nginx.conf` 中的 HTTPS 配置块

---

## 生产环境检查清单

部署前请确认：

- [ ] `APP_DEBUG=false`
- [ ] `AUTH_ENABLED=true`
- [ ] `JWT_SECRET` 使用强随机密钥
- [ ] `DB_PASSWORD` 使用强密码
- [ ] `RATE_LIMIT_ENABLED=true`
- [ ] SSL 证书配置完成
- [ ] 防火墙仅开放必要端口（80/443）
- [ ] 数据库定期备份
- [ ] 日志定期清理

---

## 故障排查

### 容器无法启动

```bash
# 查看容器日志
docker-compose logs app

# 检查容器状态
docker-compose ps
```

### 数据库连接失败

```bash
# 测试数据库连接
docker-compose exec db mysql -u root -p

# 检查网络
docker-compose exec app ping db
```

### 性能问题

```bash
# 查看资源使用
docker stats

# 查看应用日志
docker-compose logs -f app
```

---

## 注意事项

1. **配置文件仅供参考**，请根据实际需求调整
2. **生产环境务必修改默认密码和密钥**
3. **SSL 证书强烈建议配置**，保障数据传输安全
4. **数据库定期备份**，防止数据丢失
5. **日志定期清理**，避免磁盘空间占满
