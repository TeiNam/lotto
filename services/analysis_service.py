# services/analysis_service.py
import logging
from typing import Dict, List, Set, Tuple
from models.lotto_draw import LottoDraw
from collections import Counter
from utils.exceptions import AnalysisError

logger = logging.getLogger("lotto_prediction")


class AnalysisService:
    """로또 데이터 분석 서비스"""

    def __init__(self, draws: List[LottoDraw]):
        self.draws = draws

    def analyze_number_frequency(self) -> Dict[int, int]:
        """번호별 출현 빈도 분석"""
        try:
            if not self.draws:
                logger.warning("빈도 분석을 위한 데이터가 없습니다")
                return {}

            frequency = Counter()

            for draw in self.draws:
                frequency.update(draw.numbers)

            return dict(frequency)
        except Exception as e:
            logger.error(f"번호 빈도 분석 오류: {e}")
            raise AnalysisError(f"번호 빈도 분석 중 오류 발생: {e}", original_error=e)

    def analyze_continuity(self) -> Dict[int, int]:
        """이전 회차와의 연속성 분석 (중복 번호 수)"""
        try:
            if len(self.draws) < 2:
                logger.warning("연속성 분석을 위한 충분한 데이터가 없습니다")
                return {}

            continuity_counts = []

            for i in range(1, len(self.draws)):
                prev_numbers = set(self.draws[i - 1].numbers)
                curr_numbers = set(self.draws[i].numbers)
                common_count = len(prev_numbers.intersection(curr_numbers))
                continuity_counts.append(common_count)

            distribution = Counter(continuity_counts)
            return dict(distribution)
        except Exception as e:
            logger.error(f"연속성 분석 오류: {e}")
            raise AnalysisError(f"연속성 분석 중 오류 발생: {e}", original_error=e)

    def analyze_number_parity(self) -> Dict[str, float]:
        """홀짝 분포 분석"""
        try:
            if not self.draws:
                logger.warning("홀짝 분석을 위한 데이터가 없습니다")
                return {}

            odd_counts = []

            for draw in self.draws:
                odd_count = sum(1 for num in draw.numbers if num % 2 == 1)
                odd_counts.append(odd_count)

            parity_distribution = Counter(odd_counts)
            total_draws = len(self.draws)

            return {
                f"odd_{k}_even_{6 - k}": v / total_draws
                for k, v in parity_distribution.items()
            }
        except Exception as e:
            logger.error(f"홀짝 분석 오류: {e}")
            raise AnalysisError(f"홀짝 분석 중 오류 발생: {e}", original_error=e)

    def analyze_sum_distribution(self) -> Dict[str, float]:
        """번호 합계 범위 분석"""
        try:
            if not self.draws:
                logger.warning("합계 분석을 위한 데이터가 없습니다")
                return {}

            sum_ranges = {
                "low": (0, 100),
                "medium": (101, 150),
                "high": (151, 270)
            }

            range_counts = {range_name: 0 for range_name in sum_ranges}

            for draw in self.draws:
                total_sum = sum(draw.numbers)
                for range_name, (min_val, max_val) in sum_ranges.items():
                    if min_val <= total_sum <= max_val:
                        range_counts[range_name] += 1
                        break

            total_draws = len(self.draws)
            return {
                range_name: count / total_draws
                for range_name, count in range_counts.items()
            }
        except Exception as e:
            logger.error(f"합계 분석 오류: {e}")
            raise AnalysisError(f"합계 분석 중 오류 발생: {e}", original_error=e)

    def get_comprehensive_analysis(self) -> Dict:
        """종합적인 분석 결과 생성"""
        try:
            if not self.draws:
                logger.error("분석할 데이터가 없습니다")
                raise AnalysisError("분석할 데이터가 없습니다")

            number_frequency = self.analyze_number_frequency()
            continuity_distribution = self.analyze_continuity()
            parity_distribution = self.analyze_number_parity()
            sum_distribution = self.analyze_sum_distribution()

            # 빈도 기반 번호 통계
            sorted_numbers = sorted(
                [(num, freq) for num, freq in number_frequency.items()],
                key=lambda x: x[1],
                reverse=True
            )
            hot_numbers = [num for num, _ in sorted_numbers[:10]]
            cold_numbers = [num for num, _ in sorted_numbers[-10:]]

            total_draws = len(self.draws)

            return {
                "number_frequency": number_frequency,
                "continuity_distribution": continuity_distribution,
                "parity_distribution": parity_distribution,
                "sum_distribution": sum_distribution,
                "hot_numbers": hot_numbers,
                "cold_numbers": cold_numbers,
                "total_draws": total_draws
            }
        except AnalysisError:
            # 이미 처리된 분석 오류는 그대로 전달
            raise
        except Exception as e:
            # 다른 예외는 AnalysisError로 래핑
            logger.error(f"종합 분석 오류: {e}")
            raise AnalysisError(f"종합 분석 중 오류 발생: {e}", original_error=e)