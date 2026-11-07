# 部署指南

本文档是生产部署的**总览**，面向裸机 / 云主机直接部署。

- 现成的配置文件（Gunicorn、systemd、Nginx、SSL、MySQL 初始化）：见 [`deploy/README.md`](../deploy/README.md)
- 配置项逐条说明：见 [`config.md`](config.md)

---

## 生产部署检查清单

- [ ] `APP_DEBUG=false`（关闭 `/docs`，默认 JWT 密钥将拒绝启动）
- [ ] `JWT_SECRET` 为 64 位随机值：`python -c "import secrets; print(secrets.token_hex(32))"`
- [ ] 数据库账号非 root，密码为强随机值
- [ ] `CORS_ORIGINS` 为具体域名（`*` 与凭证互斥，框架会自动关闭凭证）
- [ ] `AUTH_ENABLED=true`、`RATE_LIMIT_ENABLED=true`
- [ ] 数据库与 Redis 端口不对公网暴露
- [ ] 部署在 Nginx 之后时 `TRUST_PROXY=true`（否则限流按代理 IP 计算）
- [ ] `python think.py db-migrate --current` 与代码版本一致
- [ ] 已配置数据库备份、日志轮转、进程守护

---

## 方式一：Uvicorn（小流量）

```bash
pip install -r requirements.txt
python think.py db-migrate --upgrade
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
```

需要多进程时建议改用 Gunicorn：`uvicorn --workers` 在部分版本下滚动重启会断开在途连接。

---

## 方式二：Gunicorn + Uvicorn Worker（推荐）

```bash
pip install -r requirements.txt -r requirements-prod.txt
python think.py db-migrate --upgrade
gunicorn -c deploy/gunicorn.conf.py main:app
```

worker 数由 `GUNICORN_WORKERS` 控制，未设置时按 `CPU × 2 + 1` 计算。
数据库连接池按 **每个 worker 独立** 建立，实际连接数约
`workers × (DB_POOL_SIZE + DB_MAX_OVERFLOW)`，需小于 MySQL `max_connections`。

> Gunicorn 不支持 Windows，Windows 开发请用 `python think.py run`。

---

## 方式三：Systemd 守护（Linux 裸机）

`deploy/thinkpython.service` 已写好，复制即可：

```bash
sudo cp deploy/thinkpython.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now thinkpython
sudo systemctl status thinkpython
sudo journalctl -u thinkpython -f
```

单元文件要点：

```ini
[Service]
Type=simple
User=thinkpython
WorkingDirectory=/opt/thinkpython
EnvironmentFile=-/opt/thinkpython/.env
ExecStart=/opt/thinkpython/.venv/bin/gunicorn -c deploy/gunicorn.conf.py main:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
ReadWritePaths=/opt/thinkpython/logs /opt/thinkpython/uploads
```

发布新版本时 `systemctl reload thinkpython`：Gunicorn 平滑重启 worker，
不中断在途请求。**迁移要单独执行**，不要放进 `ExecReload`——
迁移失败会让平滑重启变成反复重启。

---

## 方式四：Nginx 反向代理 + HTTPS

```bash
sudo cp deploy/nginx.conf /etc/nginx/conf.d/thinkpython.conf
sudo vim /etc/nginx/conf.d/thinkpython.conf   # 改 server_name 与 uploads 实际路径
sudo nginx -t && sudo systemctl reload nginx
```

要点：

- `/uploads/` 由 Nginx 直接读磁盘，应用不参与文件传输；
- `/uploads/.chunks/` 必须 404，分片未合并前不可访问；
- 透传 `X-Forwarded-For`，并设 `TRUST_PROXY=true`，否则真实 IP 拿不到；
- HTTPS 证书放 `deploy/ssl/`，取消 `nginx.conf` 底部 443 `server` 块注释；
- 80 端口 `return 301 https://$host$request_uri`。

---

## 数据库迁移

```bash
python think.py db-migrate --upgrade     # 升级到最新
python think.py db-migrate --current     # 查看当前版本
python think.py db-migrate --downgrade   # 回滚一个版本
```

要点：

1. **先备份再迁移**：`mysqldump -u root -p thinkpython > backup_$(date +%F).sql`
2. **迁移脚本随代码一起发布**：服务器上必须包含 `alembic/versions/*.py`
3. **失败返回非零退出码**，发布脚本据此中止，不会带病上线
4. 多实例部署时，迁移作为发布流程的独立步骤，避免并发 DDL

---

## 性能调优

### 1. 进程与并发

| 场景 | worker 数 | 说明 |
|---|---|---|
| 1 核 2G | 2 | 单机演示 |
| 2 核 4G | 4 | 常规小型生产 |
| 4 核 8G | 8~9 | 中等流量 |

I/O 密集（多为数据库等待）可超过 `CPU×2`；CPU 密集时不要超过 `CPU×2`。

### 2. 数据库连接池

```env
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_RECYCLE=3600     # 小于 MySQL wait_timeout，避免用到已断开的连接
DB_POOL_PRE_PING=True    # 取连接前探活，代价是一次 round-trip
```

### 3. 缓存与限流

- 生产用 `CACHE_TYPE=redis`：内存缓存只在单进程内有效；
- 限流同理 `RATE_LIMIT_BACKEND=redis`：memory 后端在多 worker 下各算各的。

### 4. 日志

- 生产 `LOG_LEVEL=INFO`，DEBUG 会显著增加 I/O；
- 文件日志异步写入（`enqueue=True`），按 10MB 轮转、保留 5 份；
- 由 systemd 托管的进程，stdout/stderr 进 journald，文件日志作为兜底。

---

## 监控与运维

```bash
# 健康检查（不含敏感信息，可用于负载均衡探活）
curl -s http://127.0.0.1:8000/health

# 路由清单（确认控制器都注册成功，防止静默 404）
python think.py list-routes

# 迁移状态
python think.py db-migrate --current
```

### 常见问题

| 现象 | 原因与处理 |
|---|---|
| 启动即退出，日志提示默认 JWT_SECRET | `APP_DEBUG=false` 时默认密钥会拒绝启动，必须配置 `JWT_SECRET` |
| 接口 404，但代码里有控制器 | 控制器导入异常被框架捕获；跑 `list-routes` 确认，并检查是否放在 `app/{module}/controller/*_controller.py` |
| 迁移报 `MissingGreenlet` | 用异步 URL 直接调用了 Alembic；统一走 `think.py db-migrate` |
| 迁移报 `'gbk' codec can't decode` | `alembic.ini` 写入过中文；该文件必须保持纯 ASCII |
| 上传后 Nginx 返回 404 | Nginx `alias` 与 `UPLOAD_DIR` 指向不同目录，或 `UPLOAD_URL_PREFIX` 与 location 前缀不一致 |
| 401 但请求带了 Token | Token 类型必须是 `access`；refresh token 不能访问业务接口 |
| 所有请求被判成同一个 IP | 反向代理后未设 `TRUST_PROXY=true` |
| 改配置不生效 | 配置在模块导入时求值，必须重启进程 |

---

## 下一步

- 接口开发规范：[`api.md`](api.md)
- 鉴权与 Token 机制：[`auth.md`](auth.md)
- 架构决策与分层约定：[`architecture-decisions.md`](architecture-decisions.md)
