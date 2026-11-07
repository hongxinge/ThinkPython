-- ThinkPython MySQL 初始化脚本
--
-- 执行时机：MySQL 官方镜像首次初始化数据目录时（/docker-entrypoint-initdb.d/）
-- 只在数据卷为空时执行一次；已存在 db-data 卷时修改本文件不会生效。
-- 需要重新初始化时：docker compose down -v && docker compose up -d

-- ==============================
-- 数据库与字符集
-- ==============================
-- 统一 utf8mb4：支持 emoji 与四字节字符，避免中文乱序
CREATE DATABASE IF NOT EXISTS `thinkpython`
    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

ALTER DATABASE `thinkpython`
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- ==============================
-- 服务端参数
-- ==============================
-- 业务时间统一东八区，避免时间字段与应用侧差 8 小时
SET GLOBAL time_zone = '+08:00';

-- 连接数上限：应 ≥ worker 数 × 每个 worker 的连接池大小 + 余量
-- 例：4 worker × (pool_size 10 + max_overflow 20) = 120，留余量后设 200
SET GLOBAL max_connections = 200;

-- 慢查询日志（定位性能问题的基础设施，阈值按业务调整）
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 1;

-- ==============================
-- 应用专用账号（可选，推荐生产启用）
-- ==============================
-- 应用不应直接使用 root。启用时同步修改 .env 的 DB_USER / DB_PASSWORD。
-- 注意：密码请使用强随机值，不要提交到版本库。
--
-- CREATE USER IF NOT EXISTS 'thinkpython'@'%' IDENTIFIED BY 'CHANGE_ME_STRONG_PASSWORD';
-- GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES
--     ON `thinkpython`.* TO 'thinkpython'@'%';
-- FLUSH PRIVILEGES;

-- ==============================
-- 时区表（可选）
-- ==============================
-- 若业务需要 CONVERT_TZ / 命名时区（如 'Asia/Shanghai'），需导入时区表：
--   mysql_tzinfo_to_sql /usr/share/zoneinfo | mysql -uroot -p mysql
-- 未导入时用数字偏移 '+08:00' 即可。
