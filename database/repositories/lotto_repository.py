# database/repositories/lotto_repository.py
import logging
from typing import List, Dict, Any, Optional

from database.connector import AsyncDatabaseConnector
from utils.exceptions import DatabaseError

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

    @classmethod
    async def check_draw_exists(cls, draw_no: int) -> bool:
        """지정된 회차가 result 테이블에 이미 존재하는지 확인"""
        try:
            pool = await AsyncDatabaseConnector.get_pool()

            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    query = "SELECT COUNT(*) as count FROM result WHERE no = %s"
                    await cursor.execute(query, (draw_no,))
                    result = await cursor.fetchone()

                    # 결과가 딕셔너리인지 튜플인지 확인하고 적절히 처리
                    if result:
                        if isinstance(result, dict):
                            # 딕셔너리 형태로 반환되는 경우
                            return result.get('count', 0) > 0
                        elif isinstance(result, (list, tuple)):
                            # 튜플 형태로 반환되는 경우
                            return result[0] > 0

                    return False

        except Exception as e:
            logger.error(f"회차 존재 여부 확인 중 오류: {e}")
            raise DatabaseError(f"회차 존재 여부 확인 중 오류: {e}")

    @classmethod
    async def get_recommendations_for_draw(cls, draw_no: int) -> List[Dict[str, Any]]:
        """특정 회차에 대한 예측 결과 조회"""
        try:
            pool = await AsyncDatabaseConnector.get_pool()

            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # 먼저 전체 회차 목록 조회 (디버깅용)
                    check_query = "SELECT DISTINCT next_no FROM recommand ORDER BY next_no"
                    await cursor.execute(check_query)
                    all_draws = await cursor.fetchall()
                    available_draws = [row['next_no'] for row in all_draws]
                    logger.debug(f"사용 가능한 예측 회차: {available_draws}")
                    
                    # 원래 쿼리
                    query = """
                    SELECT id, next_no, `1`, `2`, `3`, `4`, `5`, `6`, create_at
                    FROM recommand
                    WHERE next_no = %s
                    ORDER BY id ASC
                    """

                    # 정수형으로 명시적 변환
                    draw_no = int(draw_no)
                    await cursor.execute(query, (draw_no,))
                    results = await cursor.fetchall()
                    
                    logger.debug(f"조회된 결과 수: {len(results)} for draw_no: {draw_no}")

                    recommendations = []
                    for row in results:
                        numbers = [row[f'{i}'] for i in range(1, 7)]
                        recommendations.append({
                            "id": row['id'],
                            "next_no": row['next_no'],
                            "numbers": numbers,
                            "create_at": row['create_at']
                        })

                    return recommendations

        except Exception as e:
            logger.error(f"예측 결과 조회 중 오류: {e}")
            raise DatabaseError(f"예측 결과 조회 중 오류: {e}")
            
    @classmethod
    async def execute_raw_query(cls, query: str, params: tuple = None):
        """임의의 쿼리 실행 (디버깅용)"""
        try:
            pool = await AsyncDatabaseConnector.get_pool()

            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query, params or ())
                    results = await cursor.fetchall()
                    return results

        except Exception as e:
            logger.error(f"쿼리 실행 중 오류: {e}")
            raise DatabaseError(f"쿼리 실행 중 오류: {e}")