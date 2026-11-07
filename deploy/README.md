# ThinkPython 部署指南

本目录存放生产部署配置（**裸机 / 云主机直接部署**）。
所有示例都以「把服务跑起来」为目标，复制后按实际路径改一改即可用。

## 目录结构

```
deploy/
├── .env.example            # 生产环境变量模板（复制为 .env 使用）
├── gunicorn.conf.py        # Gunicorn 进程配置
├── thinkpython.service     # systemd 服务单元（开机自启 + 崩溃重启）
├── nginx.conf              # 反向代理 + 静态文件 + SSL 示例
├── mysql-init.sql          # MySQL 首次初始化（库、字符集、时区、应用账号）
├── ssl/                    # 证书目录（内容不入库）
└── README.md
```

## 部署方式选择

| 方式 | 适用场景 | 命令 |
|---|---|---|
| 开发服务器 | 本地开发 | `python think.py run` |
| Uvicorn 单进程 | 内部工具、日请求 < 1 万 | `uvicorn main:app --host 0.0.0.0 --port 8000` |
| Gunicorn 多进程 | 中小型生产（Linux） | `gunicorn -c deploy/gunicorn.conf.py main:app` |
| Gunicorn + systemd | 生产常驻（推荐） | `systemctl start thinkpython` |

> `gunicorn` 不支持 Windows。Windows 上开发用 `think.py run`，
> 部署建议放到 Linux 服务器（云主机 / 独立服务器）。

---

## 一、环境准备

| 依赖 | 版本 | 说明 |
|---|---|---|
| Python | 3.11+ | 仓库开发环境为 3.13 |
| MySQL | 8.0+ | 也可用 SQLite（`DB_TYPE=sqlite`，仅适合单机小流量） |
| Redis | 6+ | 可选。多 worker 部署下缓存/限流/Token 黑名单**必须**用 Redis |
| Nginx | 1.20+ | 可选。反向代理、静态文件、HTTPS 终止 |

```bash
# 以 /opt/thinkpython 为例
sudo useradd -r -s /sbin/nologin thinkpython
sudo mkdir -p /opt/thinkpython && sudo chown thinkpython:thinkpython /opt/thinkpython
sudo -u thinkpython git clone <仓库地址> /opt/thinkpython
cd /opt/thinkpython

# 独立虚拟环境，避免污染系统 Python
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-prod.txt
```

---

## 二、数据库初始化（MySQL）

`mysql-init.sql` 负责建库、统一字符集与时区、调整连接数与慢查询阈值；
脚本末尾有**应用专用账号**段落，取消注释并改成强随机密码即可创建非 root 账号。
用 root 手工执行，重复执行是幂等的：

```bash
# 先按实际情况修改库名与账号密码
mysql -u root -p < deploy/mysql-init.sql

# 校验
mysql -u thinkpython -p -e "SHOW VARIABLES LIKE 'character_set_database';"
```

要点：

- **字符集必须是 utf8mb4**：否则 emoji 与四字节字符写入报错或乱码；
- **应用账号不要用 root**：泄露后影响面完全不同；
- **`SET GLOBAL` 重启即失效**：需要长期生效请写进 `my.cnf` 的 `[mysqld]` 段；
- 后台跑 `mysqldump` 做每日备份，至少保留 7 天。

---

## 三、配置环境变量

```bash
cp deploy/.env.example .env
vim .env      # 必填：DB_PASSWORD、JWT_SECRET、CORS_ORIGINS
python -c "import secrets; print(secrets.token_hex(32))"   # 生成 JWT_SECRET
```

`.env` 含密钥，不要提交到版本库（`.gitignore` 已排除）。
生产也可以用 systemd `Environment=` 或进程管理器注入环境变量，优先级高于 `.env`。

---

## 四、方式一：本机直接运行（开发 / 冒烟验证）

```bash
pip install -r requirements.txt
cp .env.example .env       # 仓库根的开发模板：single + SQLite + memory
python think.py db-migrate --upgrade
python think.py run
```

访问 `http://127.0.0.1:8000/docs` 查看接口文档。

---

## 五、方式二：Gunicorn 多进程（Linux 生产）

```bash
.venv/bin/python think.py db-migrate --upgrade
.venv/bin/gunicorn -c deploy/gunicorn.conf.py main:app
```

关键参数（`gunicorn.conf.py`）：

| 参数 | 默认 | 说明 |
|---|---|---|
| `workers` | 环境变量 `GUNICORN_WORKERS`，否则 `CPU × 2 + 1` | 生产务必显式指定，便于按内存规划 |
| `worker_class` | `uvicorn.workers.UvicornWorker` | 跑 ASGI 必须用此类型 |
| `preload_app` | `True` | 降低内存；连接在 lifespan 内建立，fork 安全 |
| `max_requests` | `2000` | 缓解潜在内存泄漏，附随机抖动防同时重启 |
| `timeout` | 120 | 长任务请改用后台队列，不要一味调大 |

**容量参考**：常驻内存约 `worker 数 × 应用基线`，数据库连接数约
`workers × (DB_POOL_SIZE + DB_MAX_OVERFLOW)`，必须小于 MySQL 的 `max_connections`。

---

## 六、方式三：systemd 守护（推荐）

`deploy/thinkpython.service` 已包含进程守护、日志接管与最小权限约束：

```bash
sudo cp deploy/thinkpython.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now thinkpython
sudo systemctl status thinkpython
sudo journalctl -u thinkpython -f
```

发布新版本：

```bash
cd /opt/thinkpython
sudo -u thinkpython git pull
sudo -u thinkpython .venv/bin/pip install -r requirements.txt -r requirements-prod.txt
sudo -u thinkpython .venv/bin/python think.py db-migrate --upgrade   # 迁移单独执行
sudo systemctl reload thinkpython                                   # HUP 平滑重启 worker
```

> 不要把迁移写进 `ExecReload`：迁移失败会让平滑重启变成反复重启。
> 多实例部署时，迁移应作为发布流程的独立步骤，避免并发 DDL。

---

## 七、方式四：Nginx 反向代理 + HTTPS

```bash
sudo cp deploy/nginx.conf /etc/nginx/conf.d/thinkpython.conf
sudo vim /etc/nginx/conf.d/thinkpython.conf   # 改 server_name 与 uploads 实际路径
sudo nginx -t && sudo systemctl reload nginx
```

`nginx.conf` 已处理：

- `/uploads/` 由 Nginx 直接读磁盘（应用不参与文件传输）；
- `/uploads/.chunks/` 强制 404（分片未合并前不可访问）；
- 统一拒绝 `.env`、`.git` 等隐藏路径；
- `X-Forwarded-For` / `X-Forwarded-Proto` 透传，配合 `.env` 的 `TRUST_PROXY=true`
  才能拿到真实客户端 IP（否则限流会把所有用户算成同一个 IP）。

### SSL 证书

把证书放到 `deploy/ssl/`（或直接指向 `/etc/letsencrypt/live/<域名>/`）：

```
deploy/ssl/fullchain.pem   # 证书链
deploy/ssl/privkey.pem     # 私钥
```

然后取消 `nginx.conf` 底部 HTTPS `server` 块的注释，改 `server_name` 为本域名，
`sudo systemctl reload nginx`。获取方式见 `deploy/ssl/README.md`。

---

## 八、数据库迁移

```bash
.venv/bin/python think.py db-migrate --upgrade     # 升级到最新
.venv/bin/python think.py db-migrate --current     # 查看当前版本
.venv/bin/python think.py db-migrate --downgrade   # 回滚一个版本
```

迁移失败会返回**非零退出码**，CI 与发布脚本据此中止，不会带病上线。

---

## 九、生产检查清单

- [ ] `APP_DEBUG=false`（同时关闭 `/docs`，默认 JWT 密钥将拒绝启动）
- [ ] `JWT_SECRET` 为 64 位随机值
- [ ] 数据库应用账号非 root，密码为强随机值
- [ ] `CORS_ORIGINS` 为具体域名，未使用 `*`
- [ ] `AUTH_ENABLED=true`、`RATE_LIMIT_ENABLED=true`
- [ ] 数据库与 Redis 只监听内网 / 本机，不对公网暴露
- [ ] Nginx 之后部署时 `TRUST_PROXY=true`
- [ ] SSL 证书已配置，80 端口重定向到 443
- [ ] 已配置数据库定时备份与日志轮转
- [ ] `python think.py db-migrate --current` 与代码版本一致

---

## 十、故障排查

| 现象 | 排查方向 |
|---|---|
| 服务反复重启 | `journalctl -u thinkpython -n 100`；多为迁移失败或环境变量缺失 |
| 启动即退出并提示密钥 | 生产模式下 `JWT_SECRET` 仍是默认值，换掉即可 |
| `/health` 502 | 应用未就绪或端口不符：`ss -lntp \| grep 8000`；再看 Nginx error_log |
| 401 全部接口 | 请求未带 `Authorization: Bearer`，或路径未加入免认证白名单 |
| 数据库连接失败 | 检查 `DB_HOST/DB_PORT/DB_USER/DB_PASSWORD`，以及 `max_connections` 是否够用 |
| `Too many connections` | worker 数 × 池大小超过 MySQL 上限，调小 `DB_POOL_SIZE` 或加 `max_connections` |
| 上传文件 404 | `UPLOAD_DIR` 与 Nginx `alias` 指向同一目录；`UPLOAD_URL_PREFIX` 要与 location 前缀一致 |
| 限流误伤所有人 | Nginx 后未开 `TRUST_PROXY`，取到的是代理 IP |
| 迁移报 `MissingGreenlet` | 用了异步驱动 URL；`alembic/env.py` 会自动转同步，检查是否绕过 CLI 直接调用 |
