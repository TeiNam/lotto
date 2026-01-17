# evaluation/cross_validator.py
from typing import List, Dict, Any
import logging
from models.lotto_draw import LottoDraw
from services.data_service import DataService
# TODO: AnalysisService 제거됨 - SimplifiedPredictionService로 대체 예정
# from services.analysis_service import AnalysisService
from services.prediction_service import PredictionService
from evaluation.metrics import EvaluationMetrics

logger = logging.getLogger("lotto_prediction")


class CrossValidator:
    """예측 시스템 교차 검증"""

    def __init__(self, data_service: DataService):
        self.data_service = data_service

    def validate(self, test_draws: int = 10) -> Dict[str, Any]:
        """역사적 데이터를 사용한 교차 검증"""
        all_draws = self.data_service.get_all_draws()

        if len(all_draws) <= test_draws:
            logger.error(f"검증을 위한 충분한 데이터가 없습니다. 필요: >{test_draws}, 있음: {len(all_draws)}")
            return {
                "error": "검증을 위한 충분한 데이터가 없습니다.",
                "detail": [],
                "overall": {}
            }

        # 테스트 세트 분리
        test_data = all_draws[-test_draws:]

        results = []
        for i, test_draw in enumerate(test_data):
            logger.info(f"검증 진행 중 {i + 1}/{test_draws} (회차: {test_draw.draw_no})")

            # 테스트 회차까지의 데이터만 사용
            training_draws = all_draws[:-(test_draws - i)]

            # 임시 데이터 서비스 생성
            temp_data_service = DataService()
            temp_data_service.draws = training_draws
            temp_data_service.existing_combinations = {
                draw.get_numbers_tuple() for draw in training_draws
            }

            # 예측 서비스 생성
            prediction_service = PredictionService(temp_data_service)

            # 예측 실행
            predictions = prediction_service.predict_next_draw(num_predictions=5)
            predicted_combinations = [p.combination for p in predictions]

            # 평가
            actual_numbers = test_draw.numbers
            evaluation = EvaluationMetrics.evaluate_predictions(
                predicted_combinations, actual_numbers
            )

            evaluation["draw_no"] = test_draw.draw_no
            evaluation["actual_numbers"] = actual_numbers

            results.append(evaluation)

        # 종합 평가
        if not results:
            logger.error("검증 결과가 없습니다.")
            return {
                "error": "검증 결과가 없습니다.",
                "detail": [],
                "overall": {}
            }

        overall = {
            "avg_max_match_rate": sum(r["max_match_rate"] for r in results) / len(results),
            "avg_avg_match_rate": sum(r["avg_match_rate"] for r in results) / len(results),
            "draws_evaluated": len(results)
        }

        return {
            "detail": results,
            "overall": overall
        }