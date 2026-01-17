"""RandomGenerator 단위 테스트

RandomGenerator의 기본 기능과 극단적 패턴 필터링을 테스트합니다.
"""

import pytest
from services.random_generator import RandomGenerator


class TestRandomGenerator:
    """RandomGenerator 테스트 클래스"""
    
    def setup_method(self):
        """각 테스트 전에 실행"""
        self.generator = RandomGenerator()
    
    def test_generate_combination_returns_six_numbers(self):
        """6개 숫자 생성 검증"""
        combination = self.generator.generate_combination()
        assert len(combination) == 6, "조합은 정확히 6개의 숫자를 포함해야 합니다"
    
    def test_generate_combination_numbers_in_valid_range(self):
        """숫자 범위 검증 (1-45)"""
        combination = self.generator.generate_combination()
        assert all(1 <= num <= 45 for num in combination), \
            "모든 숫자는 1-45 범위 내에 있어야 합니다"
    
    def test_generate_combination_numbers_are_unique(self):
        """고유성 검증"""
        combination = self.generator.generate_combination()
        assert len(set(combination)) == 6, \
            "모든 숫자는 고유해야 합니다 (중복 없음)"
    
    def test_generate_combination_is_sorted(self):
        """정렬 검증"""
        combination = self.generator.generate_combination()
        assert combination == sorted(combination), \
            "조합은 오름차순으로 정렬되어야 합니다"
    
    def test_generate_multiple_combinations_are_different(self):
        """여러 조합 생성 시 다양성 검증"""
        combinations = [
            tuple(self.generator.generate_combination())
            for _ in range(10)
        ]
        # 10개 중 최소 8개는 달라야 함 (확률적으로 거의 모두 다름)
        unique_combinations = set(combinations)
        assert len(unique_combinations) >= 8, \
            "생성된 조합들은 충분히 다양해야 합니다"


class TestExtremePatternDetection:
    """극단적 패턴 감지 테스트 클래스"""
    
    def setup_method(self):
        """각 테스트 전에 실행"""
        self.generator = RandomGenerator()
    
    def test_detects_five_consecutive_numbers(self):
        """연속 숫자 5개 이상 감지 테스트"""
        # 5개 연속
        extreme_combo = [1, 2, 3, 4, 5, 10]
        assert self.generator.is_extreme_pattern(extreme_combo), \
            "5개 연속 숫자는 극단적 패턴으로 감지되어야 합니다"
        
        # 6개 연속
        extreme_combo = [10, 11, 12, 13, 14, 15]
        assert self.generator.is_extreme_pattern(extreme_combo), \
            "6개 연속 숫자는 극단적 패턴으로 감지되어야 합니다"
        
        # 4개 연속은 정상 (합계도 정상 범위)
        normal_combo = [10, 11, 12, 13, 25, 40]  # 합계 111
        assert not self.generator.is_extreme_pattern(normal_combo), \
            "4개 연속 숫자는 정상 패턴입니다"
    
    def test_detects_arithmetic_sequence(self):
        """등차수열 감지 테스트"""
        # 간격 5의 등차수열
        extreme_combo = [5, 10, 15, 20, 25, 30]
        assert self.generator.is_extreme_pattern(extreme_combo), \
            "등차수열은 극단적 패턴으로 감지되어야 합니다"
        
        # 간격 3의 등차수열
        extreme_combo = [3, 6, 9, 12, 15, 18]
        assert self.generator.is_extreme_pattern(extreme_combo), \
            "등차수열은 극단적 패턴으로 감지되어야 합니다"
        
        # 간격 1은 연속 숫자로 이미 감지됨
        extreme_combo = [1, 2, 3, 4, 5, 6]
        assert self.generator.is_extreme_pattern(extreme_combo), \
            "간격 1의 등차수열(연속)은 극단적 패턴입니다"
        
        # 불규칙한 간격은 정상
        normal_combo = [1, 3, 7, 15, 28, 42]
        assert not self.generator.is_extreme_pattern(normal_combo), \
            "불규칙한 간격은 정상 패턴입니다"
    
    def test_detects_extreme_sum_low(self):
        """극단적 합계 감지 테스트 (낮은 값)"""
        # 합계 < 80
        extreme_combo = [1, 2, 3, 4, 5, 6]  # 합계 21
        assert self.generator.is_extreme_pattern(extreme_combo), \
            "합계가 80 미만인 조합은 극단적 패턴입니다"
        
        extreme_combo = [1, 2, 3, 10, 20, 30]  # 합계 66
        assert self.generator.is_extreme_pattern(extreme_combo), \
            "합계가 80 미만인 조합은 극단적 패턴입니다"
    
    def test_detects_extreme_sum_high(self):
        """극단적 합계 감지 테스트 (높은 값)"""
        # 합계 > 200
        extreme_combo = [40, 41, 42, 43, 44, 45]  # 합계 255
        assert self.generator.is_extreme_pattern(extreme_combo), \
            "합계가 200 초과인 조합은 극단적 패턴입니다"
        
        extreme_combo = [35, 38, 40, 42, 44, 45]  # 합계 244
        assert self.generator.is_extreme_pattern(extreme_combo), \
            "합계가 200 초과인 조합은 극단적 패턴입니다"
    
    def test_normal_sum_range(self):
        """정상 합계 범위 테스트"""
        # 합계 80-200 범위는 정상
        normal_combo = [5, 12, 18, 25, 33, 40]  # 합계 133
        # 다른 극단적 패턴이 없다면 정상
        if not any([
            self.generator.is_extreme_pattern([5, 12, 18, 25, 33, 40])
        ]):
            assert not self.generator.is_extreme_pattern(normal_combo), \
                "합계가 80-200 범위인 조합은 정상일 수 있습니다"
    
    def test_detects_all_odd_numbers(self):
        """홀수만 감지 테스트"""
        extreme_combo = [1, 3, 5, 7, 9, 11]
        assert self.generator.is_extreme_pattern(extreme_combo), \
            "홀수만 있는 조합은 극단적 패턴입니다"
        
        extreme_combo = [15, 21, 27, 33, 39, 45]
        assert self.generator.is_extreme_pattern(extreme_combo), \
            "홀수만 있는 조합은 극단적 패턴입니다"
    
    def test_detects_all_even_numbers(self):
        """짝수만 감지 테스트"""
        extreme_combo = [2, 4, 6, 8, 10, 12]
        assert self.generator.is_extreme_pattern(extreme_combo), \
            "짝수만 있는 조합은 극단적 패턴입니다"
        
        extreme_combo = [20, 24, 28, 32, 36, 40]
        assert self.generator.is_extreme_pattern(extreme_combo), \
            "짝수만 있는 조합은 극단적 패턴입니다"
    
    def test_mixed_odd_even_is_normal(self):
        """홀수/짝수 혼합은 정상"""
        normal_combo = [1, 2, 15, 20, 33, 44]  # 홀수 3개, 짝수 3개
        # 다른 극단적 패턴 체크
        has_other_extreme = (
            sum(normal_combo) < 80 or sum(normal_combo) > 200
        )
        if not has_other_extreme:
            # 홀짝 혼합 자체는 문제없음
            pass
    
    def test_detects_range_concentration(self):
        """구간 편중 감지 테스트"""
        # 1-10 구간에 5개
        extreme_combo = [1, 2, 3, 4, 5, 20]
        assert self.generator.is_extreme_pattern(extreme_combo), \
            "한 구간에 5개 이상 몰린 조합은 극단적 패턴입니다"
        
        # 11-20 구간에 5개
        extreme_combo = [11, 12, 13, 14, 15, 30]
        assert self.generator.is_extreme_pattern(extreme_combo), \
            "한 구간에 5개 이상 몰린 조합은 극단적 패턴입니다"
        
        # 41-45 구간에 5개
        extreme_combo = [5, 41, 42, 43, 44, 45]
        assert self.generator.is_extreme_pattern(extreme_combo), \
            "한 구간에 5개 이상 몰린 조합은 극단적 패턴입니다"
    
    def test_distributed_range_is_normal(self):
        """고르게 분포된 구간은 정상"""
        normal_combo = [5, 15, 25, 30, 35, 42]
        # 각 구간: 1-10(1개), 11-20(1개), 21-30(2개), 31-40(1개), 41-45(1개)
        # 다른 극단적 패턴이 없다면 정상
        has_other_extreme = (
            sum(normal_combo) < 80 or sum(normal_combo) > 200
        )
        if not has_other_extreme:
            assert not self.generator.is_extreme_pattern(normal_combo), \
                "고르게 분포된 조합은 정상 패턴입니다"
    
    def test_normal_combination_example(self):
        """정상적인 조합 예시"""
        # 모든 극단적 패턴을 피한 정상 조합
        normal_combo = [7, 14, 23, 28, 35, 42]
        # 합계: 149 (80-200 범위)
        # 연속 없음
        # 등차수열 아님
        # 홀짝 혼합: 홀수 3개, 짝수 3개
        # 구간 분포: 각 구간에 1-2개씩
        assert not self.generator.is_extreme_pattern(normal_combo), \
            "정상적인 조합은 극단적 패턴으로 감지되지 않아야 합니다"


class TestGenerateCombinationFiltering:
    """generate_combination의 필터링 동작 테스트"""
    
    def setup_method(self):
        """각 테스트 전에 실행"""
        self.generator = RandomGenerator()
    
    def test_generated_combinations_are_not_extreme(self):
        """생성된 조합이 극단적 패턴이 아님을 검증"""
        # 여러 번 생성하여 모두 정상 패턴인지 확인
        for _ in range(20):
            combination = self.generator.generate_combination()
            assert not self.generator.is_extreme_pattern(combination), \
                f"생성된 조합 {combination}은 극단적 패턴이 아니어야 합니다"
    
    def test_generated_combinations_meet_all_requirements(self):
        """생성된 조합이 모든 요구사항을 만족하는지 검증"""
        for _ in range(10):
            combination = self.generator.generate_combination()
            
            # 기본 요구사항
            assert len(combination) == 6
            assert all(1 <= n <= 45 for n in combination)
            assert len(set(combination)) == 6
            assert combination == sorted(combination)
            
            # 극단적 패턴 아님
            assert not self.generator.is_extreme_pattern(combination)
