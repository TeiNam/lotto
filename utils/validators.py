# utils/validators.py
from typing import List, Optional
import logging

logger = logging.getLogger("lotto_prediction")


class LottoValidator:
    """로또 번호 유효성 검증 유틸리티"""

    @staticmethod
    def validate_numbers(numbers: List[int], min_num: int = 1, max_num: int = 45, count: int = 6) -> bool:
        """로또 번호 유효성 검사"""
        if not isinstance(numbers, list):
            logger.error(f"유효하지 않은 번호 형식: {type(numbers)}")
            return False

        if len(numbers) != count:
            logger.error(f"번호 개수 불일치: 예상 {count}, 실제 {len(numbers)}")
            return False

        if len(set(numbers)) != count:
            logger.error("중복 번호 발견")
            return False

        if not all(min_num <= num <= max_num for num in numbers):
            logger.error(f"범위를 벗어난 번호 발견 (유효 범위: {min_num}-{max_num})")
            return False

        return True