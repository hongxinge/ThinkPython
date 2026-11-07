"""统一日志配置

设计目标：
1. **一处配置，全局生效**：应用、CLI、迁移脚本共用同一套输出格式；
2. **可观测**：同时写控制台与文件，文件按大小轮转、限制保留份数；
3. **高性能**：文件写入使用 ``enqueue=True``（独立线程 + 队列），
   避免同步 I/O 阻塞事件循环；
4. **不拖垮业务**：日志目录不可写时自动降级为仅控制台输出，不抛异常；
5. **时区一致**：日志时间按 ``TIMEZONE`` 配置（默认 Asia/Shanghai）渲染，
   与数据库时间口径一致。

使用方式::

    from core.logger import setup_logging
    setup_logging()          # 幂等，重复调用不会重复添加 handler

    from loguru import logger
    logger.info("业务日志")
"""
import sys
from typing import Optional

from loguru import logger

from config.app import APP_CONFIG

# 是否已完成初始化（幂等标记）
_configured = False

# 控制台格式：时间 | 级别 | 模块:函数:行号 | 消息
_CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

# 文件格式：纯文本，便于 grep 与日志采集
_FILE_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"


def _resolve_timezone(name: str):
    """解析时区名，失败时返回 None（回退到系统本地时区）"""
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(name)
    except Exception:  # noqa: BLE001 - 无效时区不应阻断启动
        return None


def _make_patcher(tzinfo):
    """构造 loguru patcher：把 record 时间转换到目标时区"""

    def patcher(record):
        if tzinfo is not None:
            record["time"] = record["time"].astimezone(tzinfo)

    return patcher


def setup_logging(level: Optional[str] = None) -> None:
    """初始化全局日志

    Args:
        level: 覆盖配置中的日志级别（可选），如 "DEBUG" / "INFO" / "WARNING"

    Notes:
        - 重复调用无副作用；
        - 文件 handler 创建失败时自动降级，仅保留控制台输出。
    """
    global _configured
    if _configured:
        return

    log_config = APP_CONFIG.get("log", {})
    log_level = (level or log_config.get("level") or "INFO").upper()
    tzinfo = _resolve_timezone(APP_CONFIG.get("timezone") or "Asia/Shanghai")

    # 移除 loguru 默认的 stderr handler，统一由本函数接管
    logger.remove()

    # 先设定时区 patcher，再注册 handler，确保首个日志就用正确时区
    logger.configure(patcher=_make_patcher(tzinfo))

    # 控制台输出：始终启用，容器环境由 stdout/stderr 采集
    logger.add(
        sys.stdout,
        level=log_level,
        format=_CONSOLE_FORMAT,
        colorize=sys.stdout.isatty(),
        backtrace=APP_CONFIG.get("debug", False),
        diagnose=APP_CONFIG.get("debug", False),
        enqueue=False,  # 控制台为同步输出，避免日志顺序错乱
    )

    # 文件输出：按大小轮转，失败时降级
    log_file = log_config.get("file")
    if log_file:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            logger.add(
                str(log_file),
                level=log_level,
                format=_FILE_FORMAT,
                rotation=log_config.get("max_bytes", 10 * 1024 * 1024),
                retention=log_config.get("backup_count", 5),
                encoding="utf-8",
                enqueue=True,  # 异步写入，避免阻塞事件循环
                backtrace=False,
                diagnose=False,  # 文件日志不记录变量值，避免泄露敏感数据
            )
        except (OSError, ValueError) as exc:
            logger.warning(f"文件日志初始化失败，仅使用控制台输出：{exc}")

    # 记录当前生效配置，便于排障
    _configured = True

    logger.debug(
        f"日志已初始化 | level={log_level} | timezone={APP_CONFIG.get('timezone')} | "
        f"file={log_file if log_file else 'disabled'}"
    )
