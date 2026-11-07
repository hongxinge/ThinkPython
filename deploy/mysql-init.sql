-- ThinkPython MySQL 初始化脚本
--
-- 执行时机：MySQL 首次部署后，用 root 手工执行一次（幂等，可重复执行）
--   mysql -u root -p < deploy/mysql-init.sql
-- 注意：SET GLOBAL 只影响当前运行实例，重启后失效；
-- 需要长期生效请把这些参数写入 my.cnf 的 [mysqld] 段。

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
-- 应用专用账号（生产必须启用）
-- ==============================
-- 应用不应直接使用 root。取消下面几行注释、改成强随机密码，
-- 并同步修改 .env 的 DB_USER / DB_PASSWORD。
-- 应用与 MySQL 不同机时，把 'localhost' 改成具体内网网段（如 '10.0.0.%'）。
--
-- CREATE USER IF NOT EXISTS 'thinkpython'@'localhost' IDENTIFIED BY 'CHANGE_ME_STRONG_PASSWORD';
-- GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES
--     ON `thinkpython`.* TO 'thinkpython'@'localhost';
-- FLUSH PRIVILEGES;

-- ==============================
-- 时区表（可选）
-- ==============================
-- 若业务需要 CONVERT_TZ / 命名时区（如 'Asia/Shanghai'），需导入时区表：
--   mysql_tzinfo_to_sql /usr/share/zoneinfo | mysql -uroot -p mysql
-- 未导入时用数字偏移 '+08:00' 即可。
