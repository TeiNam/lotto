"""DuplicateChecker 단위 테스트"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
from services.duplicate_checker import DuplicateChecker
from services.data_service import AsyncDataService


@pytest.fixture
def mock_data_service():
    """Mock 데이터 서비스 픽스처"""
    service = MagicMock(spec=AsyncDataService)
    return service


@pytest.fixture
def duplicate_checker(mock_data_service):
    """DuplicateChecker 인스턴스 픽스처"""
    return DuplicateChecker(mock_data_service)


@pytest.mark.asyncio
async def test_is_duplicate_returns_true_for_matching_combination(mock_data_service, duplicate_checker):
    """중복 조합 감지 테스트"""
    # Given: 과거 당첨 번호 설정
    mock_data_service.get_existing_combinations.return_value = {
        (1, 2, 3, 4, 5, 6),
        (7, 8, 9, 10, 11, 12)
    }
    
    # When: 중복 조합 확인
    result = await duplicate_checker.is_duplicate([1, 2, 3, 4, 5, 6])
    
    # Then: 중복으로 판단되어야 함
    assert result is True


@pytest.mark.asyncio
async def test_is_duplicate_returns_false_for_new_combination(mock_data_service, duplicate_checker):
    """새로운 조합 감지 테스트"""
    # Given: 과거 당첨 번호 설정
    mock_data_service.get_existing_combinations.return_value = {
        (1, 2, 3, 4, 5, 6)
    }
    
    # When: 새로운 조합 확인
    result = await duplicate_checker.is_duplicate([7, 8, 9, 10, 11, 12])
    
    # Then: 중복이 아니어야 함
    assert result is False


@pytest.mark.asyncio
async def test_is_duplicate_ignores_order(mock_data_service, duplicate_checker):
    """순서 무관 중복 검증 테스트"""
    # Given: 과거 당첨 번호 설정
    mock_data_service.get_existing_combinations.return_value = {
        (1, 2, 3, 4, 5, 6)
    }
    
    # When: 역순으로 조합 확인
    result = await duplicate_checker.is_duplicate([6, 5, 4, 3, 2, 1])
    
    # Then: 순서와 관계없이 중복으로 판단되어야 함
    assert result is True


@pytest.mark.asyncio
async def test_is_duplicate_with_different_order(mock_data_service, duplicate_checker):
    """다양한 순서의 중복 검증 테스트"""
    # Given: 과거 당첨 번호 설정
    mock_data_service.get_existing_combinations.return_value = {
        (1, 2, 3, 4, 5, 6)
    }
    
    # When: 무작위 순서로 조합 확인
    result = await duplicate_checker.is_duplicate([3, 1, 5, 2, 6, 4])
    
    # Then: 순서와 관계없이 중복으로 판단되어야 함
    assert result is True


@pytest.mark.asyncio
async def test_is_new_combination_returns_true_for_new(mock_data_service, duplicate_checker):
    """is_new_combination: 새로운 조합 테스트"""
    # Given: 과거 당첨 번호 설정
    mock_data_service.get_existing_combinations.return_value = {
        (1, 2, 3, 4, 5, 6)
    }
    
    # When: 새로운 조합 확인
    result = await duplicate_checker.is_new_combination([7, 8, 9, 10, 11, 12])
    
    # Then: 새로운 조합으로 판단되어야 함
    assert result is True


@pytest.mark.asyncio
async def test_is_new_combination_returns_false_for_duplicate(mock_data_service, duplicate_checker):
    """is_new_combination: 중복 조합 테스트"""
    # Given: 과거 당첨 번호 설정
    mock_data_service.get_existing_combinations.return_value = {
        (1, 2, 3, 4, 5, 6)
    }
    
    # When: 중복 조합 확인
    result = await duplicate_checker.is_new_combination([1, 2, 3, 4, 5, 6])
    
    # Then: 새로운 조합이 아니어야 함
    assert result is False


@pytest.mark.asyncio
async def test_caching_behavior(mock_data_service, duplicate_checker):
    """캐싱 동작 테스트"""
    # Given: 과거 당첨 번호 설정
    mock_data_service.get_existing_combinations.return_value = {
        (1, 2, 3, 4, 5, 6)
    }
    
    # When: 여러 번 중복 확인
    await duplicate_checker.is_duplicate([1, 2, 3, 4, 5, 6])
    await duplicate_checker.is_duplicate([7, 8, 9, 10, 11, 12])
    await duplicate_checker.is_duplicate([1, 2, 3, 4, 5, 6])
    
    # Then: 데이터 서비스는 한 번만 호출되어야 함 (캐싱)
    assert mock_data_service.get_existing_combinations.call_count == 1


@pytest.mark.asyncio
async def test_cache_expiration(mock_data_service, duplicate_checker):
    """캐시 만료 테스트"""
    # Given: 과거 당첨 번호 설정
    mock_data_service.get_existing_combinations.return_value = {
        (1, 2, 3, 4, 5, 6)
    }
    
    # When: 첫 번째 호출
    await duplicate_checker.is_duplicate([1, 2, 3, 4, 5, 6])
    
    # 캐시 타임스탬프를 1시간 이상 전으로 설정
    duplicate_checker._cache_timestamp = datetime.now() - timedelta(hours=2)
    
    # 두 번째 호출
    await duplicate_checker.is_duplicate([7, 8, 9, 10, 11, 12])
    
    # Then: 캐시가 만료되어 데이터 서비스가 두 번 호출되어야 함
    assert mock_data_service.get_existing_combinations.call_count == 2


@pytest.mark.asyncio
async def test_clear_cache(mock_data_service, duplicate_checker):
    """캐시 초기화 테스트"""
    # Given: 과거 당첨 번호 설정 및 캐시 생성
    mock_data_service.get_existing_combinations.return_value = {
        (1, 2, 3, 4, 5, 6)
    }
    await duplicate_checker.is_duplicate([1, 2, 3, 4, 5, 6])
    
    # When: 캐시 초기화
    duplicate_checker.clear_cache()
    
    # Then: 캐시가 초기화되어야 함
    assert duplicate_checker._winning_cache is None
    assert duplicate_checker._cache_timestamp is None
    
    # 다음 호출 시 데이터 서비스가 다시 호출되어야 함
    await duplicate_checker.is_duplicate([7, 8, 9, 10, 11, 12])
    assert mock_data_service.get_existing_combinations.call_count == 2


@pytest.mark.asyncio
async def test_invalid_combination_length(mock_data_service, duplicate_checker):
    """유효하지 않은 조합 길이 테스트"""
    # Given: 과거 당첨 번호 설정
    mock_data_service.get_existing_combinations.return_value = {
        (1, 2, 3, 4, 5, 6)
    }
    
    # When: 잘못된 길이의 조합 확인
    result_short = await duplicate_checker.is_duplicate([1, 2, 3])
    result_long = await duplicate_checker.is_duplicate([1, 2, 3, 4, 5, 6, 7])
    result_empty = await duplicate_checker.is_duplicate([])
    
    # Then: 모두 중복(유효하지 않음)으로 판단되어야 함
    assert result_short is True
    assert result_long is True
    assert result_empty is True


@pytest.mark.asyncio
async def test_multiple_winning_combinations(mock_data_service, duplicate_checker):
    """여러 당첨 번호와 비교 테스트"""
    # Given: 여러 과거 당첨 번호 설정
    mock_data_service.get_existing_combinations.return_value = {
        (1, 2, 3, 4, 5, 6),
        (7, 8, 9, 10, 11, 12),
        (13, 14, 15, 16, 17, 18),
        (19, 20, 21, 22, 23, 24),
        (25, 26, 27, 28, 29, 30)
    }
    
    # When & Then: 각 조합 확인
    assert await duplicate_checker.is_duplicate([1, 2, 3, 4, 5, 6]) is True
    assert await duplicate_checker.is_duplicate([7, 8, 9, 10, 11, 12]) is True
    assert await duplicate_checker.is_duplicate([25, 26, 27, 28, 29, 30]) is True
    assert await duplicate_checker.is_duplicate([31, 32, 33, 34, 35, 36]) is False


@pytest.mark.asyncio
async def test_error_handling(mock_data_service, duplicate_checker):
    """에러 처리 테스트"""
    # Given: 데이터 서비스에서 예외 발생
    mock_data_service.get_existing_combinations.side_effect = Exception("Database error")
    
    # When: 중복 확인 시도
    result = await duplicate_checker.is_duplicate([1, 2, 3, 4, 5, 6])
    
    # Then: 안전하게 중복으로 판단되어야 함
    assert result is True
