# api/dependencies.py
import logging
import os

from fastapi import Depends

from services.data_service import AsyncDataService
from services.simplified_prediction_service import SimplifiedPredictionService
from services.random_generator import RandomGenerator
from services.duplicate_checker import DuplicateChecker

logger = logging.getLogger("lotto_prediction")


def get_async_data_service():
    """비동기 DataService 의존성"""
    return AsyncDataService()


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
