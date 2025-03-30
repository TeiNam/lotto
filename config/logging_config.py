# config/logging_config.py
import logging
import sys
from logging.handlers import RotatingFileHandler
import os


def setup_logging(log_dir="logs"):
    # 로그 디렉토리 생성
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 로거 설정
    logger = logging.getLogger("lotto_prediction")
    logger.setLevel(logging.INFO)

    # 파일 핸들러
    file_handler = RotatingFileHandler(
        f"{log_dir}/lotto_prediction.log",
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3
    )
    file_handler.setLevel(logging.INFO)

    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # 포맷 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # 핸들러 추가
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger