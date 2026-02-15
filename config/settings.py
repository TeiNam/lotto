# config/settings.py
import os
from dotenv import load_dotenv
import logging
from utils.exceptions import ConfigurationError

load_dotenv()

logger = logging.getLogger("lotto_prediction")

# 데이터베이스 설정
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "user"),
    "password": os.getenv("DB_PASSWORD", "password"),
    "database": os.getenv("DB_NAME", "lotto_db"),
    "port": int(os.getenv("DB_PORT", "3306"))
}

# 로또 설정
MIN_NUMBER = 1
MAX_NUMBER = 45
NUMBERS_PER_DRAW = 6

# 예측 설정
DEFAULT_PREDICTION_COUNT = 5

# 캐시 설정
ENABLE_CACHE = os.getenv("ENABLE_CACHE", "true").lower() == "true"
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))

# Telegram 설정
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def verify_required_env_vars():
    """필수 환경 변수 검증"""
    required_vars = ["DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        error_msg = f"다음 필수 환경 변수가 설정되지 않았습니다: {', '.join(missing_vars)}"
        logger.error(error_msg)
        raise ConfigurationError(error_msg)

    logger.info("모든 필수 환경 변수가 설정되었습니다.")
