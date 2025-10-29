import logging
import sys
from pathlib import Path
from typing import Optional
from app.config import settings


def setup_logging():
    """设置结构化日志系统"""
    
    # 创建日志目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    
    # 根日志器配置
    root_logger = logging.getLogger()
    root_logger.setLevel(
        logging.INFO if settings.NODE_ENV == "production" else logging.DEBUG
    )
    
    # 清除现有处理器
    root_logger.handlers.clear()
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 文件处理器（仅生产环境）
    if settings.NODE_ENV == "production":
        file_handler = logging.FileHandler(
            log_dir / "app.log",
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        
        # 错误日志文件
        error_handler = logging.FileHandler(
            log_dir / "error.log",
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        root_logger.addHandler(error_handler)
    
    # 设置第三方库日志级别
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.WARNING if settings.NODE_ENV == "production" else logging.INFO
    )
    
    return root_logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """获取日志器"""
    return logging.getLogger(name or __name__)


# 初始化日志系统
logger = setup_logging()