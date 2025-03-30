# evaluation/metrics.py
from typing import List, Dict, Any
import logging
import numpy as np

logger = logging.getLogger("lotto_prediction")


class EvaluationMetrics:
    """예측 평가 지표 계산"""

    @staticmethod
    def calculate_match_rate(predicted: List[int], actual: List[int]) -> Dict[str, Any]:
        """예측 번호와 실제 번호의 일치율 계산"""
        predicted_set = set(predicted)
        actual_set = set(actual)

        matches = len(predicted_set.intersection(actual_set))
        match_rate = matches / len(actual)

        return {
            "matches": matches,
            "match_rate": match_rate
        }

    @staticmethod
    def evaluate_predictions(
            predictions: List[List[int]],
            actual_numbers: List[int]
    ) -> Dict[str, Any]:
        """여러 예측 조합 평가"""
        match_rates = []

        for combo in predictions:
            result = EvaluationMetrics.calculate_match_rate(combo, actual_numbers)
            match_rates.append(result["match_rate"])

        if not match_rates:
            return {
                "predictions": 0,
                "max_match_rate": 0,
                "avg_match_rate": 0,
                "max_matches": 0
            }

        max_rate_index = np.argmax(match_rates)
        max_matches = int(match_rates[max_rate_index] * len(actual_numbers))

        return {
            "predictions": len(predictions),
            "max_match_rate": max(match_rates),
            "avg_match_rate": sum(match_rates) / len(match_rates),
            "max_matches": max_matches
        }