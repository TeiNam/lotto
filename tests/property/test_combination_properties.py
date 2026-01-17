"""RandomGenerator 속성 기반 테스트

Property-Based Testing을 사용하여 RandomGenerator의 보편적 속성을 검증합니다.
각 property는 최소 100회 반복 실행됩니다.

Feature: lotto-algorithm-simplification
"""

import pytest
from hypothesis import given, settings, strategies as st
from services.random_generator import RandomGenerator


class TestCombinationProperties:
    """조합 생성 속성 테스트"""
    
    def setup_method(self):
        """각 테스트 전에 실행"""
        self.generator = RandomGenerator()
    
    @settings(max_examples=100)
    @given(st.integers(min_value=1, max_value=100))
    def test_property_1_valid_combination_generation(self, iterations):
        """
        Feature: lotto-algorithm-simplification, Property 1: Valid Combination Generation
        
        **Validates: Requirements 1.1**
        
        For any generated combination, all 6 numbers should be unique, 
        within the range 1-45, and the combination should contain exactly 6 numbers.
        
        이 속성은 생성된 모든 조합이 기본 요구사항을 만족하는지 검증합니다:
        - 정확히 6개의 숫자
        - 모든 숫자가 1-45 범위 내
        - 모든 숫자가 고유함 (중복 없음)
        """
        combination = self.generator.generate_combination()
        
        # 정확히 6개
        assert len(combination) == 6, \
            f"조합은 정확히 6개의 숫자를 포함해야 합니다. 실제: {len(combination)}"
        
        # 모두 고유
        assert len(set(combination)) == 6, \
            f"모든 숫자는 고유해야 합니다. 중복 발견: {combination}"
        
        # 범위 내
        assert all(1 <= num <= 45 for num in combination), \
            f"모든 숫자는 1-45 범위 내에 있어야 합니다. 실제: {combination}"
    
    @settings(max_examples=100)
    @given(st.integers(min_value=1, max_value=100))
    def test_property_2_sorted_combination_output(self, iterations):
        """
        Feature: lotto-algorithm-simplification, Property 2: Sorted Combination Output
        
        **Validates: Requirements 1.4**
        
        For any generated combination, the numbers should be in ascending order 
        (n1 < n2 < n3 < n4 < n5 < n6).
        
        이 속성은 생성된 모든 조합이 오름차순으로 정렬되어 있는지 검증합니다.
        """
        combination = self.generator.generate_combination()
        
        # 오름차순 정렬 확인
        assert combination == sorted(combination), \
            f"조합은 오름차순으로 정렬되어야 합니다. 실제: {combination}, 정렬: {sorted(combination)}"
        
        # 엄격한 오름차순 (중복 없음) 확인
        for i in range(5):
            assert combination[i] < combination[i + 1], \
                f"각 숫자는 다음 숫자보다 작아야 합니다. 위치 {i}: {combination[i]} >= {combination[i + 1]}"
    
    @settings(max_examples=100)
    @given(st.integers(min_value=1, max_value=100))
    def test_property_12_extreme_pattern_filtering(self, iterations):
        """
        Feature: lotto-algorithm-simplification, Property 12: Extreme Pattern Filtering
        
        **Validates: Requirements 12.1, 12.2, 12.3, 12.4, 12.5**
        
        For any generated combination, the system should reject extreme patterns including:
        - 5+ consecutive numbers
        - Arithmetic sequences (all gaps equal and > 1)
        - Extreme sums (< 80 or > 200)
        - All odd/even numbers
        - 5+ numbers in a single 10-number range
        
        이 속성은 생성된 모든 조합이 극단적 패턴을 포함하지 않는지 검증합니다.
        """
        combination = self.generator.generate_combination()
        
        # 극단적 패턴이 아니어야 함
        assert not self.generator.is_extreme_pattern(combination), \
            f"생성된 조합 {combination}은 극단적 패턴이 아니어야 합니다"
        
        # 개별 극단적 패턴 체크
        sorted_combo = sorted(combination)
        
        # 1. 연속 숫자 5개 이상 없음
        consecutive_count = 0
        max_consecutive = 0
        for i in range(5):
            if sorted_combo[i + 1] - sorted_combo[i] == 1:
                consecutive_count += 1
                max_consecutive = max(max_consecutive, consecutive_count + 1)
            else:
                consecutive_count = 0
        assert max_consecutive < 5, \
            f"5개 이상 연속 숫자가 있으면 안 됩니다. 조합: {combination}"
        
        # 2. 등차수열 아님 (간격이 모두 동일하고 1보다 큼)
        gaps = [sorted_combo[i + 1] - sorted_combo[i] for i in range(5)]
        is_arithmetic = len(set(gaps)) == 1 and gaps[0] > 1
        assert not is_arithmetic, \
            f"등차수열이면 안 됩니다. 조합: {combination}, 간격: {gaps}"
        
        # 3. 합계가 80-200 범위 내
        total_sum = sum(combination)
        assert 80 <= total_sum <= 200, \
            f"합계는 80-200 범위 내여야 합니다. 실제: {total_sum}, 조합: {combination}"
        
        # 4. 홀수/짝수 혼합
        odd_count = sum(1 for n in combination if n % 2 == 1)
        assert 0 < odd_count < 6, \
            f"홀수와 짝수가 혼합되어야 합니다. 홀수 개수: {odd_count}, 조합: {combination}"
        
        # 5. 구간 분포 (한 구간에 5개 이상 몰리지 않음)
        ranges = {
            "1-10": sum(1 for n in combination if 1 <= n <= 10),
            "11-20": sum(1 for n in combination if 11 <= n <= 20),
            "21-30": sum(1 for n in combination if 21 <= n <= 30),
            "31-40": sum(1 for n in combination if 31 <= n <= 40),
            "41-45": sum(1 for n in combination if 41 <= n <= 45),
        }
        max_in_range = max(ranges.values())
        assert max_in_range < 5, \
            f"한 구간에 5개 이상 몰리면 안 됩니다. 구간 분포: {ranges}, 조합: {combination}"


class TestCombinationDiversity:
    """조합 다양성 속성 테스트"""
    
    def setup_method(self):
        """각 테스트 전에 실행"""
        self.generator = RandomGenerator()
    
    @settings(max_examples=50)
    @given(st.integers(min_value=10, max_value=50))
    def test_property_combination_diversity(self, num_generations):
        """
        조합 다양성 속성
        
        여러 조합을 생성할 때 충분히 다양한 조합이 생성되는지 검증합니다.
        동일한 조합이 반복적으로 생성되지 않아야 합니다.
        """
        combinations = set()
        
        for _ in range(num_generations):
            combination = tuple(self.generator.generate_combination())
            combinations.add(combination)
        
        # 생성된 조합의 최소 80%는 고유해야 함
        uniqueness_ratio = len(combinations) / num_generations
        assert uniqueness_ratio >= 0.8, \
            f"조합의 다양성이 부족합니다. 고유 비율: {uniqueness_ratio:.2%}"


class TestExtremePatternDetection:
    """극단적 패턴 감지 속성 테스트"""
    
    def setup_method(self):
        """각 테스트 전에 실행"""
        self.generator = RandomGenerator()
    
    @settings(max_examples=100)
    @given(
        st.lists(
            st.integers(min_value=1, max_value=45),
            min_size=6,
            max_size=6,
            unique=True
        )
    )
    def test_property_extreme_pattern_consistency(self, numbers):
        """
        극단적 패턴 감지 일관성 속성
        
        is_extreme_pattern 메서드가 일관되게 동작하는지 검증합니다.
        동일한 조합에 대해 항상 동일한 결과를 반환해야 합니다.
        """
        sorted_numbers = sorted(numbers)
        
        # 첫 번째 호출
        result1 = self.generator.is_extreme_pattern(sorted_numbers)
        
        # 두 번째 호출 (동일한 결과여야 함)
        result2 = self.generator.is_extreme_pattern(sorted_numbers)
        
        assert result1 == result2, \
            f"동일한 조합에 대해 일관된 결과를 반환해야 합니다. 조합: {sorted_numbers}"
    
    @settings(max_examples=100)
    @given(
        st.lists(
            st.integers(min_value=1, max_value=45),
            min_size=6,
            max_size=6,
            unique=True
        )
    )
    def test_property_order_independence(self, numbers):
        """
        순서 독립성 속성
        
        극단적 패턴 감지가 숫자의 순서에 독립적인지 검증합니다.
        동일한 숫자들이 다른 순서로 제공되어도 동일한 결과를 반환해야 합니다.
        """
        # 원본 순서
        result1 = self.generator.is_extreme_pattern(numbers)
        
        # 정렬된 순서
        sorted_numbers = sorted(numbers)
        result2 = self.generator.is_extreme_pattern(sorted_numbers)
        
        # 역순
        reversed_numbers = sorted(numbers, reverse=True)
        result3 = self.generator.is_extreme_pattern(reversed_numbers)
        
        assert result1 == result2 == result3, \
            f"순서에 관계없이 동일한 결과를 반환해야 합니다. 숫자: {numbers}"
