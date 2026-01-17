# tests/unit/test_data_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from services.data_service import AsyncDataService
from models.lotto_draw import LottoDraw
from utils.exceptions import DataLoadError, ValidationError
from datetime import datetime


@pytest.fixture
def data_service():
    """DataService 인스턴스 생성"""
    return AsyncDataService()


@pytest.fixture
def sample_draws():
    """샘플 당첨 데이터"""
    return [
        LottoDraw(draw_no=1, numbers=[1, 2, 3, 4, 5, 6], draw_date=datetime.now()),
        LottoDraw(draw_no=2, numbers=[7, 8, 9, 10, 11, 12], draw_date=datetime.now()),
        LottoDraw(draw_no=3, numbers=[13, 14, 15, 16, 17, 18], draw_date=datetime.now()),
    ]


class TestGetAllWinningCombinations:
    """당첨 번호 조회 테스트"""

    @pytest.mark.asyncio
    async def test_returns_all_combinations_when_draws_loaded(self, data_service, sample_draws):
        """당첨 데이터가 로드된 경우 모든 조합 반환"""
        # Given
        data_service.draws = sample_draws
        
        # When
        combinations = await data_service.get_all_winning_combinations()
        
        # Then
        assert len(combinations) == 3
        assert combinations[0] == [1, 2, 3, 4, 5, 6]
        assert combinations[1] == [7, 8, 9, 10, 11, 12]
        assert combinations[2] == [13, 14, 15, 16, 17, 18]

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_draws(self, data_service):
        """당첨 데이터가 없는 경우 빈 리스트 반환"""
        # Given
        data_service.draws = []
        
        # When
        combinations = await data_service.get_all_winning_combinations()
        
        # Then
        assert combinations == []

    @pytest.mark.asyncio
    async def test_returns_sorted_combinations(self, data_service):
        """조합이 정렬되어 반환되는지 확인"""
        # Given
        data_service.draws = [
            LottoDraw(draw_no=1, numbers=[45, 1, 23, 12, 34, 5], draw_date=datetime.now())
        ]
        
        # When
        combinations = await data_service.get_all_winning_combinations()
        
        # Then
        assert combinations[0] == [1, 5, 12, 23, 34, 45]

    @pytest.mark.asyncio
    async def test_raises_error_on_exception(self, data_service):
        """예외 발생 시 DataLoadError 발생"""
        # Given
        data_service.draws = [MagicMock(spec=LottoDraw)]
        data_service.draws[0].num1 = None  # 오류 유발
        
        # When/Then
        with pytest.raises(DataLoadError):
            await data_service.get_all_winning_combinations()


class TestSavePrediction:
    """예측 저장 테스트"""

    @pytest.mark.asyncio
    async def test_saves_prediction_successfully(self, data_service, sample_draws):
        """예측이 성공적으로 저장됨"""
        # Given
        data_service.draws = sample_draws
        combination = [1, 5, 12, 23, 34, 45]
        
        with patch('services.data_service.AsyncDatabaseConnector.execute_query') as mock_query:
            mock_query.side_effect = [
                1,  # INSERT 결과 (affected rows)
                [{'id': 123}]  # LAST_INSERT_ID 결과
            ]
            
            # When
            result_id = await data_service.save_prediction(combination)
            
            # Then
            assert result_id == 123
            assert mock_query.call_count == 2
            
            # 첫 번째 호출 (INSERT) 검증
            first_call = mock_query.call_args_list[0]
            assert 'INSERT INTO recommand' in first_call[0][0]
            assert first_call[0][1] == (4, 1, 5, 12, 23, 34, 45)  # next_no=4 (마지막 회차 3 + 1)

    @pytest.mark.asyncio
    async def test_validates_combination_length(self, data_service):
        """조합 길이 검증"""
        # Given
        invalid_combination = [1, 2, 3, 4, 5]  # 5개만
        
        # When/Then
        with pytest.raises(ValidationError) as exc_info:
            await data_service.save_prediction(invalid_combination)
        
        assert "정확히 6개의 숫자여야 합니다" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validates_number_range(self, data_service):
        """숫자 범위 검증"""
        # Given
        invalid_combination = [1, 2, 3, 4, 5, 50]  # 50은 범위 초과
        
        # When/Then
        with pytest.raises(ValidationError) as exc_info:
            await data_service.save_prediction(invalid_combination)
        
        assert "1-45 범위의 정수여야 합니다" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validates_number_type(self, data_service):
        """숫자 타입 검증"""
        # Given
        invalid_combination = [1, 2, 3, 4, 5, "6"]  # 문자열 포함
        
        # When/Then
        with pytest.raises(ValidationError):
            await data_service.save_prediction(invalid_combination)

    @pytest.mark.asyncio
    async def test_sorts_numbers_before_saving(self, data_service, sample_draws):
        """저장 전 숫자 정렬"""
        # Given
        data_service.draws = sample_draws
        unsorted_combination = [45, 1, 23, 12, 34, 5]
        
        with patch('services.data_service.AsyncDatabaseConnector.execute_query') as mock_query:
            mock_query.side_effect = [
                1,  # INSERT 결과
                [{'id': 123}]  # LAST_INSERT_ID 결과
            ]
            
            # When
            await data_service.save_prediction(unsorted_combination)
            
            # Then
            first_call = mock_query.call_args_list[0]
            # 정렬된 순서로 저장되어야 함
            assert first_call[0][1] == (4, 1, 5, 12, 23, 34, 45)

    @pytest.mark.asyncio
    async def test_uses_parameterized_query(self, data_service, sample_draws):
        """파라미터화된 쿼리 사용 확인 (SQL 인젝션 방지)"""
        # Given
        data_service.draws = sample_draws
        combination = [1, 5, 12, 23, 34, 45]
        
        with patch('services.data_service.AsyncDatabaseConnector.execute_query') as mock_query:
            mock_query.side_effect = [
                1,  # INSERT 결과
                [{'id': 123}]  # LAST_INSERT_ID 결과
            ]
            
            # When
            await data_service.save_prediction(combination)
            
            # Then
            first_call = mock_query.call_args_list[0]
            query = first_call[0][0]
            params = first_call[0][1]
            
            # 쿼리에 %s 플레이스홀더 사용 확인
            assert '%s' in query
            # 파라미터가 튜플로 전달되는지 확인
            assert isinstance(params, tuple)
            assert len(params) == 7  # next_no + 6개 숫자

    @pytest.mark.asyncio
    async def test_handles_database_error(self, data_service, sample_draws):
        """데이터베이스 오류 처리"""
        # Given
        data_service.draws = sample_draws
        combination = [1, 5, 12, 23, 34, 45]
        
        with patch('services.data_service.AsyncDatabaseConnector.execute_query') as mock_query:
            mock_query.side_effect = Exception("Database connection failed")
            
            # When/Then
            with pytest.raises(DataLoadError) as exc_info:
                await data_service.save_prediction(combination)
            
            assert "예측 저장 실패" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handles_insert_failure(self, data_service, sample_draws):
        """INSERT 실패 처리"""
        # Given
        data_service.draws = sample_draws
        combination = [1, 5, 12, 23, 34, 45]
        
        with patch('services.data_service.AsyncDatabaseConnector.execute_query') as mock_query:
            mock_query.return_value = 0  # 0 rows affected
            
            # When/Then
            with pytest.raises(DataLoadError) as exc_info:
                await data_service.save_prediction(combination)
            
            assert "예측 저장 실패" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_calculates_next_draw_number(self, data_service, sample_draws):
        """다음 회차 번호 계산"""
        # Given
        data_service.draws = sample_draws  # 마지막 회차 = 3
        combination = [1, 5, 12, 23, 34, 45]
        
        with patch('services.data_service.AsyncDatabaseConnector.execute_query') as mock_query:
            mock_query.side_effect = [
                1,  # INSERT 결과
                [{'id': 123}]  # LAST_INSERT_ID 결과
            ]
            
            # When
            await data_service.save_prediction(combination)
            
            # Then
            first_call = mock_query.call_args_list[0]
            next_no = first_call[0][1][0]
            assert next_no == 4  # 마지막 회차(3) + 1

    @pytest.mark.asyncio
    async def test_handles_no_draws_loaded(self, data_service):
        """당첨 데이터가 로드되지 않은 경우 처리"""
        # Given
        data_service.draws = []
        combination = [1, 5, 12, 23, 34, 45]
        
        with patch('services.data_service.AsyncDatabaseConnector.execute_query') as mock_query:
            mock_query.side_effect = [
                1,  # INSERT 결과
                [{'id': 123}]  # LAST_INSERT_ID 결과
            ]
            
            # When
            await data_service.save_prediction(combination)
            
            # Then
            first_call = mock_query.call_args_list[0]
            next_no = first_call[0][1][0]
            assert next_no == 1  # 기본값 1 사용


class TestErrorHandling:
    """에러 처리 테스트"""

    @pytest.mark.asyncio
    async def test_logs_error_on_save_failure(self, data_service, sample_draws, caplog):
        """저장 실패 시 에러 로깅"""
        # Given
        data_service.draws = sample_draws
        combination = [1, 5, 12, 23, 34, 45]
        
        with patch('services.data_service.AsyncDatabaseConnector.execute_query') as mock_query:
            mock_query.side_effect = Exception("Database error")
            
            # When
            with pytest.raises(DataLoadError):
                await data_service.save_prediction(combination)
            
            # Then
            assert "예측 저장 중 오류" in caplog.text

    @pytest.mark.asyncio
    async def test_logs_error_on_get_combinations_failure(self, data_service, caplog):
        """조합 조회 실패 시 에러 로깅"""
        # Given
        data_service.draws = [MagicMock(spec=LottoDraw)]
        data_service.draws[0].num1 = None  # 오류 유발
        
        # When
        with pytest.raises(DataLoadError):
            await data_service.get_all_winning_combinations()
        
        # Then
        assert "당첨 조합 조회 중 오류" in caplog.text
