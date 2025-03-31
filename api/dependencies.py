# api/dependencies.py
import logging

from fastapi import Depends

from services.data_service import AsyncDataService
from services.prediction_service import AsyncPredictionService
from services.slack_service import SlackNotifier

logger = logging.getLogger("lotto_prediction")


def get_async_data_service():
    """비동기 DataService 의존성"""
    return AsyncDataService()


def get_async_prediction_service(
        data_service: AsyncDataService = Depends(get_async_data_service)
):
    """비동기 PredictionService 의존성"""
    return AsyncPredictionService(data_service)

async def get_slack_notifier() -> SlackNotifier:
    """슬랙 알림 서비스 인스턴스 반환"""
    try:
        return SlackNotifier()
    except Exception as e:
        logger.error(f"슬랙 알림 서비스 초기화 실패: {e}")
        raise