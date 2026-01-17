"""DuplicateChecker 속성 기반 테스트"""
import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import MagicMock
from services.duplicate_checker import DuplicateChecker
from services.data_service import AsyncDataService


# 유효한 로또 번호 조합 생성 전략
valid_combination = st.lists(
    st.integers(min_value=1, max_value=45),
    min_size=6,
    max_size=6,
    unique=True
)


def create_mock_data_service(winning_combinations):
    """Mock 데이터 서비스 생성 헬퍼"""
    service = MagicMock(spec=AsyncDataService)
    # 조합을 정렬된 튜플 집합으로 변환
    service.get_existing_combinations.return_value = {
        tuple(sorted(combo)) for combo in winning_combinations
    }
    return service


@given(
    winning_combinations=st.lists(valid_combination, min_size=1, max_size=10),
    test_combination=valid_combination
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_duplicate_detection_and_regeneration(winning_combinations, test_combination):
    """
    Feature: lotto-algorithm-simplification, Property 3: Duplicate Detection and Regeneration
    
    **Validates: Requirements 2.2**
    
    For any combination that matches a historical winning combination,
    the system should detect it as a duplicate.
    """
    # Given: Mock 데이터 서비스 생성
    mock_service = create_mock_data_service(winning_combinations)
    checker = DuplicateChecker(mock_service)
    
    # When: 테스트 조합이 당첨 조합 중 하나와 일치하는지 확인
    test_tuple = tuple(sorted(test_combination))
    winning_tuples = {tuple(sorted(combo)) for combo in winning_combinations}
    expected_is_duplicate = test_tuple in winning_tuples
    
    # Then: 중복 감지 결과가 예상과 일치해야 함
    actual_is_duplicate = await checker.is_duplicate(test_combination)
    assert actual_is_duplicate == expected_is_duplicate, (
        f"조합 {test_combination}의 중복 감지 결과가 예상과 다릅니다. "
        f"예상: {expected_is_duplicate}, 실제: {actual_is_duplicate}"
    )


@given(
    winning_combinations=st.lists(valid_combination, min_size=1, max_size=10),
    combination=valid_combination
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_order_independent_duplicate_checking(winning_combinations, combination):
    """
    Feature: lotto-algorithm-simplification, Property 4: Order-Independent Duplicate Checking
    
    **Validates: Requirements 2.3**
    
    For any two combinations with the same numbers in different orders,
    the duplicate checker should consider them as identical.
    """
    # Given: Mock 데이터 서비스 생성
    mock_service = create_mock_data_service(winning_combinations)
    checker = DuplicateChecker(mock_service)
    
    # When: 동일한 조합을 다양한 순서로 확인
    # 원본 순서
    result_original = await checker.is_duplicate(combination)
    
    # 역순
    reversed_combo = list(reversed(combination))
    result_reversed = await checker.is_duplicate(reversed_combo)
    
    # 정렬된 순서
    sorted_combo = sorted(combination)
    result_sorted = await checker.is_duplicate(sorted_combo)
    
    # Then: 모든 순서에서 동일한 결과를 반환해야 함
    assert result_original == result_reversed, (
        f"원본 {combination}과 역순 {reversed_combo}의 중복 감지 결과가 다릅니다. "
        f"원본: {result_original}, 역순: {result_reversed}"
    )
    
    assert result_original == result_sorted, (
        f"원본 {combination}과 정렬 {sorted_combo}의 중복 감지 결과가 다릅니다. "
        f"원본: {result_original}, 정렬: {result_sorted}"
    )


@given(
    winning_combinations=st.lists(valid_combination, min_size=1, max_size=10),
    new_combination=valid_combination
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_new_combination_consistency(winning_combinations, new_combination):
    """
    Property: is_new_combination과 is_duplicate의 일관성
    
    is_new_combination()은 is_duplicate()의 정확한 반대 결과를 반환해야 합니다.
    """
    # Given: Mock 데이터 서비스 생성
    mock_service = create_mock_data_service(winning_combinations)
    checker = DuplicateChecker(mock_service)
    
    # When: 두 메서드 호출
    is_dup = await checker.is_duplicate(new_combination)
    is_new = await checker.is_new_combination(new_combination)
    
    # Then: 결과가 정확히 반대여야 함
    assert is_dup != is_new, (
        f"is_duplicate()와 is_new_combination()의 결과가 일관되지 않습니다. "
        f"조합: {new_combination}, is_duplicate: {is_dup}, is_new: {is_new}"
    )


@given(
    winning_combinations=st.lists(valid_combination, min_size=5, max_size=20),
    test_combinations=st.lists(valid_combination, min_size=3, max_size=10)
)
@settings(max_examples=50)
@pytest.mark.asyncio
async def test_property_cache_consistency(winning_combinations, test_combinations):
    """
    Property: 캐싱이 결과에 영향을 주지 않음
    
    캐시 사용 여부와 관계없이 동일한 조합에 대해 동일한 결과를 반환해야 합니다.
    """
    # Given: Mock 데이터 서비스 생성
    mock_service = create_mock_data_service(winning_combinations)
    checker = DuplicateChecker(mock_service)
    
    # When: 각 조합을 두 번씩 확인 (첫 번째는 캐시 미스, 두 번째는 캐시 히트)
    for combo in test_combinations:
        first_result = await checker.is_duplicate(combo)
        second_result = await checker.is_duplicate(combo)
        
        # Then: 두 결과가 동일해야 함
        assert first_result == second_result, (
            f"캐시 사용 전후 결과가 다릅니다. "
            f"조합: {combo}, 첫 번째: {first_result}, 두 번째: {second_result}"
        )


@given(
    winning_combinations=st.lists(valid_combination, min_size=1, max_size=10)
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_all_winning_combinations_are_duplicates(winning_combinations):
    """
    Property: 모든 당첨 조합은 중복으로 감지되어야 함
    
    당첨 조합 목록에 있는 모든 조합은 중복으로 감지되어야 합니다.
    """
    # Given: Mock 데이터 서비스 생성
    mock_service = create_mock_data_service(winning_combinations)
    checker = DuplicateChecker(mock_service)
    
    # When & Then: 모든 당첨 조합이 중복으로 감지되어야 함
    for combo in winning_combinations:
        is_dup = await checker.is_duplicate(combo)
        assert is_dup is True, (
            f"당첨 조합 {combo}가 중복으로 감지되지 않았습니다."
        )


@given(
    invalid_length=st.integers(min_value=0, max_value=10).filter(lambda x: x != 6)
)
@settings(max_examples=50)
@pytest.mark.asyncio
async def test_property_invalid_length_combinations_are_duplicates(invalid_length):
    """
    Property: 유효하지 않은 길이의 조합은 중복으로 처리
    
    6개가 아닌 숫자 조합은 안전하게 중복으로 처리되어야 합니다.
    """
    # Given: Mock 데이터 서비스 생성
    mock_service = create_mock_data_service([[1, 2, 3, 4, 5, 6]])
    checker = DuplicateChecker(mock_service)
    
    # When: 유효하지 않은 길이의 조합 생성
    if invalid_length == 0:
        invalid_combo = []
    else:
        invalid_combo = list(range(1, invalid_length + 1))
    
    # Then: 중복(유효하지 않음)으로 처리되어야 함
    result = await checker.is_duplicate(invalid_combo)
    assert result is True, (
        f"유효하지 않은 길이({invalid_length})의 조합이 중복으로 처리되지 않았습니다."
    )
