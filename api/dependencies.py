# api/dependencies.py
from fastapi import Depends
from services.data_service import AsyncDataService
from services.prediction_service import AsyncPredictionService
import logging

logger = logging.getLogger("lotto_prediction")

def get_async_data_service():
    """비동기 DataService 의존성"""
    return AsyncDataService()

def get_async_prediction_service(
    data_service: AsyncDataService = Depends(get_async_data_service)
):
    """비동기 PredictionService 의존성"""
    return AsyncPredictionService(data_service)