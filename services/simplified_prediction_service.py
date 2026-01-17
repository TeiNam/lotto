"""단순화된 예측 서비스

이 모듈은 완전 랜덤 방식으로 로또 번호를 생성하는 단순화된 예측 서비스를 제공합니다.
복잡한 통계 분석 없이 RandomGenerator와 DuplicateChecker를 사용하여
중복되지 않은 유효한 조합을 생성합니다.
"""

import logging
from typing import List, Optional
from datetime import datetime

from services.random_generator import RandomGenerator
from services.duplicate_checker import DuplicateChecker
from services.data_service import AsyncDataService
from models.prediction import LottoPrediction
from utils.exceptions import ValidationError, PredictionGenerationError

logger = logging.getLogger("lotto_prediction")


class SimplifiedPredictionService:
    """단순화된 예측 서비스
    
    완전 랜덤 방식으로 로또 번호를 생성하며, 과거 당첨 번호와의 중복을 방지합니다.
    배치 생성 시 생성된 조합들 간의 고유성도 보장합니다.
    """
    
    def __init__(
        self,
        random_generator: RandomGenerator,
        duplicate_checker: DuplicateChecker,
        data_service: AsyncDataService
    ):
        """
        Args:
            random_generator: 랜덤 번호 생성기
            duplicate_checker: 중복 검증기
            data_service: 데이터 서비스
        """
        self.random_generator = random_generator
        self.duplicate_checker = duplicate_checker
        self.data_service = data_service
        self.max_retries = 100  # 무한 루프 방지
    
    async def generate_predictions(
        self,
        num_predictions: int,
        user_id: Optional[int] = None
    ) -> List[LottoPrediction]:
        """요청된 개수만큼 예측 생성
        
        Args:
            num_predictions: 생성할 예측 개수 (1-20)
            user_id: 사용자 ID (선택)
            
        Returns:
            생성된 예측 리스트
            
        Raises:
            ValidationError: num_predictions가 유효하지 않은 경우
            PredictionGenerationError: 예측 생성 실패 시
        """
        # 입력 유효성 검증
        if not isinstance(num_predictions, int):
            raise ValidationError(
                f"num_predictions must be an integer, got {type(num_predictions).__name__}"
            )
        
        if not 1 <= num_predictions <= 20:
            raise ValidationError(
                f"num_predictions must be between 1 and 20, got {num_predictions}"
            )
        
        logger.info(
            f"예측 생성 요청: num_predictions={num_predictions}, user_id={user_id}"
        )
        
        start_time = datetime.now()
        predictions = []
        generated_combinations = set()  # 배치 내 중복 방지
        
        try:
            for i in range(num_predictions):
                # 단일 예측 생성 (중복 방지)
                combination = await self._generate_single_prediction(generated_combinations)
                
                # 생성된 조합 추가
                generated_combinations.add(tuple(combination))
                
                # LottoPrediction 객체 생성
                # 단순화된 버전에서는 score와 common_with_last는 의미 없음
                prediction = LottoPrediction(
                    combination=combination,
                    score=0.0,  # 더 이상 점수 계산 안 함
                    common_with_last=0  # 더 이상 비교 안 함
                )
                predictions.append(prediction)
                
                logger.debug(f"예측 {i+1}/{num_predictions} 생성 완료: {combination}")
            
            elapsed_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(
                f"예측 생성 완료: {len(predictions)}개 생성, "
                f"소요 시간: {elapsed_time:.2f}ms"
            )
            
            return predictions
            
        except PredictionGenerationError:
            # 예측 생성 실패는 그대로 전파
            raise
        except Exception as e:
            logger.exception(f"예측 생성 중 예상치 못한 오류: {e}")
            raise PredictionGenerationError(
                f"예측 생성 중 오류 발생: {str(e)}",
                original_error=e
            )
    
    async def _generate_single_prediction(
        self,
        generated_combinations: set
    ) -> List[int]:
        """중복되지 않은 단일 예측 생성
        
        과거 당첨 번호 및 이미 생성된 조합과 중복되지 않는 조합을 생성합니다.
        
        Args:
            generated_combinations: 이미 생성된 조합들의 집합 (튜플 형태)
            
        Returns:
            유효한 6개 숫자 조합
            
        Raises:
            PredictionGenerationError: 최대 재시도 횟수 초과 시
        """
        retry_count = 0
        
        while retry_count < self.max_retries:
            # 랜덤 조합 생성 (극단적 패턴 자동 필터링)
            combination = self.random_generator.generate_combination()
            
            # 과거 당첨 번호와 중복 확인
            is_historical_duplicate = await self.duplicate_checker.is_duplicate(combination)
            
            if is_historical_duplicate:
                retry_count += 1
                logger.debug(
                    f"과거 당첨 번호와 중복: {combination}, "
                    f"재시도 {retry_count}/{self.max_retries}"
                )
                continue
            
            # 배치 내 중복 확인
            combo_tuple = tuple(combination)
            if combo_tuple in generated_combinations:
                retry_count += 1
                logger.debug(
                    f"배치 내 중복: {combination}, "
                    f"재시도 {retry_count}/{self.max_retries}"
                )
                continue
            
            # 유효한 조합 발견
            logger.debug(f"유효한 조합 생성: {combination}")
            return combination
        
        # 최대 재시도 횟수 초과
        error_msg = (
            f"최대 재시도 횟수({self.max_retries})를 초과했습니다. "
            f"유효한 조합을 생성할 수 없습니다."
        )
        logger.error(error_msg)
        raise PredictionGenerationError(error_msg)
