# SSL 证书目录

把生产证书放在此目录（Nginx 配置里的 `ssl_certificate` 指向它）：

```
deploy/ssl/fullchain.pem   # 证书链
deploy/ssl/privkey.pem     # 私钥
```

启用方式：取消 `deploy/nginx.conf` 底部 HTTPS server 块的注释，
把 `server_name` 改成本域名，然后 `sudo systemctl reload nginx`。

获取免费证书（Let's Encrypt）示例：

```bash
certbot certonly --webroot -w /var/www/certbot -d your_domain.com
cp /etc/letsencrypt/live/your_domain.com/fullchain.pem deploy/ssl/
cp /etc/letsencrypt/live/your_domain.com/privkey.pem   deploy/ssl/
```

也可以不拷贝，直接把 Nginx 的 `ssl_certificate` 指向
`/etc/letsencrypt/live/your_domain.com/fullchain.pem`，
并让 `certbot renew` 的 `--deploy-hook` 执行 `systemctl reload nginx`。

注意：证书与私钥已被 `.gitignore` 排除，**不要提交到版本库**。
