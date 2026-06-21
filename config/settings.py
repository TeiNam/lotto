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


def _parse_admin_ids(raw: str) -> set:
    """쉼표로 구분된 관리자 텔레그램 user_id 목록을 정수 set으로 파싱"""
    ids = set()
    for part in (raw or "").replace(" ", "").split(","):
        if not part:
            continue
        try:
            ids.add(int(part))
        except ValueError:
            logger.warning(f"잘못된 TELEGRAM_ADMIN_IDS 항목 무시: {part}")
    return ids


# 봇 사용 허용 관리자(텔레그램 user_id) 목록. 비어 있으면 모든 사용자 차단.
TELEGRAM_ADMIN_IDS = _parse_admin_ids(os.getenv("TELEGRAM_ADMIN_IDS", ""))

# TELEGRAM_ADMIN_IDS 미설정 시, 개인 채팅용 TELEGRAM_CHAT_ID를 관리자로 사용한다.
# (1:1 DM에서는 chat_id == user_id 이므로. 단, 그룹 chat_id(음수)는 user_id가 아니라 제외)
if not TELEGRAM_ADMIN_IDS and TELEGRAM_CHAT_ID:
    _chat_id = str(TELEGRAM_CHAT_ID).strip()
    if _chat_id.isdigit():  # 양수(개인)만 해당
        TELEGRAM_ADMIN_IDS = {int(_chat_id)}

# 동행복권 계정 (운영자 본인 단일 계정). 구매/잔액조회에 사용.
DHL_USERNAME = os.getenv("DHL_USERNAME")
DHL_PASSWORD = os.getenv("DHL_PASSWORD")


def verify_required_env_vars():
    """필수 환경 변수 검증"""
    required_vars = ["DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        error_msg = f"다음 필수 환경 변수가 설정되지 않았습니다: {', '.join(missing_vars)}"
        logger.error(error_msg)
        raise ConfigurationError(error_msg)

    logger.info("모든 필수 환경 변수가 설정되었습니다.")
