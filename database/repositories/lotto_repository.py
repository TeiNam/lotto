# database/repositories/lotto_repository.py
import logging
from typing import List, Dict, Any, Optional

from database.connector import AsyncDatabaseConnector

logger = logging.getLogger("lotto_prediction")


class AsyncLottoRepository:
    """비동기 로또 데이터 액세스 리포지토리"""

    @staticmethod
    async def get_draws_by_range(start_no: int, end_no: Optional[int]) -> List[Dict[str, Any]]:
        """특정 범위의 로또 당첨 번호 조회 (비동기)"""
        if end_no is None:
            # 최신 회차까지 전부 조회
            query = """
            SELECT no, `1`, `2`, `3`, `4`, `5`, `6`, create_at 
            FROM result 
            WHERE no >= %s
            ORDER BY no
            """
            params = (start_no,)
        else:
            query = """
            SELECT no, `1`, `2`, `3`, `4`, `5`, `6`, create_at 
            FROM result 
            WHERE no BETWEEN %s AND %s 
            ORDER BY no
            """
            params = (start_no, end_no)

        results = await AsyncDatabaseConnector.execute_query(query, params)

        if results is None:
            logger.error(f"당첨 번호 조회 실패 (범위: {start_no}-{end_no if end_no else '최신'})")
            return []

        logger.info(f"당첨 번호 {len(results)}개 조회 성공 (범위: {start_no}-{end_no if end_no else '최신'})")
        return results

    @staticmethod
    async def get_last_draw() -> Optional[Dict[str, Any]]:
        """가장 최근 회차의 당첨 번호 조회 (비동기)"""
        query = """
        SELECT no, `1`, `2`, `3`, `4`, `5`, `6`, create_at 
        FROM result 
        ORDER BY no DESC 
        LIMIT 1
        """

        results = await AsyncDatabaseConnector.execute_query(query)

        if not results:
            logger.error("최근 당첨 번호 조회 실패")
            return None

        logger.info(f"최근 당첨 번호 조회 성공 (회차: {results[0]['no']})")
        return results[0]

    @staticmethod
    async def save_prediction(draw_no: int, numbers: List[int], score: float, common_count: int) -> bool:
        """예측 결과 저장 (비동기)"""
        query = """
        INSERT INTO predictions (draw_no, number1, number2, number3, number4, number5, number6, score, common_count) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        params = (draw_no, *numbers, score, common_count)

        result = await AsyncDatabaseConnector.execute_query(query, params, fetch=False)

        if result is None or result <= 0:
            logger.error(f"예측 결과 저장 실패 (회차: {draw_no})")
            return False

        logger.info(f"예측 결과 저장 성공 (회차: {draw_no})")
        return True

    @staticmethod
    async def save_recommendation(numbers: List[int], next_no: int) -> bool:
        """예측 결과를 recommand 테이블에 저장 (비동기)"""
        # 정렬된 번호 사용
        sorted_numbers = sorted(numbers)

        query = """
        INSERT INTO recommand (next_no, `1`, `2`, `3`, `4`, `5`, `6`) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        params = (next_no, *sorted_numbers)

        try:
            result = await AsyncDatabaseConnector.execute_query(query, params, fetch=False)

            if result is None or result <= 0:
                logger.error(f"예측 결과 저장 실패: {sorted_numbers}, 회차: {next_no}")
                return False

            logger.info(f"예측 결과 저장 성공: {sorted_numbers}, 회차: {next_no}")
            return True
        except Exception as e:
            logger.error(f"예측 결과 저장 중 DB 오류: {e}, 번호: {sorted_numbers}, 회차: {next_no}")
            return False

    @staticmethod
    async def save_draw_result(draw_no: int, numbers: List[int]) -> bool:
        """새로운 당첨 결과를 result 테이블에 저장 (비동기)"""
        # 번호 정렬 (필요하다면)
        sorted_numbers = sorted(numbers)

        # 중복 저장 방지를 위해 기존 데이터 확인
        check_query = """
        SELECT no FROM result WHERE no = %s
        """

        existing = await AsyncDatabaseConnector.execute_query(check_query, (draw_no,))
        if existing:
            logger.warning(f"이미 존재하는 당첨 결과입니다 (회차: {draw_no})")
            return False

        # 새 결과 저장
        query = """
        INSERT INTO result (no, `1`, `2`, `3`, `4`, `5`, `6`) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        params = (draw_no, *sorted_numbers)

        try:
            result = await AsyncDatabaseConnector.execute_query(query, params, fetch=False)

            if result is None or result <= 0:
                logger.error(f"당첨 결과 저장 실패: {sorted_numbers}, 회차: {draw_no}")
                return False

            logger.info(f"당첨 결과 저장 성공: {sorted_numbers}, 회차: {draw_no}")
            return True
        except Exception as e:
            logger.error(f"당첨 결과 저장 중 DB 오류: {e}, 번호: {sorted_numbers}, 회차: {draw_no}")
            return False
