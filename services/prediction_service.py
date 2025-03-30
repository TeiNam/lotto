# services/prediction_service.py - 오류 처리 개선
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from models.prediction import LottoPrediction
from services.data_service import AsyncDataService
from services.analysis_service import AnalysisService
from services.rag_service import RAGService
from config.settings import CONTINUITY_WEIGHT, FREQUENCY_WEIGHT
from utils.exceptions import PredictionGenerationError, ValidationError, DataLoadError, AnalysisError, \
    LottoPredictionError

logger = logging.getLogger("lotto_prediction")


class AsyncPredictionService:
    """비동기 로또 번호 예측 서비스"""

    def __init__(self, data_service: AsyncDataService):
        self.data_service = data_service
        self.rag_service = RAGService()

    async def predict_next_draw(self, num_predictions: int = 5) -> Tuple[List[LottoPrediction], Dict[str, Any]]:
        """다음 회차 번호 예측 (비동기)"""
        # 입력 유효성 검증
        if num_predictions < 1:
            raise ValidationError(f"예측 개수는 1 이상이어야 합니다: {num_predictions}")

        # API 사용량 통계 초기화
        api_usage = {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "api_calls": 0,
            "estimated_cost": 0.0,
        }

        # 마지막 회차 데이터 가져오기
        last_draw = self.data_service.get_last_draw()
        if not last_draw:
            logger.error("마지막 회차 데이터를 찾을 수 없습니다")
            raise DataLoadError("마지막 회차 데이터를 찾을 수 없습니다")

        # 데이터 분석
        try:
            all_draws = self.data_service.get_all_draws()
            if not all_draws:
                raise DataLoadError("분석할 데이터가 없습니다")

            analysis_service = AnalysisService(all_draws)
            analysis_results = analysis_service.get_comprehensive_analysis()

            if not analysis_results:
                raise AnalysisError("데이터 분석에 실패했습니다")

        except Exception as e:
            logger.exception(f"데이터 분석 중 오류 발생: {e}")
            if isinstance(e, LottoPredictionError):
                raise
            raise AnalysisError(f"데이터 분석 중 오류 발생: {e}", original_error=e)

        # 마지막 회차 정보 추가
        analysis_results["last_draw"] = {
            "numbers": last_draw.numbers,
            "draw_no": last_draw.draw_no
        }

        # 후보 조합 생성 (비동기)
        try:
            raw_combinations, rag_api_usage = await self.rag_service.generate_combinations(
                analysis_results,
                num_combinations=max(10, num_predictions * 2)  # 최소 10개 이상 요청
            )

            # API 사용량 정보 업데이트
            if rag_api_usage:
                api_usage.update(rag_api_usage)

            if not raw_combinations:
                raise PredictionGenerationError("후보 조합 생성에 실패했습니다")

        except Exception as e:
            logger.exception(f"후보 조합 생성 중 오류 발생: {e}")
            if isinstance(e, LottoPredictionError):
                raise
            raise PredictionGenerationError(f"후보 조합 생성 중 오류 발생: {e}", original_error=e)

        # 후보 조합 필터링 및 점수 계산
        try:
            filtered_combinations = await self._filter_combinations(
                raw_combinations,
                last_draw.numbers,
                analysis_results
            )

            if not filtered_combinations:
                logger.warning("유효한 조합이 생성되지 않았습니다, 백업 전략 사용")
                # 백업 전략: 원본 조합으로 점수 계산
                filtered_combinations = await self._calculate_scores_only(
                    raw_combinations,
                    last_draw.numbers,
                    analysis_results
                )

            # 상위 N개 선택
            top_predictions = filtered_combinations[:num_predictions]

            if not top_predictions:
                raise PredictionGenerationError("최종 예측 조합 생성에 실패했습니다")

            logger.info(f"다음 회차 예측 완료: {len(top_predictions)}개 예측 생성")
            return top_predictions, api_usage

        except Exception as e:
            logger.exception(f"조합 필터링 중 오류 발생: {e}")
            if isinstance(e, LottoPredictionError):
                raise
            raise PredictionGenerationError(f"조합 필터링 중 오류 발생: {e}", original_error=e)

    async def _calculate_scores_only(
            self,
            combinations: List[List[int]],
            last_numbers: List[int],
            analysis_results: Dict[str, Any]
    ) -> List[LottoPrediction]:
        """조합 필터링 없이 점수만 계산"""
        # 연속성 확률 분포
        continuity_dist = analysis_results.get("continuity_distribution", {})
        total_draws = analysis_results.get("total_draws", 1)
        number_frequency = analysis_results.get("number_frequency", {})

        # 각 연속성 수준의 확률 계산
        continuity_probs = {
            k: v / total_draws
            for k, v in continuity_dist.items()
        }

        # 점수 계산 - 병렬 처리
        tasks = []
        for combo in combinations:
            tasks.append(self._score_combination(
                combo, last_numbers, continuity_probs, number_frequency
            ))

        scored_combinations = await asyncio.gather(*tasks)

        # None 값 필터링 후 정렬
        valid_combinations = [combo for combo in scored_combinations if combo is not None]
        valid_combinations.sort(key=lambda x: x.score, reverse=True)

        return valid_combinations

    async def _filter_combinations(
            self,
            combinations: List[List[int]],
            last_numbers: List[int],
            analysis_results: Dict[str, Any]
    ) -> List[LottoPrediction]:
        """생성된 조합 필터링 및 점수 부여 (비동기)"""
        # 연속성 확률 분포
        continuity_dist = analysis_results.get("continuity_distribution", {})
        total_draws = analysis_results.get("total_draws", 1)
        number_frequency = analysis_results.get("number_frequency", {})

        # 각 연속성 수준의 확률 계산
        continuity_probs = {
            k: v / total_draws
            for k, v in continuity_dist.items()
        }

        # 기존 조합 필터링 - 병렬 처리
        tasks = []
        for combo in combinations:
            if self.data_service.is_new_combination(combo):
                tasks.append(self._score_combination(
                    combo, last_numbers, continuity_probs, number_frequency
                ))

        scored_combinations = await asyncio.gather(*tasks)

        # None 값 필터링 후 정렬
        valid_combinations = [combo for combo in scored_combinations if combo is not None]
        valid_combinations.sort(key=lambda x: x.score, reverse=True)

        if not valid_combinations:
            logger.warning("유효한 조합이 생성되지 않았습니다")

        return valid_combinations

    async def _score_combination(
            self,
            combo: List[int],
            last_numbers: List[int],
            continuity_probs: Dict[int, float],
            number_frequency: Dict[int, int]
    ) -> Optional[LottoPrediction]:
        """조합 점수 계산 (비동기)"""
        # 이전 회차와의 연속성 계산
        common_count = len(set(combo).intersection(set(last_numbers)))

        # 연속성 점수 (실제 분포에 따른 확률)
        continuity_score = continuity_probs.get(common_count, 0)

        # 숫자 빈도 점수
        max_freq = max(number_frequency.values()) if number_frequency else 1
        frequency_score = sum(
            number_frequency.get(n, 0) / max_freq
            for n in combo
        ) / 6

        # 최종 점수 계산
        final_score = (
                CONTINUITY_WEIGHT * continuity_score +
                FREQUENCY_WEIGHT * frequency_score
        )

        # 예측 객체 생성
        return LottoPrediction(
            combination=combo,
            score=final_score,
            common_with_last=common_count
        )