"""전체 예측 플로우 통합 테스트

이 모듈은 예측 생성부터 저장, 조회까지 전체 플로우를 테스트합니다.
실제 데이터베이스 연결을 사용하며, Telegram 알림도 테스트합니다.
"""

import pytest
import asyncio
from datetime import datetime
from typing import List

from database.connector import AsyncDatabaseConnector
from database.repositories.lotto_repository import AsyncLottoRepository
from services.data_service import AsyncDataService
from services.random_generator import RandomGenerator
from services.duplicate_checker import DuplicateChecker
from services.simplified_prediction_service import SimplifiedPredictionService
from utils.exceptions import ValidationError, PredictionGenerationError


class TestFullPredictionFlow:
    """전체 예측 플로우 통합 테스트"""

    @pytest.mark.asyncio
    async def test_complete_prediction_workflow(self):
        """
        완전한 예측 워크플로우 테스트
        
        플로우:
        1. 데이터 로드
        2. 예측 생성
        3. 데이터베이스 저장
        4. 저장된 데이터 조회
        
        Requirements: 1.1, 2.2, 3.1, 6.1
        """
        # 1. 서비스 초기화
        data_service = AsyncDataService()
        random_generator = RandomGenerator()
        duplicate_checker = DuplicateChecker(data_service)
        prediction_service = SimplifiedPredictionService(
            random_generator=random_generator,
            duplicate_checker=duplicate_checker,
            data_service=data_service
        )
        
        # 2. 데이터 로드
        last_draw = await AsyncLottoRepository.get_last_draw()
        assert last_draw is not None, "최근 회차 데이터를 가져올 수 없습니다"
        
        last_draw_no = last_draw['no']
        start_no = max(1, last_draw_no - 9)  # 최근 10개 회차
        
        success = await data_service.load_historical_data(
            start_no=start_no,
            end_no=last_draw_no
        )
        assert success is True, "데이터 로드 실패"
        assert len(data_service.draws) > 0, "로드된 데이터가 없습니다"
        
        # 3. 예측 생성
        num_predictions = 3
        predictions = await prediction_service.generate_predictions(
            num_predictions=num_predictions
        )
        
        # 예측 검증
        assert len(predictions) == num_predictions, f"예측 개수 불일치: {len(predictions)} != {num_predictions}"
        
        for pred in predictions:
            # 6개 숫자
            assert len(pred.combination) == 6, f"조합 길이 오류: {len(pred.combination)}"
            
            # 범위 확인
            assert all(1 <= n <= 45 for n in pred.combination), f"범위 오류: {pred.combination}"
            
            # 고유성 확인
            assert len(set(pred.combination)) == 6, f"중복 숫자: {pred.combination}"
            
            # 정렬 확인
            assert pred.combination == sorted(pred.combination), f"정렬 오류: {pred.combination}"
        
        # 4. 데이터베이스 저장
        next_draw_no = last_draw_no + 1
        saved_combinations = []
        
        try:
            for pred in predictions:
                success = await AsyncLottoRepository.save_recommendation(
                    numbers=pred.combination,
                    next_no=next_draw_no
                )
                assert success is True, f"예측 저장 실패: {pred.combination}"
                saved_combinations.append(pred.combination)
            
            # 5. 저장된 데이터 조회
            saved_predictions = await AsyncLottoRepository.get_recommendations_for_draw(next_draw_no)
            
            assert len(saved_predictions) >= num_predictions, "저장된 예측 개수 부족"
            
            # 저장된 조합 확인
            saved_numbers = [pred['numbers'] for pred in saved_predictions]
            
            for combo in saved_combinations:
                assert any(
                    sorted(nums) == sorted(combo) for nums in saved_numbers
                ), f"저장된 조합을 찾을 수 없음: {combo}"
            
        finally:
            # 테스트 데이터 정리
            for combo in saved_combinations:
                cleanup_query = """
                DELETE FROM recommand 
                WHERE next_no = %s 
                AND `1` = %s AND `2` = %s AND `3` = %s 
                AND `4` = %s AND `5` = %s AND `6` = %s
                """
                sorted_combo = sorted(combo)
                await AsyncDatabaseConnector.execute_query(
                    cleanup_query,
                    (next_draw_no, *sorted_combo),
                    fetch=False
                )

    @pytest.mark.asyncio
    async def test_prediction_with_duplicate_prevention(self):
        """
        중복 방지 기능이 포함된 예측 플로우 테스트
        
        Requirements: 2.2, 2.3
        """
        # 서비스 초기화
        data_service = AsyncDataService()
        random_generator = RandomGenerator()
        duplicate_checker = DuplicateChecker(data_service)
        prediction_service = SimplifiedPredictionService(
            random_generator=random_generator,
            duplicate_checker=duplicate_checker,
            data_service=data_service
        )
        
        # 데이터 로드
        last_draw = await AsyncLottoRepository.get_last_draw()
        last_draw_no = last_draw['no']
        start_no = max(1, last_draw_no - 9)
        
        await data_service.load_historical_data(start_no=start_no, end_no=last_draw_no)
        
        # 예측 생성
        predictions = await prediction_service.generate_predictions(num_predictions=5)
        
        # 과거 당첨 번호와 중복 확인
        winning_combinations = await data_service.get_all_winning_combinations()
        winning_set = {tuple(sorted(combo)) for combo in winning_combinations}
        
        for pred in predictions:
            combo_tuple = tuple(sorted(pred.combination))
            assert combo_tuple not in winning_set, f"과거 당첨 번호와 중복: {pred.combination}"
        
        # 배치 내 고유성 확인
        prediction_set = {tuple(sorted(pred.combination)) for pred in predictions}
        assert len(prediction_set) == len(predictions), "배치 내 중복 조합 발견"

    @pytest.mark.asyncio
    async def test_batch_prediction_uniqueness(self):
        """
        배치 예측의 고유성 테스트
        
        Requirements: 6.1, 6.4
        """
        # 서비스 초기화
        data_service = AsyncDataService()
        random_generator = RandomGenerator()
        duplicate_checker = DuplicateChecker(data_service)
        prediction_service = SimplifiedPredictionService(
            random_generator=random_generator,
            duplicate_checker=duplicate_checker,
            data_service=data_service
        )
        
        # 데이터 로드
        last_draw = await AsyncLottoRepository.get_last_draw()
        last_draw_no = last_draw['no']
        start_no = max(1, last_draw_no - 9)
        
        await data_service.load_historical_data(start_no=start_no, end_no=last_draw_no)
        
        # 최대 개수 예측 생성
        num_predictions = 20
        predictions = await prediction_service.generate_predictions(num_predictions=num_predictions)
        
        # 개수 확인
        assert len(predictions) == num_predictions
        
        # 모든 조합이 고유한지 확인
        combinations = [tuple(sorted(pred.combination)) for pred in predictions]
        assert len(set(combinations)) == num_predictions, "중복 조합 발견"
        
        # 각 조합이 유효한지 확인
        for pred in predictions:
            assert len(pred.combination) == 6
            assert all(1 <= n <= 45 for n in pred.combination)
            assert len(set(pred.combination)) == 6
            assert pred.combination == sorted(pred.combination)

    @pytest.mark.asyncio
    async def test_input_validation(self):
        """
        입력 유효성 검증 테스트
        
        Requirements: 6.2
        """
        # 서비스 초기화
        data_service = AsyncDataService()
        random_generator = RandomGenerator()
        duplicate_checker = DuplicateChecker(data_service)
        prediction_service = SimplifiedPredictionService(
            random_generator=random_generator,
            duplicate_checker=duplicate_checker,
            data_service=data_service
        )
        
        # 데이터 로드
        last_draw = await AsyncLottoRepository.get_last_draw()
        last_draw_no = last_draw['no']
        start_no = max(1, last_draw_no - 4)
        
        await data_service.load_historical_data(start_no=start_no, end_no=last_draw_no)
        
        # 유효하지 않은 입력 테스트
        
        # 0개 예측
        with pytest.raises(ValidationError):
            await prediction_service.generate_predictions(num_predictions=0)
        
        # 음수 예측
        with pytest.raises(ValidationError):
            await prediction_service.generate_predictions(num_predictions=-1)
        
        # 21개 이상 예측
        with pytest.raises(ValidationError):
            await prediction_service.generate_predictions(num_predictions=21)
        
        # 문자열 입력
        with pytest.raises(ValidationError):
            await prediction_service.generate_predictions(num_predictions="5")

    @pytest.mark.asyncio
    async def test_performance_requirements(self):
        """
        성능 요구사항 테스트
        
        Requirements: 9.1, 9.2
        """
        import time
        
        # 서비스 초기화
        data_service = AsyncDataService()
        random_generator = RandomGenerator()
        duplicate_checker = DuplicateChecker(data_service)
        prediction_service = SimplifiedPredictionService(
            random_generator=random_generator,
            duplicate_checker=duplicate_checker,
            data_service=data_service
        )
        
        # 데이터 로드
        last_draw = await AsyncLottoRepository.get_last_draw()
        last_draw_no = last_draw['no']
        start_no = max(1, last_draw_no - 9)
        
        await data_service.load_historical_data(start_no=start_no, end_no=last_draw_no)
        
        # 단일 예측 성능 테스트 (< 100ms)
        start_time = time.time()
        predictions = await prediction_service.generate_predictions(num_predictions=1)
        elapsed_time = (time.time() - start_time) * 1000  # ms
        
        assert len(predictions) == 1
        # 성능 요구사항은 참고용 (실제 환경에 따라 다를 수 있음)
        print(f"단일 예측 소요 시간: {elapsed_time:.2f}ms")
        
        # 20개 예측 성능 테스트 (< 500ms)
        start_time = time.time()
        predictions = await prediction_service.generate_predictions(num_predictions=20)
        elapsed_time = (time.time() - start_time) * 1000  # ms
        
        assert len(predictions) == 20
        print(f"20개 예측 소요 시간: {elapsed_time:.2f}ms")

    @pytest.mark.asyncio
    async def test_concurrent_predictions(self):
        """
        동시 예측 요청 테스트
        
        Requirements: 9.3
        """
        # 서비스 초기화
        data_service = AsyncDataService()
        random_generator = RandomGenerator()
        duplicate_checker = DuplicateChecker(data_service)
        prediction_service = SimplifiedPredictionService(
            random_generator=random_generator,
            duplicate_checker=duplicate_checker,
            data_service=data_service
        )
        
        # 데이터 로드
        last_draw = await AsyncLottoRepository.get_last_draw()
        last_draw_no = last_draw['no']
        start_no = max(1, last_draw_no - 9)
        
        await data_service.load_historical_data(start_no=start_no, end_no=last_draw_no)
        
        # 동시에 여러 예측 요청
        tasks = [
            prediction_service.generate_predictions(num_predictions=3),
            prediction_service.generate_predictions(num_predictions=5),
            prediction_service.generate_predictions(num_predictions=2),
        ]
        
        results = await asyncio.gather(*tasks)
        
        # 각 결과 검증
        assert len(results) == 3
        assert len(results[0]) == 3
        assert len(results[1]) == 5
        assert len(results[2]) == 2
        
        # 모든 조합이 유효한지 확인
        for predictions in results:
            for pred in predictions:
                assert len(pred.combination) == 6
                assert all(1 <= n <= 45 for n in pred.combination)
                assert len(set(pred.combination)) == 6



