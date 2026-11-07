# SSL 证书目录

把生产证书放在此目录，容器内挂载路径为 `/etc/nginx/ssl`：

```
deploy/ssl/fullchain.pem   # 证书链
deploy/ssl/privkey.pem     # 私钥
```

启用方式：取消 `deploy/nginx.conf` 底部 HTTPS server 块的注释，
把 `server_name` 改成本域名，然后 `docker compose restart nginx`。

获取免费证书（Let's Encrypt）示例：

```bash
certbot certonly --webroot -w /var/www/certbot -d your_domain.com
cp /etc/letsencrypt/live/your_domain.com/fullchain.pem deploy/ssl/
cp /etc/letsencrypt/live/your_domain.com/privkey.pem   deploy/ssl/
```

注意：证书与私钥已被 `.gitignore` 排除，**不要提交到版本库**。
