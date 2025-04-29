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
    def _apply_diversity_filter(self, predictions: List[LottoPrediction], min_distance=2, max_similar_pairs=10) -> List[LottoPrediction]:
        """조합 간 다양성 보장 필터"""
        if not predictions:
            return []
            
        filtered_predictions = []
        
        # 항상 가장 높은 점수의 조합은 포함
        filtered_predictions.append(predictions[0])
        
        for pred in predictions[1:]:
            # 이미 선택된 조합들과의 유사도 체크
            too_similar = False
            similar_pairs = 0
            
            for selected_pred in filtered_predictions:
                # 두 조합 간 공통 번호 수
                common_count = len(set(pred.combination).intersection(set(selected_pred.combination)))
                unique_count = 6 - common_count  # 서로 다른 번호 수
                
                # 공통 번호가 너무 많으면 유사하다고 판단
                if unique_count < min_distance:  # 최소 거리 미만
                    too_similar = True
                    break
                
                if common_count >= 4:  # 4개 이상 공통
                    similar_pairs += 1
                    if similar_pairs > max_similar_pairs:
                        too_similar = True
                        break
            
            # 충분히 다양하면 추가
            if not too_similar:
                filtered_predictions.append(pred)
        
        return filtered_predictions
        
    async def monte_carlo_validation(self, combinations: List[List[int]], analysis_results: Dict[str, Any], num_simulations=1000) -> List[float]:
        """몬테카를로 시뮬레이션으로 생성된 조합 검증"""
        import random
        import numpy as np
        
        # 실제 당첨 번호 분포 특성
        actual_parity_dist = analysis_results.get("parity_distribution", {})
        actual_sum_dist = analysis_results.get("sum_distribution", {})
        
        # 각 조합별 시뮬레이션 점수
        simulation_scores = []
        
        for combo in combinations:
            # 특성 계산
            odd_count = sum(1 for num in combo if num % 2 == 1)
            sum_value = sum(combo)
            
            # 합계 범위 결정
            sum_range = "low" if sum_value <= 100 else "high" if sum_value >= 151 else "medium"
            
            # 실제 분포와의 일치 확률
            parity_prob = actual_parity_dist.get(f"odd_{odd_count}_even_{6-odd_count}", 0)
            sum_prob = actual_sum_dist.get(sum_range, 0)
            
            # 무작위 시뮬레이션 (병렬 처리를 위해 축소)
            random_draws = [sorted(random.sample(range(1, 46), 6)) for _ in range(100)]
            
            # 생성된 조합과 유사한 무작위 조합의 비율 계산
            similar_draws = 0
            for draw in random_draws:
                draw_odd_count = sum(1 for num in draw if num % 2 == 1)
                draw_sum = sum(draw)
                draw_sum_range = "low" if draw_sum <= 100 else "high" if draw_sum >= 151 else "medium"
                
                if (f"odd_{draw_odd_count}_even_{6-draw_odd_count}" == f"odd_{odd_count}_even_{6-odd_count}" and
                    draw_sum_range == sum_range):
                    similar_draws += 1
            
            simulation_score = similar_draws / len(random_draws)
            simulation_scores.append(simulation_score)
        
        # 점수 정규화
        max_score = max(simulation_scores) if simulation_scores and max(simulation_scores) > 0 else 1
        normalized_scores = [score / max_score for score in simulation_scores]
        
        return normalized_scores
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
    ) -> List[LottoPrediction]:]:
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

        # 점수 계산 - 병렬 처리
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

        # 다양성 필터 적용
        logger.info(f"다양성 필터 적용 전 유효 조합: {len(valid_combinations)}개")
        filtered_by_diversity = self._apply_diversity_filter(valid_combinations)
        logger.info(f"다양성 필터 적용 후 유효 조합: {len(filtered_by_diversity)}개")

        if not filtered_by_diversity:
            logger.warning("다양성 필터 적용 후 유효한 조합이 생성되지 않았습니다")
            # 다양성 필터를 적용하지 않은 원본 결과 반환
            return valid_combinations

        return filtered_by_diversity

    async def _score_combination(
            self,
            combo: List[int],
            last_numbers: List[int],
            continuity_probs: Dict[int, float],
            number_frequency: Dict[int, int]
    ) -> Optional[LottoPrediction]:
        """조합 점수 계산 (비동기) - 개선된 통계 기반 점수 시스템"""
        # 분석 서비스 가져오기
        all_draws = self.data_service.get_all_draws()
        analysis_service = AnalysisService(all_draws)
        analysis_results = analysis_service.get_comprehensive_analysis()
        
        # 1. 이전 회차와의 연속성 계산
        common_count = len(set(combo).intersection(set(last_numbers)))
        continuity_score = continuity_probs.get(common_count, 0)

        # 2. 숫자 빈도 점수 (베이지안 확률 사용)
        bayesian_probs = analysis_results.get("bayesian_probabilities", {})
        if not bayesian_probs:
            # 베이지안 확률이 없으면 일반 빈도 사용
            max_freq = max(number_frequency.values()) if number_frequency else 1
            frequency_score = sum(
                number_frequency.get(n, 0) / max_freq
                for n in combo
            ) / 6
        else:
            # 베이지안 확률 사용
            frequency_score = sum(bayesian_probs.get(n, 1/45) for n in combo) / 6

        # 3. 번호 분포 점수 계산
        distribution_score = self._calculate_distribution_score(combo, analysis_results)
        
        # 4. 홀짝 균형 점수
        parity_score = self._calculate_parity_score(combo, analysis_results)
        
        # 5. 합계 범위 점수
        sum_score = self._calculate_sum_range_score(combo, analysis_results)

        # 통계적 패턴 검증 (유효성 검사)
        if not analysis_service.validate_statistical_patterns(combo):
            logger.debug(f"통계적 패턴 검증 실패: {combo}")
            # 유효하지 않은 패턴이면 점수 페널티 부여
            penalty = 0.5
            continuity_score *= penalty
            frequency_score *= penalty
            distribution_score *= penalty
            parity_score *= penalty
            sum_score *= penalty

        # 최종 점수 계산 (가중치 적용)
        final_score = (
            CONTINUITY_WEIGHT * continuity_score +
            FREQUENCY_WEIGHT * frequency_score +
            DISTRIBUTION_WEIGHT * distribution_score +
            PARITY_WEIGHT * parity_score +
            SUM_RANGE_WEIGHT * sum_score
        )

        # 예측 객체 생성
        return LottoPrediction(
            combination=combo,
            score=final_score,
            common_with_last=common_count
        )
        
    def _calculate_distribution_score(self, combo: List[int], analysis_results: Dict[str, Any]) -> float:
        """번호 분포 점수 계산 - 구간 분포 제약 완화"""
        # 실제 범위 분포 분석 (구간 분포에 대한 제약을 완화)
        range_distribution = analysis_results.get("range_distribution", {})
        
        # 번호 간격 분석 (gap analysis) 결과 활용
        gap_analysis = analysis_results.get("number_gap_analysis", {})
        
        # 정렬된 번호 목록
        sorted_combo = sorted(combo)
        
        # 번호 간 간격 계산
        gaps = [sorted_combo[i+1] - sorted_combo[i] for i in range(5)]
        
        # 간격 점수 계산 (실제 간격 분포와 유사할수록 높은 점수)
        gap_dist = gap_analysis.get("distribution", {})
        if gap_dist:
            # 각 간격이 실제 분포에서 나타나는 확률에 비례한 점수
            gap_scores = []
            for gap in gaps:
                # 실제 분포에서의 확률 (없으면 낮은 확률 부여)
                gap_prob = gap_dist.get(str(gap), 0) if isinstance(gap_dist, dict) else 0
                if gap_prob > 0:
                    # 로그 스케일로 변환하여 너무 작은 확률도 적절한 점수 부여
                    import math
                    score = 0.5 + 0.5 * math.log(gap_prob * 10 + 1) / math.log(11)
                    gap_scores.append(max(0.1, min(1.0, score)))
                else:
                    gap_scores.append(0.1)  # 매우 드문 간격
                    
            # 간격 점수 평균
            if gap_scores:
                return sum(gap_scores) / len(gap_scores)
        
        # 간격 분석 결과가 없으면 기본값
        return 0.5
        
    def _calculate_parity_score(self, combo: List[int], analysis_results: Dict[str, Any]) -> float:
        """홀짝 균형 점수 계산"""
        # 홀짝 분포 분석
        parity_distribution = analysis_results.get("parity_distribution", {})
        if not parity_distribution:
            return 0.5  # 기본값
            
        # 현재 조합의 홀짝 비율
        odd_count = sum(1 for num in combo if num % 2 == 1)
        parity_key = f"odd_{odd_count}_even_{6-odd_count}"
        
        # 실제 분포에서의 확률
        parity_prob = parity_distribution.get(parity_key, 0)
        
        # 확률에 기반한 점수 (최소 0.1, 최대 1.0)
        if parity_prob > 0:
            # 로그 스케일 적용하여 소수의 확률값도 적절한 점수 부여
            import math
            score = 0.5 + 0.5 * math.log(parity_prob * 10 + 1) / math.log(11)
            return max(0.1, min(1.0, score))
        else:
            return 0.1  # 이례적인 홀짝 비율
        
    def _calculate_sum_range_score(self, combo: List[int], analysis_results: Dict[str, Any]) -> float:
        """합계 범위 점수 계산"""
        # 합계 분포 분석
        sum_distribution = analysis_results.get("sum_distribution", {})
        if not "avg" in sum_distribution or not "std" in sum_distribution:
            # 기본 평균 및 표준편차 사용
            avg_sum = 130
            std_sum = 30
        else:
            avg_sum = sum_distribution.get("avg")
            std_sum = sum_distribution.get("std")
            
        # 현재 조합의 합계
        total_sum = sum(combo)
        
        # 정규분포에 기반한 점수 계산
        # Z-점수 계산
        z_score = abs(total_sum - avg_sum) / std_sum
        
        # Z-점수가 낮을수록 평균에 가까움 (더 좋은 점수)
        if z_score <= 1:  # 1 표준편차 이내
            return 1.0
        elif z_score <= 2:  # 2 표준편차 이내
            return 0.75
        elif z_score <= 3:  # 3 표준편차 이내
            return 0.5
        else:  # 3 표준편차 초과
            return 0.25