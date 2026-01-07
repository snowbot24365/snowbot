"""
로깅 설정 유틸리티
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logger(
    name: str = "stock_trading",
    level: int = logging.INFO,
    log_to_file: bool = True,
    log_dir: str = "logs"
) -> logging.Logger:
    """
    로거 설정
    
    Args:
        name: 로거 이름
        level: 로그 레벨
        log_to_file: 파일 로깅 여부
        log_dir: 로그 디렉토리
    
    Returns:
        설정된 로거
    """
    logger = logging.getLogger(name)
    
    # 이미 핸들러가 있으면 스킵
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # 포맷터
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 파일 핸들러
    if log_to_file:
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)
        
        today = datetime.now().strftime('%Y%m%d')
        file_handler = logging.FileHandler(
            log_path / f"{name}_{today}.log",
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """
    로거 가져오기
    
    Args:
        name: 로거 이름 (없으면 기본 로거)
    
    Returns:
        로거
    """
    if name:
        return logging.getLogger(f"stock_trading.{name}")
    return logging.getLogger("stock_trading")


# 기본 로거 설정
default_logger = setup_logger()
