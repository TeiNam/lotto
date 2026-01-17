# config/settings.py
import os
from dotenv import load_dotenv
import logging
from utils.exceptions import ConfigurationError

# .env 파일 로드
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

# TODO: Anthropic API 설정 제거됨 - 완전 랜덤 생성 방식으로 전환
# ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
# ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-7-sonnet-20250219")
# ANTHROPIC_MAX_TOKENS = int(os.getenv("ANTHROPIC_MAX_TOKENS", "1000"))
# ANTHROPIC_TEMPERATURE = float(os.getenv("ANTHROPIC_TEMPERATURE", "0.7"))
# ANTHROPIC_FALLBACK_STRATEGY = os.getenv("ANTHROPIC_FALLBACK_STRATEGY", "statistical")

# 로또 설정
MIN_NUMBER = 1
MAX_NUMBER = 45
NUMBERS_PER_DRAW = 6

# 예측 설정
DEFAULT_PREDICTION_COUNT = 5
# 개선된 가중치 시스템
CONTINUITY_WEIGHT = 0.4    # 연속성에 40% 가중치
FREQUENCY_WEIGHT = 0.2     # 빈도에 20% 가중치
DISTRIBUTION_WEIGHT = 0.2  # 번호 분포에 20% 가중치
PARITY_WEIGHT = 0.1        # 홀짝 균형에 10% 가중치
SUM_RANGE_WEIGHT = 0.1     # 합계 범위에 10% 가중치

# 캐시 설정
ENABLE_CACHE = os.getenv("ENABLE_CACHE", "true").lower() == "true"
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # 초 단위 (기본값: 1시간)

# TODO: 슬랙 웹훅 설정 제거됨 - Telegram으로 전환 예정
# SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')

# Telegram 설정
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# TODO: 필수 환경 변수 목록에서 ANTHROPIC_API_KEY와 SLACK_WEBHOOK_URL 제거됨
# REQUIRED_ENV_VARS = [
#     'DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME', 'ANTHROPIC_API_KEY',
#     'SLACK_WEBHOOK_URL'
# ]

def verify_required_env_vars():
    """필수 환경 변수 검증"""
    # TODO: ANTHROPIC_API_KEY 제거됨
    required_vars = ["DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        error_msg = f"다음 필수 환경 변수가 설정되지 않았습니다: {', '.join(missing_vars)}"
        logger.error(error_msg)
        raise ConfigurationError(error_msg)

    logger.info("모든 필수 환경 변수가 설정되었습니다.")