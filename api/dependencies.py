# api/dependencies.py
import logging
import os

from fastapi import Depends

from services.data_service import AsyncDataService
from services.prediction_service import AsyncPredictionService
from services.simplified_prediction_service import SimplifiedPredictionService
from services.random_generator import RandomGenerator
from services.duplicate_checker import DuplicateChecker
from services.telegram_notifier import TelegramNotifier

logger = logging.getLogger("lotto_prediction")


def get_async_data_service():
    """비동기 DataService 의존성"""
    return AsyncDataService()


def get_async_prediction_service(
        data_service: AsyncDataService = Depends(get_async_data_service)
):
    """비동기 PredictionService 의존성 (기존 서비스 - 호환성 유지)"""
    return AsyncPredictionService(data_service)


def get_random_generator() -> RandomGenerator:
    """RandomGenerator 의존성"""
    return RandomGenerator()


def get_duplicate_checker(
    data_service: AsyncDataService = Depends(get_async_data_service)
) -> DuplicateChecker:
    """DuplicateChecker 의존성"""
    return DuplicateChecker(data_service)


def get_simplified_prediction_service(
    random_generator: RandomGenerator = Depends(get_random_generator),
    duplicate_checker: DuplicateChecker = Depends(get_duplicate_checker),
    data_service: AsyncDataService = Depends(get_async_data_service)
) -> SimplifiedPredictionService:
    """SimplifiedPredictionService 의존성"""
    return SimplifiedPredictionService(
        random_generator=random_generator,
        duplicate_checker=duplicate_checker,
        data_service=data_service
    )


def get_telegram_notifier() -> TelegramNotifier:
    """TelegramNotifier 의존성
    
    환경 변수에서 Telegram Bot 설정을 로드합니다.
    
    Returns:
        TelegramNotifier 인스턴스
        
    Raises:
        ValueError: 필수 환경 변수가 없는 경우
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN 환경 변수가 설정되지 않았습니다")
        raise ValueError("TELEGRAM_BOT_TOKEN 환경 변수가 필요합니다")
    
    if not chat_id:
        logger.warning("TELEGRAM_CHAT_ID 환경 변수가 설정되지 않았습니다")
        raise ValueError("TELEGRAM_CHAT_ID 환경 변수가 필요합니다")
    
    return TelegramNotifier(bot_token=bot_token, chat_id=chat_id)