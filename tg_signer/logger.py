import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler

# 更好的格式化，使用固定宽度的字段以便对齐
format_str = (
    "%(asctime)s | %(levelname)-8s | %(name)-30s | %(filename)-20s:%(lineno)-4d | %(message)s"
)
formatter = logging.Formatter(format_str, datefmt="%Y-%m-%d %H:%M:%S")


def configure_logger(
    log_level: str = "INFO",
    filename: str = "tg-signer.log",
    max_bytes: int = 1024 * 1024 * 3,
    account: str = None,
):
    """
    配置日志记录器
    
    Args:
        log_level: 日志级别
        filename: 日志文件名（当account为None时使用）
        max_bytes: 单个日志文件最大字节数
        account: 账号名称，如果提供则创建账号专属日志目录和文件
    
    Returns:
        配置好的logger对象
    """
    level = log_level.strip().upper()
    logger = logging.getLogger("tg-signer")
    logger.setLevel(level)
    
    # 清除已有的handlers，避免重复
    logger.handlers.clear()

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 如果指定了账号，创建账号专属日志
    if account:
        log_dir = Path("logs") / account
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{account}.log"
        
        file_handler = RotatingFileHandler(
            str(log_file),
            maxBytes=max_bytes,
            backupCount=10,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        logger.info(f"账号 {account} 日志文件: {log_file}")
    else:
        # 使用通用日志文件
        file_handler = RotatingFileHandler(
            filename,
            maxBytes=max_bytes,
            backupCount=10,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    if os.environ.get("PYROGRAM_LOG_ON", "0") == "1":
        pyrogram_logger = logging.getLogger("pyrogram")
        pyrogram_logger.setLevel(level)
        pyrogram_logger.addHandler(console_handler)
    
    return logger


def get_account_logger(account: str, log_level: str = "INFO") -> logging.Logger:
    """
    获取账号专属的logger
    
    Args:
        account: 账号名称
        log_level: 日志级别
        
    Returns:
        账号专属的logger
    """
    logger_name = f"tg-signer.account.{account}"
    logger = logging.getLogger(logger_name)
    
    # 如果已经配置过，直接返回
    if logger.handlers:
        return logger
    
    level = log_level.strip().upper()
    logger.setLevel(level)
    
    # 创建账号专属日志目录
    log_dir = Path("logs") / account
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{account}.log"
    
    # 文件handler
    file_handler = RotatingFileHandler(
        str(log_file),
        maxBytes=1024 * 1024 * 3,
        backupCount=10,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 控制台handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


def log_step(logger: logging.Logger, step: str, status: str = "开始", details: str = ""):
    """
    记录步骤进度，使用统一格式
    
    Args:
        logger: logger对象
        step: 步骤名称
        status: 状态 (开始/完成/失败)
        details: 详细信息
    """
    status_emoji = {
        "开始": "▶",
        "完成": "✓",
        "失败": "✗",
        "跳过": "⊘",
    }
    emoji = status_emoji.get(status, "•")
    
    msg = f"{emoji} [{step}] {status}"
    if details:
        msg += f" - {details}"
    
    if status == "失败":
        logger.error(msg)
    elif status == "完成":
        logger.info(msg)
    else:
        logger.info(msg)


def log_separator(logger: logging.Logger, title: str = ""):
    """
    记录分隔线，用于区分不同的执行阶段
    
    Args:
        logger: logger对象
        title: 标题（可选）
    """
    if title:
        logger.info(f"{'='*20} {title} {'='*20}")
    else:
        logger.info("="*60)

