"""중복 조합 검증 서비스"""
import logging
from typing import List, Set, Tuple, Optional
from datetime import datetime, timedelta
from services.data_service import AsyncDataService

logger = logging.getLogger("lotto_prediction")


class DuplicateChecker:
    """중복 조합 검증기
    
    과거 당첨 번호와 중복되는 조합을 감지하고 필터링합니다.
    성능 최적화를 위해 1시간 TTL 캐싱을 사용합니다.
    """
    
    def __init__(self, data_service: AsyncDataService):
        """
        Args:
            data_service: 데이터베이스 접근을 위한 데이터 서비스
        """
        self.data_service = data_service
        self._winning_cache: Optional[Set[Tuple[int, ...]]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = timedelta(hours=1)
    
    async def _get_winning_combinations(self) -> Set[Tuple[int, ...]]:
        """캐시된 당첨 번호 반환 (1시간 TTL)
        
        캐시가 없거나 만료된 경우 데이터베이스에서 새로 로드합니다.
        
        Returns:
            정렬된 튜플 형태의 당첨 번호 집합
        """
        now = datetime.now()
        
        # 캐시가 없거나 만료된 경우 새로 로드
        if (self._winning_cache is None or 
            self._cache_timestamp is None or
            now - self._cache_timestamp > self._cache_ttl):
            
            logger.debug("당첨 번호 캐시 갱신 중...")
            
            # 데이터 서비스에서 기존 조합 가져오기
            combinations = self.data_service.get_existing_combinations()
            
            # 이미 정렬된 튜플 형태로 저장되어 있음
            self._winning_cache = combinations
            self._cache_timestamp = now
            
            logger.info(f"당첨 번호 캐시 갱신 완료: {len(self._winning_cache)}개 조합")
        
        return self._winning_cache
    
    async def is_duplicate(self, combination: List[int]) -> bool:
        """조합이 과거 당첨 번호와 중복되는지 확인
        
        순서에 관계없이 동일한 숫자 조합이면 중복으로 판단합니다.
        
        Args:
            combination: 검증할 6개 숫자 조합
            
        Returns:
            중복이면 True, 아니면 False
        """
        try:
            # 입력 유효성 검증
            if not combination or len(combination) != 6:
                logger.warning(f"유효하지 않은 조합 길이: {len(combination) if combination else 0}")
                return True  # 유효하지 않은 조합은 중복으로 간주
            
            # 정렬된 튜플로 변환하여 비교
            combo_tuple = tuple(sorted(combination))
            
            # 캐시된 당첨 번호와 비교
            winning_combinations = await self._get_winning_combinations()
            is_dup = combo_tuple in winning_combinations
            
            if is_dup:
                logger.debug(f"중복 조합 감지: {combination}")
            
            return is_dup
            
        except Exception as e:
            logger.error(f"중복 확인 중 오류: {e}")
            # 오류 발생 시 안전하게 중복으로 간주
            return True
    
    async def is_new_combination(self, combination: List[int]) -> bool:
        """조합이 새로운(중복되지 않은) 조합인지 확인
        
        is_duplicate()의 반대 결과를 반환하는 편의 메서드입니다.
        
        Args:
            combination: 검증할 6개 숫자 조합
            
        Returns:
            새로운 조합이면 True, 중복이면 False
        """
        return not await self.is_duplicate(combination)
    
    def clear_cache(self) -> None:
        """캐시를 강제로 초기화
        
        테스트나 데이터 갱신 후 즉시 반영이 필요한 경우 사용합니다.
        """
        self._winning_cache = None
        self._cache_timestamp = None
        logger.info("당첨 번호 캐시 초기화됨")
