# services/analysis_service.py
import logging
from typing import Dict, List, Set, Tuple, Any
from models.lotto_draw import LottoDraw
from collections import Counter
from utils.exceptions import AnalysisError
import numpy as np

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

    def calculate_bayesian_probabilities(self) -> Dict[int, float]:
        """베이지안 확률 계산 (라플라스 스무딩 적용)"""
        try:
            if not self.draws:
                logger.warning("베이지안 분석을 위한 데이터가 없습니다")
                return {i: 1/45 for i in range(1, 46)}  # 균등 확률 반환

            # 사전 확률은 균등 분포 (1/45)
            prior = {i: 1/45 for i in range(1, 46)}
            
            # 빈도 데이터
            frequency = self.analyze_number_frequency()
            total_draws = len(self.draws)
            
            # 라플라스 스무딩 적용 (과적합 방지)
            alpha = 2  # 평활화 계수
            
            # 베이지안 갱신
            posterior = {}
            for num in range(1, 46):
                # 관측 빈도 + 스무딩 / 전체 관측 + 스무딩 * 가능한 결과 수
                posterior[num] = (frequency.get(num, 0) + alpha) / (total_draws * 6 + alpha * 45)
            
            return posterior
            
        except Exception as e:
            logger.error(f"베이지안 확률 분석 오류: {e}")
            raise AnalysisError(f"베이지안 확률 분석 중 오류 발생: {e}", original_error=e)

    def build_markov_transition_matrix(self) -> Dict[int, Dict[int, float]]:
        """마르코프 체인 전이 행렬 구축"""
        try:
            if len(self.draws) < 2:
                logger.warning("마르코프 체인 분석을 위한 충분한 데이터가 없습니다")
                return {i: {j: 1/45 for j in range(1, 46)} for i in range(1, 46)}
            
            # 번호별 등장 후 다음 회차 등장 확률 계산
            transition_matrix = {i: {j: 0 for j in range(1, 46)} for i in range(1, 46)}
            
            for i in range(1, len(self.draws)):
                prev_numbers = set(self.draws[i-1].numbers)
                curr_numbers = set(self.draws[i].numbers)
                
                # 이전 회차에 등장한 번호가 다음 회차에 등장할 확률
                for prev_num in prev_numbers:
                    for curr_num in range(1, 46):
                        transition_matrix[prev_num][curr_num] += 1 if curr_num in curr_numbers else 0
            
            # 확률로 정규화
            for i in range(1, 46):
                total = sum(transition_matrix[i].values())
                if total > 0:
                    for j in range(1, 46):
                        transition_matrix[i][j] /= total
                else:
                    # 데이터가 없는 경우 균등 확률 부여
                    for j in range(1, 46):
                        transition_matrix[i][j] = 1/45
            
            return transition_matrix
            
        except Exception as e:
            logger.error(f"마르코프 체인 분석 오류: {e}")
            raise AnalysisError(f"마르코프 체인 분석 중 오류 발생: {e}", original_error=e)

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
            sum_values = []

            for draw in self.draws:
                total_sum = sum(draw.numbers)
                sum_values.append(total_sum)
                for range_name, (min_val, max_val) in sum_ranges.items():
                    if min_val <= total_sum <= max_val:
                        range_counts[range_name] += 1
                        break

            total_draws = len(self.draws)
            
            # 합계 범위별 확률
            distribution = {
                range_name: count / total_draws
                for range_name, count in range_counts.items()
            }
            
            # 평균 및 표준편차 추가
            distribution["avg"] = np.mean(sum_values)
            distribution["std"] = np.std(sum_values)
            
            return distribution
            
        except Exception as e:
            logger.error(f"합계 분석 오류: {e}")
            raise AnalysisError(f"합계 분석 중 오류 발생: {e}", original_error=e)

    def analyze_number_gaps(self) -> Dict[str, Any]:
        """번호 간 간격 분석"""
        try:
            if not self.draws:
                logger.warning("간격 분석을 위한 데이터가 없습니다")
                return {}
            
            gaps = []
            
            for draw in self.draws:
                sorted_numbers = sorted(draw.numbers)
                draw_gaps = [sorted_numbers[i+1] - sorted_numbers[i] for i in range(5)]
                gaps.extend(draw_gaps)
            
            gap_distribution = dict(Counter(gaps))
            
            # 평균 및 표준편차
            gap_stats = {
                "distribution": gap_distribution,
                "avg": np.mean(gaps),
                "std": np.std(gaps)
            }
            
            return gap_stats
            
        except Exception as e:
            logger.error(f"간격 분석 오류: {e}")
            raise AnalysisError(f"간격 분석 중 오류 발생: {e}", original_error=e)

    def analyze_number_ranges(self) -> Dict[str, float]:
        """번호 구간별 분포 분석"""
        try:
            if not self.draws:
                logger.warning("구간 분석을 위한 데이터가 없습니다")
                return {}
            
            ranges = {
                "1-9": (1, 9),
                "10-19": (10, 19),
                "20-29": (20, 29),
                "30-39": (30, 39),
                "40-45": (40, 45)
            }
            
            range_counts = {range_name: 0 for range_name in ranges}
            total_numbers = 0
            
            for draw in self.draws:
                for num in draw.numbers:
                    total_numbers += 1
                    for range_name, (min_val, max_val) in ranges.items():
                        if min_val <= num <= max_val:
                            range_counts[range_name] += 1
                            break
            
            # 각 구간별 확률 계산
            distribution = {
                range_name: count / total_numbers
                for range_name, count in range_counts.items()
            }
            
            return distribution
            
        except Exception as e:
            logger.error(f"구간 분석 오류: {e}")
            raise AnalysisError(f"구간 분석 중 오류 발생: {e}", original_error=e)

    def get_consecutive_number_stats(self) -> Dict[str, Any]:
        """연속된 숫자 패턴 분석"""
        try:
            if not self.draws:
                logger.warning("연속 숫자 분석을 위한 데이터가 없습니다")
                return {}
            
            consecutive_counts = []
            
            for draw in self.draws:
                sorted_numbers = sorted(draw.numbers)
                consecutive_count = 0
                
                for i in range(5):
                    if sorted_numbers[i+1] - sorted_numbers[i] == 1:
                        consecutive_count += 1
                
                consecutive_counts.append(consecutive_count)
            
            distribution = dict(Counter(consecutive_counts))
            total_draws = len(self.draws)
            
            # 각 연속 갯수별 확률
            stats = {
                str(count): freq / total_draws
                for count, freq in distribution.items()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"연속 숫자 분석 오류: {e}")
            raise AnalysisError(f"연속 숫자 분석 중 오류 발생: {e}", original_error=e)

    def get_comprehensive_analysis(self) -> Dict:
        """종합적인 분석 결과 생성"""
        try:
            if not self.draws:
                logger.error("분석할 데이터가 없습니다")
                raise AnalysisError("분석할 데이터가 없습니다")

            # 기본 분석
            number_frequency = self.analyze_number_frequency()
            continuity_distribution = self.analyze_continuity()
            parity_distribution = self.analyze_number_parity()
            sum_distribution = self.analyze_sum_distribution()

            # 새로운 고급 분석
            bayesian_probabilities = self.calculate_bayesian_probabilities()
            markov_transition = self.build_markov_transition_matrix()
            number_gap_analysis = self.analyze_number_gaps()
            range_distribution = self.analyze_number_ranges()
            consecutive_stats = self.get_consecutive_number_stats()

            # 빈도 기반 번호 통계
            sorted_numbers = sorted(
                [(num, freq) for num, freq in number_frequency.items()],
                key=lambda x: x[1],
                reverse=True
            )
            hot_numbers = [num for num, _ in sorted_numbers[:10]]
            cold_numbers = [num for num, _ in sorted_numbers[-10:]]

            # 베이지안 확률 기반 번호 통계
            sorted_bayes = sorted(
                [(num, prob) for num, prob in bayesian_probabilities.items()],
                key=lambda x: x[1],
                reverse=True
            )
            bayes_hot_numbers = [num for num, _ in sorted_bayes[:10]]
            bayes_cold_numbers = [num for num, _ in sorted_bayes[-10:]]

            total_draws = len(self.draws)

            return {
                "number_frequency": number_frequency,
                "bayesian_probabilities": bayesian_probabilities,
                "markov_transition": markov_transition,
                "continuity_distribution": continuity_distribution,
                "parity_distribution": parity_distribution,
                "sum_distribution": sum_distribution,
                "number_gap_analysis": number_gap_analysis,
                "range_distribution": range_distribution,
                "consecutive_stats": consecutive_stats,
                "hot_numbers": hot_numbers,
                "cold_numbers": cold_numbers,
                "bayes_hot_numbers": bayes_hot_numbers,
                "bayes_cold_numbers": bayes_cold_numbers,
                "total_draws": total_draws
            }
        except AnalysisError:
            # 이미 처리된 분석 오류는 그대로 전달
            raise
        except Exception as e:
            # 다른 예외는 AnalysisError로 래핑
            logger.error(f"종합 분석 오류: {e}")
            raise AnalysisError(f"종합 분석 중 오류 발생: {e}", original_error=e)
    
    def validate_statistical_patterns(self, combination: List[int]) -> bool:
        """통계적 패턴 유효성 검증 - 구간 분산 제약 완화"""
        try:
            if not self.draws:
                logger.warning("패턴 검증을 위한 데이터가 없습니다")
                return True  # 데이터 없으면 모든 조합 허용
            
            # 1. 홀짝 검증
            odd_count = sum(1 for num in combination if num % 2 == 1)
            parity_key = f"odd_{odd_count}_even_{6-odd_count}"
            parity_distribution = self.analyze_number_parity()
            parity_prob = parity_distribution.get(parity_key, 0)
            
            # 통계적으로 매우 비정상적인 홀짝 분포인지 검증 (5% 미만 확률)
            if parity_prob < 0.05:
                logger.debug(f"홀짝 분포 검증 실패: {parity_key}, 확률={parity_prob:.4f}")
                return False
            
            # 2. 합계 검증
            total_sum = sum(combination)
            sum_distribution = self.analyze_sum_distribution()
            avg_sum = sum_distribution.get("avg", 130)
            std_sum = sum_distribution.get("std", 30)
            
            # 평균에서 2.5 표준편차 이상 벗어나는지 검증 (더 관대하게 조정)
            if total_sum < avg_sum - 2.5*std_sum or total_sum > avg_sum + 2.5*std_sum:
                logger.debug(f"합계 검증 실패: {total_sum}, 허용범위={avg_sum - 2.5*std_sum:.1f}~{avg_sum + 2.5*std_sum:.1f}")
                return False
            
            # 3. 연속 번호 검증
            sorted_combo = sorted(combination)
            consecutive_count = sum(1 for i in range(5) if sorted_combo[i+1] - sorted_combo[i] == 1)
            consecutive_stats = self.get_consecutive_number_stats()
            
            # 극단적인 연속 번호 패턴인지 검증 (더 관대하게 조정)
            if str(consecutive_count) in consecutive_stats:
                consecutive_prob = consecutive_stats[str(consecutive_count)]
                if consecutive_prob < 0.03:  # 3% 미만 확률
                    logger.debug(f"연속 번호 검증 실패: {consecutive_count}개 연속, 확률={consecutive_prob:.4f}")
                    return False
            
            # 4. 구간 분포 검증 (완화됨)
            # 구간별 분포는 검증에서 제외 - 실제로 몰려서 나오는 경우가 많음
            
            return True
            
        except Exception as e:
            logger.error(f"패턴 검증 오류: {e}")
            # 오류 발생 시 검증 통과 처리 (거부하지 않음)
            return True
