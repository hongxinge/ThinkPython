# ThinkPython 部署指南

本目录存放生产部署配置。所有示例都以「一个服务跑起来」为目标，复制即可用。

## 目录结构

```
deploy/
├── Dockerfile              # 生产镜像（多阶段构建，非 root 运行）
├── docker-compose.yml      # 应用 + MySQL + Redis + Nginx 完整编排
├── .env.example            # 生产环境变量模板（复制为 .env 使用）
├── gunicorn.conf.py        # Gunicorn 进程配置
├── nginx.conf              # 反向代理 + 静态文件 + SSL 示例
├── mysql-init.sql          # MySQL 首次初始化（字符集、时区、慢查询）
├── ssl/                    # 证书目录（内容不入库）
└── README.md
```

> 注意：Docker 构建上下文是**仓库根目录**，因此 `.dockerignore` 也放在仓库根。
> 放在 `deploy/` 下的 `.dockerignore` 不会生效。

## 部署方式选择

| 方式 | 适用场景 | 命令 |
|---|---|---|
| 开发服务器 | 本地开发 | `python think.py run` |
| Uvicorn 单进程 | 内部工具、日请求 < 1 万 | `uvicorn main:app --host 0.0.0.0 --port 8000` |
| Gunicorn 多进程 | 中小型生产（Linux） | `gunicorn -c deploy/gunicorn.conf.py main:app` |
| Docker Compose | 完整生产环境 | `cd deploy && docker compose up -d --build` |

---

## 方式一：本机直接运行（开发）

```bash
pip install -r requirements.txt
cp .env.example .env       # 仓库根的开发模板：single + SQLite + memory
python think.py run
```

访问 `http://127.0.0.1:8000/docs` 查看接口文档。

---

## 方式二：Gunicorn 多进程（Linux 生产）

```bash
pip install -r requirements.txt -r requirements-prod.txt
cp deploy/.env.example .env    # 按需修改；生产建议放环境变量而非文件
python think.py db-migrate --upgrade
gunicorn -c deploy/gunicorn.conf.py main:app
```

关键参数（`gunicorn.conf.py`）：

| 参数 | 默认 | 说明 |
|---|---|---|
| `workers` | 环境变量 `GUNICORN_WORKERS`，否则 CPU×2+1 | 容器内务必显式指定 |
| `worker_class` | `uvicorn.workers.UvicornWorker` | 跑 ASGI 必须用此类型 |
| `preload_app` | `True` | 降低内存；数据库连接在 lifespan 内建立，fork 安全 |
| `max_requests` | `2000` | 缓解潜在内存泄漏 |

> `gunicorn` 不支持 Windows，Windows 开发请用 `think.py run`。

---

## 方式三：Docker Compose（推荐）

### 1. 准备配置

```bash
cd deploy
cp .env.example .env
# 必填：DB_ROOT_PASSWORD、DB_PASSWORD、JWT_SECRET、CORS_ORIGINS
python -c "import secrets; print(secrets.token_hex(32))"   # 生成 JWT_SECRET
```

### 2. 启动

```bash
docker compose up -d --build
```

启动顺序由健康检查保证：MySQL 就绪 → 应用执行 `db-migrate --upgrade` → Gunicorn 启动 → Nginx 接入。

### 3. 验证

```bash
curl http://127.0.0.1/health
docker compose ps
docker compose logs -f app
```

### 4. 停止与清理

```bash
docker compose down          # 停止，保留数据
docker compose down -v       # 停止并删除数据卷（会丢数据）
```

### 关于自动迁移

`app.command` 会在启动时先跑迁移。**单副本**部署下这样最省事；多副本部署时，
应删除 command 中的迁移步骤，改为发布流程里的独立 Job，避免并发 DDL。

---

## 数据库迁移

```bash
# 在宿主机（需能连到数据库）
python think.py db-migrate --upgrade
# 在容器内
docker compose exec app python think.py db-migrate --upgrade
# 查看当前版本
docker compose exec app python think.py db-migrate --current
```

迁移失败会返回非零退出码，容器会中止启动而不是带病运行。

---

## SSL 证书

把证书放到 `deploy/ssl/`（已挂载到容器 `/etc/nginx/ssl`）：

```
deploy/ssl/fullchain.pem
deploy/ssl/privkey.pem
```

然后取消 `nginx.conf` 底部 HTTPS `server` 块的注释，改 `server_name` 为本域名，
`docker compose restart nginx`。Let's Encrypt 获取方式见 `deploy/ssl/README.md`。

---

## 生产检查清单

- [ ] `APP_DEBUG=false`（同时关闭 `/docs`，并在默认 JWT 密钥时拒绝启动）
- [ ] `JWT_SECRET` 为 64 位随机值
- [ ] `DB_ROOT_PASSWORD` / `DB_PASSWORD` 为强随机值，且应用账号非 root
- [ ] `CORS_ORIGINS` 为具体域名，未使用 `*`
- [ ] `AUTH_ENABLED=true`、`RATE_LIMIT_ENABLED=true`
- [ ] 数据库与 Redis 端口未映射到公网
- [ ] SSL 证书已配置，80 端口重定向到 443
- [ ] 已配置数据库定时备份与日志轮转
- [ ] `python think.py db-migrate --current` 与代码版本一致

---

## 故障排查

| 现象 | 排查方向 |
|---|---|
| 容器反复重启 | `docker compose logs app`；多为迁移失败或环境变量缺失 |
| `/health` 502 | 应用未就绪或端口不符；`docker compose ps` 看 health 状态 |
| 401 全部接口 | 请求未带 `Authorization: Bearer`，或路径在 `SKIP_AUTH_PATHS` 外 |
| 数据库连接失败 | `DB_HOST` 应为 compose 服务名 `db`；确认 db 健康检查通过 |
| 上传文件 404 | Nginx 未挂载 `app-uploads` 卷，或 `UPLOAD_DIR` 与卷路径不一致 |
| 迁移报 `MissingGreenlet` | 用了异步驱动 URL；`alembic/env.py` 会自动转同步，检查是否绕过 CLI 直接调用 |
