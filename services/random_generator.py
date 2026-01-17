"""완전 랜덤 로또 번호 생성기

이 모듈은 암호학적으로 안전한 난수 생성을 사용하여
1-45 범위에서 6개의 고유한 숫자를 선택합니다.
극단적 패턴은 자동으로 필터링됩니다.
"""

import secrets
from typing import List


class RandomGenerator:
    """완전 랜덤 로또 번호 생성기
    
    암호학적으로 안전한 난수 생성을 사용하여 로또 번호를 생성하고,
    극단적 패턴을 필터링합니다.
    """
    
    def __init__(self):
        """RandomGenerator 초기화"""
        self.random = secrets.SystemRandom()
    
    def generate_combination(self) -> List[int]:
        """1-45 범위에서 6개의 고유한 숫자를 랜덤으로 선택
        
        극단적 패턴은 자동으로 필터링되며, 정상적인 조합이 생성될 때까지
        재시도합니다.
        
        Returns:
            정렬된 6개 숫자 리스트 [n1, n2, n3, n4, n5, n6] (n1 < n2 < ... < n6)
            
        Note:
            극단적 패턴이 감지되면 자동으로 재생성됩니다.
            무한 루프를 방지하기 위해 최대 재시도 횟수는 호출자가 관리해야 합니다.
        """
        while True:
            # 1-45 범위에서 6개 고유 숫자 선택
            combination = self.random.sample(range(1, 46), 6)
            
            # 정렬
            combination.sort()
            
            # 극단적 패턴 체크
            if not self.is_extreme_pattern(combination):
                return combination
    
    def is_extreme_pattern(self, combination: List[int]) -> bool:
        """극단적 패턴 감지
        
        다음 패턴들을 극단적으로 간주합니다:
        1. 연속 숫자 5개 이상 (예: [1,2,3,4,5,10])
        2. 등차수열 - 모든 간격이 동일하고 1보다 큼 (예: [5,10,15,20,25,30])
        3. 극단적 합계 - 80 미만 또는 200 초과
        4. 홀수만 또는 짝수만
        5. 한 구간(10개 단위)에 5개 이상 몰림
        
        Args:
            combination: 검증할 6개 숫자 조합 (정렬된 상태)
            
        Returns:
            극단적 패턴이면 True, 정상이면 False
        """
        sorted_combo = sorted(combination)
        
        # 1. 연속 숫자 5개 이상 체크
        consecutive_count = 0
        max_consecutive = 0
        for i in range(5):
            if sorted_combo[i + 1] - sorted_combo[i] == 1:
                consecutive_count += 1
                max_consecutive = max(max_consecutive, consecutive_count + 1)
            else:
                consecutive_count = 0
        
        if max_consecutive >= 5:
            return True
        
        # 2. 등차수열 체크 (모든 간격이 동일하고 1보다 큼)
        gaps = [sorted_combo[i + 1] - sorted_combo[i] for i in range(5)]
        if len(set(gaps)) == 1 and gaps[0] > 1:
            return True
        
        # 3. 극단적 합계 체크
        total_sum = sum(combination)
        if total_sum < 80 or total_sum > 200:
            return True
        
        # 4. 홀수만 또는 짝수만 체크
        odd_count = sum(1 for n in combination if n % 2 == 1)
        if odd_count == 0 or odd_count == 6:
            return True
        
        # 5. 구간 편중 체크 (한 구간에 5개 이상)
        ranges = {
            "1-10": sum(1 for n in combination if 1 <= n <= 10),
            "11-20": sum(1 for n in combination if 11 <= n <= 20),
            "21-30": sum(1 for n in combination if 21 <= n <= 30),
            "31-40": sum(1 for n in combination if 31 <= n <= 40),
            "41-45": sum(1 for n in combination if 41 <= n <= 45),
        }
        if max(ranges.values()) >= 5:
            return True
        
        return False
