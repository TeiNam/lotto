"""SimplifiedPredictionService 단위 테스트"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from services.simplified_prediction_service import SimplifiedPredictionService
from services.random_generator import RandomGenerator
from services.duplicate_checker import DuplicateChecker
from services.data_service import AsyncDataService
from models.prediction import LottoPrediction
from utils.exceptions import ValidationError, PredictionGenerationError


def create_test_service(
    mock_duplicate_checker=None,
    mock_data_service=None,
    max_retries=100
):
    """테스트용 SimplifiedPredictionService 생성
    
    Args:
        mock_duplicate_checker: 모의 DuplicateChecker (None이면 기본 생성)
        mock_data_service: 모의 AsyncDataService (None이면 기본 생성)
        max_retries: 최대 재시도 횟수
        
    Returns:
        SimplifiedPredictionService 인스턴스
    """
    random_generator = RandomGenerator()
    
    if mock_duplicate_checker is None:
        mock_duplicate_checker = AsyncMock(spec=DuplicateChecker)
        mock_duplicate_checker.is_duplicate = AsyncMock(return_value=False)
    
    if mock_data_service is None:
        mock_data_service = AsyncMock(spec=AsyncDataService)
    
    service = SimplifiedPredictionService(
        random_generator=random_generator,
        duplicate_checker=mock_duplicate_checker,
        data_service=mock_data_service
    )
    service.max_retries = max_retries
    
    return service


class TestInputValidation:
    """입력 유효성 검증 테스트"""
    
    @pytest.mark.asyncio
    async def test_rejects_zero_predictions(self):
        """0개 예측 요청 거부"""
        service = create_test_service()
        
        with pytest.raises(ValidationError) as exc_info:
            await service.generate_predictions(num_predictions=0)
        
        assert "must be between 1 and 20" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_rejects_negative_predictions(self):
        """음수 예측 요청 거부"""
        service = create_test_service()
        
        with pytest.raises(ValidationError) as exc_info:
            await service.generate_predictions(num_predictions=-5)
        
        assert "must be between 1 and 20" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_rejects_too_many_predictions(self):
        """21개 이상 예측 요청 거부"""
        service = create_test_service()
        
        with pytest.raises(ValidationError) as exc_info:
            await service.generate_predictions(num_predictions=21)
        
        assert "must be between 1 and 20" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_rejects_non_integer_predictions(self):
        """정수가 아닌 예측 개수 거부"""
        service = create_test_service()
        
        with pytest.raises(ValidationError) as exc_info:
            await service.generate_predictions(num_predictions="5")
        
        assert "must be an integer" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_accepts_minimum_valid_predictions(self):
        """최소값 1개 예측 허용"""
        service = create_test_service()
        
        predictions = await service.generate_predictions(num_predictions=1)
        
        assert len(predictions) == 1
    
    @pytest.mark.asyncio
    async def test_accepts_maximum_valid_predictions(self):
        """최대값 20개 예측 허용"""
        service = create_test_service()
        
        predictions = await service.generate_predictions(num_predictions=20)
        
        assert len(predictions) == 20


class TestPredictionGeneration:
    """예측 생성 테스트"""
    
    @pytest.mark.asyncio
    async def test_generates_requested_count(self):
        """요청된 개수만큼 예측 생성"""
        service = create_test_service()
        
        for count in [1, 5, 10, 20]:
            predictions = await service.generate_predictions(num_predictions=count)
            assert len(predictions) == count
    
    @pytest.mark.asyncio
    async def test_returns_lotto_prediction_objects(self):
        """LottoPrediction 객체 반환"""
        service = create_test_service()
        
        predictions = await service.generate_predictions(num_predictions=3)
        
        assert all(isinstance(p, LottoPrediction) for p in predictions)
    
    @pytest.mark.asyncio
    async def test_each_prediction_has_six_numbers(self):
        """각 예측이 6개 숫자 포함"""
        service = create_test_service()
        
        predictions = await service.generate_predictions(num_predictions=5)
        
        for prediction in predictions:
            assert len(prediction.combination) == 6
    
    @pytest.mark.asyncio
    async def test_predictions_are_sorted(self):
        """예측 번호가 정렬됨"""
        service = create_test_service()
        
        predictions = await service.generate_predictions(num_predictions=5)
        
        for prediction in predictions:
            assert prediction.combination == sorted(prediction.combination)
    
    @pytest.mark.asyncio
    async def test_predictions_in_valid_range(self):
        """예측 번호가 1-45 범위 내"""
        service = create_test_service()
        
        predictions = await service.generate_predictions(num_predictions=10)
        
        for prediction in predictions:
            assert all(1 <= num <= 45 for num in prediction.combination)
    
    @pytest.mark.asyncio
    async def test_predictions_have_unique_numbers(self):
        """각 예측 내 번호가 고유함"""
        service = create_test_service()
        
        predictions = await service.generate_predictions(num_predictions=10)
        
        for prediction in predictions:
            assert len(set(prediction.combination)) == 6


class TestBatchUniqueness:
    """배치 고유성 테스트"""
    
    @pytest.mark.asyncio
    async def test_batch_predictions_are_unique(self):
        """배치 내 모든 예측이 서로 다름"""
        service = create_test_service()
        
        predictions = await service.generate_predictions(num_predictions=10)
        
        # 조합을 튜플로 변환하여 비교
        combinations = [tuple(p.combination) for p in predictions]
        
        # 모든 조합이 고유해야 함
        assert len(set(combinations)) == len(combinations)
    
    @pytest.mark.asyncio
    async def test_large_batch_uniqueness(self):
        """큰 배치(20개)에서도 고유성 보장"""
        service = create_test_service()
        
        predictions = await service.generate_predictions(num_predictions=20)
        
        combinations = [tuple(p.combination) for p in predictions]
        assert len(set(combinations)) == 20


class TestDuplicateHandling:
    """중복 처리 테스트"""
    
    @pytest.mark.asyncio
    async def test_skips_historical_duplicates(self):
        """과거 당첨 번호 중복 건너뜀"""
        # 첫 번째 호출은 중복, 두 번째부터는 중복 아님
        mock_checker = AsyncMock(spec=DuplicateChecker)
        mock_checker.is_duplicate = AsyncMock(side_effect=[True, False, False, False])
        
        service = create_test_service(mock_duplicate_checker=mock_checker)
        
        predictions = await service.generate_predictions(num_predictions=3)
        
        # 3개 예측 생성 성공
        assert len(predictions) == 3
        # is_duplicate가 4번 호출됨 (1번 중복 + 3번 성공)
        assert mock_checker.is_duplicate.call_count == 4
    
    @pytest.mark.asyncio
    async def test_raises_error_on_max_retries(self):
        """최대 재시도 초과 시 에러 발생"""
        # 모든 조합이 중복인 상황 시뮬레이션
        mock_checker = AsyncMock(spec=DuplicateChecker)
        mock_checker.is_duplicate = AsyncMock(return_value=True)
        
        service = create_test_service(
            mock_duplicate_checker=mock_checker,
            max_retries=10
        )
        
        with pytest.raises(PredictionGenerationError) as exc_info:
            await service.generate_predictions(num_predictions=1)
        
        assert "최대 재시도 횟수" in str(exc_info.value)
        # 정확히 max_retries만큼 시도했는지 확인
        assert mock_checker.is_duplicate.call_count == 10


class TestUserIdHandling:
    """사용자 ID 처리 테스트"""
    
    @pytest.mark.asyncio
    async def test_accepts_user_id(self):
        """user_id 파라미터 허용"""
        service = create_test_service()
        
        # user_id를 전달해도 정상 동작
        predictions = await service.generate_predictions(
            num_predictions=3,
            user_id=123
        )
        
        assert len(predictions) == 3
    
    @pytest.mark.asyncio
    async def test_accepts_none_user_id(self):
        """user_id=None 허용"""
        service = create_test_service()
        
        predictions = await service.generate_predictions(
            num_predictions=3,
            user_id=None
        )
        
        assert len(predictions) == 3


class TestPredictionModel:
    """예측 모델 테스트"""
    
    @pytest.mark.asyncio
    async def test_prediction_has_zero_score(self):
        """단순화된 버전에서는 score가 0"""
        service = create_test_service()
        
        predictions = await service.generate_predictions(num_predictions=3)
        
        for prediction in predictions:
            assert prediction.score == 0.0
    
    @pytest.mark.asyncio
    async def test_prediction_has_zero_common_with_last(self):
        """단순화된 버전에서는 common_with_last가 0"""
        service = create_test_service()
        
        predictions = await service.generate_predictions(num_predictions=3)
        
        for prediction in predictions:
            assert prediction.common_with_last == 0
