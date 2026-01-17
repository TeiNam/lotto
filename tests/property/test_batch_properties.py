"""SimplifiedPredictionService 속성 기반 테스트

이 모듈은 배치 예측 생성의 보편적 속성을 검증합니다.
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import AsyncMock

from services.simplified_prediction_service import SimplifiedPredictionService
from services.random_generator import RandomGenerator
from services.duplicate_checker import DuplicateChecker
from services.data_service import AsyncDataService
from utils.exceptions import ValidationError


def create_test_service_for_property_tests():
    """속성 기반 테스트용 서비스 생성
    
    Returns:
        SimplifiedPredictionService 인스턴스
    """
    random_generator = RandomGenerator()
    
    # 중복 체크를 항상 False로 설정 (새로운 조합)
    mock_duplicate_checker = AsyncMock(spec=DuplicateChecker)
    mock_duplicate_checker.is_duplicate = AsyncMock(return_value=False)
    
    mock_data_service = AsyncMock(spec=AsyncDataService)
    
    service = SimplifiedPredictionService(
        random_generator=random_generator,
        duplicate_checker=mock_duplicate_checker,
        data_service=mock_data_service
    )
    
    return service


# Property 8: Batch Uniqueness
@given(st.integers(min_value=1, max_value=20))
@settings(max_examples=100, deadline=None)
@pytest.mark.asyncio
async def test_property_batch_uniqueness(num_predictions):
    """
    Feature: lotto-algorithm-simplification, Property 8: Batch Uniqueness
    
    For any N predictions (1 ≤ N ≤ 20), all N combinations should be unique from each other.
    
    **Validates: Requirements 6.1**
    """
    service = create_test_service_for_property_tests()
    
    # 예측 생성
    predictions = await service.generate_predictions(num_predictions)
    
    # 정확히 N개 생성되었는지 확인
    assert len(predictions) == num_predictions, \
        f"Expected {num_predictions} predictions, got {len(predictions)}"
    
    # 조합을 튜플로 변환하여 비교
    combinations = [tuple(p.combination) for p in predictions]
    
    # 모든 조합이 고유해야 함
    unique_combinations = set(combinations)
    assert len(unique_combinations) == len(combinations), \
        f"Found duplicate combinations in batch: {len(combinations)} total, {len(unique_combinations)} unique"


# Property 9: Input Validation
@given(st.integers())
@settings(max_examples=100, deadline=None)
@pytest.mark.asyncio
async def test_property_input_validation(num_predictions):
    """
    Feature: lotto-algorithm-simplification, Property 9: Input Validation
    
    For any request with num_predictions outside the range [1, 20], 
    the system should reject the request with a validation error.
    
    **Validates: Requirements 6.2**
    """
    service = create_test_service_for_property_tests()
    
    if 1 <= num_predictions <= 20:
        # 유효한 범위: 성공해야 함
        predictions = await service.generate_predictions(num_predictions)
        assert len(predictions) == num_predictions
    else:
        # 유효하지 않은 범위: ValidationError 발생해야 함
        with pytest.raises(ValidationError) as exc_info:
            await service.generate_predictions(num_predictions)
        
        # 에러 메시지에 범위 정보 포함 확인
        assert "must be between 1 and 20" in str(exc_info.value)


# Property 10: Historical Duplicate Prevention
@given(st.integers(min_value=1, max_value=20))
@settings(max_examples=100, deadline=None)
@pytest.mark.asyncio
async def test_property_historical_duplicate_prevention(num_predictions):
    """
    Feature: lotto-algorithm-simplification, Property 10: Historical Duplicate Prevention
    
    For any batch of N generated predictions, none of the combinations should match 
    any historical winning combination in the database.
    
    **Validates: Requirements 6.5**
    """
    # 실제 데이터베이스 연결을 사용하는 서비스 생성
    random_generator = RandomGenerator()
    
    # 실제 데이터 서비스 사용
    data_service = AsyncDataService()
    
    # 데이터 로드 시도
    try:
        await data_service.load_historical_data(start_no=601, end_no=650)
    except Exception:
        # 데이터베이스 연결 실패 시 테스트 스킵
        pytest.skip("데이터베이스 연결 실패 - 통합 테스트 환경 필요")
    
    # 실제 DuplicateChecker 사용
    duplicate_checker = DuplicateChecker(data_service)
    
    service = SimplifiedPredictionService(
        random_generator=random_generator,
        duplicate_checker=duplicate_checker,
        data_service=data_service
    )
    
    # 예측 생성
    predictions = await service.generate_predictions(num_predictions)
    
    # 과거 당첨 번호 집합 가져오기
    winning_combinations = data_service.get_existing_combinations()
    
    # 모든 예측이 과거 당첨 번호와 다른지 확인
    for prediction in predictions:
        combo_tuple = tuple(prediction.combination)
        assert combo_tuple not in winning_combinations, \
            f"Generated combination {prediction.combination} matches historical winning combination"


# 추가 속성: 각 예측의 기본 유효성
@given(st.integers(min_value=1, max_value=20))
@settings(max_examples=100, deadline=None)
@pytest.mark.asyncio
async def test_property_valid_predictions_in_batch(num_predictions):
    """
    Feature: lotto-algorithm-simplification, Additional Property: Valid Predictions in Batch
    
    For any N predictions, each prediction should be valid:
    - Exactly 6 numbers
    - All numbers unique
    - All numbers in range [1, 45]
    - Numbers sorted in ascending order
    
    **Validates: Requirements 1.1, 1.4, 6.1**
    """
    service = create_test_service_for_property_tests()
    
    predictions = await service.generate_predictions(num_predictions)
    
    for i, prediction in enumerate(predictions):
        combination = prediction.combination
        
        # 정확히 6개
        assert len(combination) == 6, \
            f"Prediction {i+1} has {len(combination)} numbers, expected 6"
        
        # 모두 고유
        assert len(set(combination)) == 6, \
            f"Prediction {i+1} has duplicate numbers: {combination}"
        
        # 범위 내 (1-45)
        assert all(1 <= num <= 45 for num in combination), \
            f"Prediction {i+1} has numbers outside range [1, 45]: {combination}"
        
        # 정렬됨
        assert combination == sorted(combination), \
            f"Prediction {i+1} is not sorted: {combination}"


# 추가 속성: 배치 생성 일관성
@given(st.integers(min_value=1, max_value=20))
@settings(max_examples=50, deadline=None)
@pytest.mark.asyncio
async def test_property_batch_generation_consistency(num_predictions):
    """
    Feature: lotto-algorithm-simplification, Additional Property: Batch Generation Consistency
    
    For any N, generating predictions multiple times should always produce N predictions,
    even though the actual combinations will differ.
    
    **Validates: Requirements 6.1**
    """
    service = create_test_service_for_property_tests()
    
    # 여러 번 생성
    for _ in range(3):
        predictions = await service.generate_predictions(num_predictions)
        
        # 항상 정확히 N개 생성
        assert len(predictions) == num_predictions, \
            f"Expected {num_predictions} predictions, got {len(predictions)}"
