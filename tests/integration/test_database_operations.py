# tests/integration/test_database_operations.py
import pytest
import asyncio
from datetime import datetime
from database.connector import AsyncDatabaseConnector
from database.repositories.lotto_repository import AsyncLottoRepository
from services.data_service import AsyncDataService
from utils.exceptions import DatabaseError, DataLoadError


class TestDatabaseConnection:
    """데이터베이스 연결 테스트"""

    @pytest.mark.asyncio
    async def test_connection_pool_creation(self):
        """연결 풀이 성공적으로 생성됨"""
        pool = await AsyncDatabaseConnector.get_pool()
        assert pool is not None
        assert not pool._closed

    @pytest.mark.asyncio
    async def test_connection_pool_reuse(self):
        """연결 풀이 재사용됨 (싱글톤)"""
        pool1 = await AsyncDatabaseConnector.get_pool()
        pool2 = await AsyncDatabaseConnector.get_pool()
        
        assert pool1 is pool2

    @pytest.mark.asyncio
    async def test_execute_simple_query(self):
        """간단한 쿼리 실행"""
        result = await AsyncDatabaseConnector.execute_query("SELECT 1 as test")
        
        assert result is not None
        assert len(result) == 1
        assert result[0]['test'] == 1


class TestLottoRepository:
    """로또 리포지토리 통합 테스트"""

    @pytest.mark.asyncio
    async def test_get_last_draw(self):
        """최근 회차 조회"""
        result = await AsyncLottoRepository.get_last_draw()
        
        assert result is not None
        assert 'no' in result
        assert result['no'] > 0
        
        # 번호 필드 확인
        for i in range(1, 7):
            assert str(i) in result
            assert 1 <= result[str(i)] <= 45

    @pytest.mark.asyncio
    async def test_get_draws_by_range(self):
        """범위 조회"""
        # 최근 회차 확인
        last_draw = await AsyncLottoRepository.get_last_draw()
        last_no = last_draw['no']
        
        # 최근 5개 회차 조회
        start_no = max(1, last_no - 4)
        results = await AsyncLottoRepository.get_draws_by_range(start_no, last_no)
        
        assert results is not None
        assert len(results) > 0
        assert len(results) <= 5
        
        # 회차 순서 확인
        for i in range(len(results) - 1):
            assert results[i]['no'] < results[i + 1]['no']

    @pytest.mark.asyncio
    async def test_get_draws_by_range_with_no_end(self):
        """종료 회차 없이 조회 (최신까지)"""
        # 최근 회차 확인
        last_draw = await AsyncLottoRepository.get_last_draw()
        last_no = last_draw['no']
        
        # 최근 10개 회차부터 최신까지
        start_no = max(1, last_no - 9)
        results = await AsyncLottoRepository.get_draws_by_range(start_no, None)
        
        assert results is not None
        assert len(results) > 0
        
        # 마지막 결과가 최신 회차인지 확인
        assert results[-1]['no'] == last_no

    @pytest.mark.asyncio
    async def test_check_draw_exists(self):
        """회차 존재 여부 확인"""
        # 최근 회차는 존재해야 함
        last_draw = await AsyncLottoRepository.get_last_draw()
        exists = await AsyncLottoRepository.check_draw_exists(last_draw['no'])
        
        assert exists is True
        
        # 미래 회차는 존재하지 않아야 함
        future_draw_no = last_draw['no'] + 1000
        not_exists = await AsyncLottoRepository.check_draw_exists(future_draw_no)
        
        assert not_exists is False


class TestDataServiceIntegration:
    """DataService 통합 테스트"""

    @pytest.mark.asyncio
    async def test_load_historical_data(self):
        """역대 데이터 로드"""
        service = AsyncDataService()
        
        # 최근 10개 회차 로드
        last_draw = await AsyncLottoRepository.get_last_draw()
        start_no = max(1, last_draw['no'] - 9)
        
        success = await service.load_historical_data(start_no=start_no)
        
        assert success is True
        assert len(service.draws) > 0
        assert len(service.existing_combinations) > 0
        assert len(service.draws) == len(service.existing_combinations)

    @pytest.mark.asyncio
    async def test_get_all_winning_combinations_from_db(self):
        """데이터베이스에서 당첨 조합 조회"""
        service = AsyncDataService()
        
        # 데이터 로드
        last_draw = await AsyncLottoRepository.get_last_draw()
        start_no = max(1, last_draw['no'] - 4)
        await service.load_historical_data(start_no=start_no)
        
        # 조합 조회
        combinations = await service.get_all_winning_combinations()
        
        assert len(combinations) > 0
        assert all(len(combo) == 6 for combo in combinations)
        assert all(all(1 <= n <= 45 for n in combo) for combo in combinations)
        assert all(combo == sorted(combo) for combo in combinations)

    @pytest.mark.asyncio
    async def test_save_and_verify_prediction(self):
        """예측 저장 및 검증"""
        service = AsyncDataService()
        
        # 데이터 로드
        last_draw = await AsyncLottoRepository.get_last_draw()
        await service.load_historical_data(start_no=max(1, last_draw['no'] - 4))
        
        # 테스트용 조합 생성 (기존 당첨 번호와 다른 조합)
        test_combination = [1, 2, 3, 4, 5, 6]
        
        # 저장
        try:
            saved_id = await service.save_prediction(test_combination)
            assert saved_id > 0 or saved_id == -1  # -1은 ID 조회 실패 (저장은 성공)
            
            # 저장된 데이터 확인
            next_no = last_draw['no'] + 1
            saved_predictions = await AsyncLottoRepository.get_recommendations_for_draw(next_no)
            
            # 방금 저장한 조합이 포함되어 있는지 확인
            saved_numbers = [pred['numbers'] for pred in saved_predictions]
            assert any(sorted(nums) == sorted(test_combination) for nums in saved_numbers)
            
        finally:
            # 테스트 데이터 정리
            cleanup_query = """
            DELETE FROM recommand 
            WHERE next_no = %s 
            AND `1` = %s AND `2` = %s AND `3` = %s 
            AND `4` = %s AND `5` = %s AND `6` = %s
            """
            sorted_combo = sorted(test_combination)
            await AsyncDatabaseConnector.execute_query(
                cleanup_query,
                (next_no, *sorted_combo),
                fetch=False
            )


class TestTransactions:
    """트랜잭션 테스트"""

    @pytest.mark.asyncio
    async def test_multiple_inserts_in_sequence(self):
        """순차적 다중 삽입"""
        service = AsyncDataService()
        
        # 데이터 로드
        last_draw = await AsyncLottoRepository.get_last_draw()
        await service.load_historical_data(start_no=max(1, last_draw['no'] - 4))
        
        # 여러 조합 저장
        test_combinations = [
            [7, 14, 21, 28, 35, 42],
            [8, 15, 22, 29, 36, 43],
            [9, 16, 23, 30, 37, 44],
        ]
        
        saved_ids = []
        try:
            for combo in test_combinations:
                saved_id = await service.save_prediction(combo)
                saved_ids.append(saved_id)
            
            # 모두 저장되었는지 확인
            assert len(saved_ids) == len(test_combinations)
            
        finally:
            # 테스트 데이터 정리
            next_no = last_draw['no'] + 1
            for combo in test_combinations:
                cleanup_query = """
                DELETE FROM recommand 
                WHERE next_no = %s 
                AND `1` = %s AND `2` = %s AND `3` = %s 
                AND `4` = %s AND `5` = %s AND `6` = %s
                """
                sorted_combo = sorted(combo)
                await AsyncDatabaseConnector.execute_query(
                    cleanup_query,
                    (next_no, *sorted_combo),
                    fetch=False
                )

    @pytest.mark.asyncio
    async def test_concurrent_queries(self):
        """동시 쿼리 실행"""
        # 여러 쿼리를 동시에 실행
        tasks = [
            AsyncDatabaseConnector.execute_query("SELECT 1 as test"),
            AsyncDatabaseConnector.execute_query("SELECT 2 as test"),
            AsyncDatabaseConnector.execute_query("SELECT 3 as test"),
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        assert results[0][0]['test'] == 1
        assert results[1][0]['test'] == 2
        assert results[2][0]['test'] == 3


class TestErrorHandling:
    """에러 처리 통합 테스트"""

    @pytest.mark.asyncio
    async def test_invalid_query_handling(self):
        """잘못된 쿼리 처리"""
        with pytest.raises(DatabaseError):
            await AsyncDatabaseConnector.execute_query("SELECT * FROM nonexistent_table")

    @pytest.mark.asyncio
    async def test_invalid_draw_range(self):
        """잘못된 회차 범위 처리"""
        service = AsyncDataService()
        
        # 음수 회차
        with pytest.raises(Exception):  # ValidationError 또는 다른 예외
            await service.load_historical_data(start_no=-1)
        
        # 종료 회차가 시작 회차보다 작음
        with pytest.raises(Exception):
            await service.load_historical_data(start_no=100, end_no=50)

    @pytest.mark.asyncio
    async def test_connection_recovery(self):
        """연결 복구 테스트"""
        # 정상 쿼리 실행
        result1 = await AsyncDatabaseConnector.execute_query("SELECT 1 as test")
        assert result1 is not None
        
        # 연결이 유지되는지 확인
        result2 = await AsyncDatabaseConnector.execute_query("SELECT 2 as test")
        assert result2 is not None
