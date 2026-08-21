# database/repositories/lotto_repository.py
import logging
import aiomysql
from datetime import datetime
from typing import List, Dict, Any, Optional

from database.connector import AsyncDatabaseConnector
from config.settings import KST
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
            SELECT no, `1`, `2`, `3`, `4`, `5`, `6`, bonus, create_at 
            FROM result 
            WHERE no >= %s
            ORDER BY no
            """
            params = (start_no,)
        else:
            query = """
            SELECT no, `1`, `2`, `3`, `4`, `5`, `6`, bonus, create_at 
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
        SELECT no, `1`, `2`, `3`, `4`, `5`, `6`, bonus, create_at 
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
    async def save_recommendation(
        numbers: List[int], next_no: int, user_id: Optional[int] = None
    ) -> bool:
        """예측 결과를 recommand 테이블에 저장 (비동기)

        Args:
            numbers: 예측 번호 리스트
            next_no: 다음 회차 번호
            user_id: 텔레그램 사용자 ID (선택)
        """
        sorted_numbers = sorted(numbers)

        query = """
        INSERT INTO recommand (next_no, user_id, `1`, `2`, `3`, `4`, `5`, `6`, create_at) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        # create_at을 KST로 명시 저장 (MySQL 세션 타임존이 UTC여도 KST로 고정)
        kst_now = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
        params = (next_no, user_id, *sorted_numbers, kst_now)

        try:
            result = await AsyncDatabaseConnector.execute_query(query, params, fetch=False)

            if result is None or result <= 0:
                logger.error(f"예측 결과 저장 실패: {sorted_numbers}, 회차: {next_no}")
                return False

            logger.info(f"예측 결과 저장 성공: {sorted_numbers}, 회차: {next_no}, user_id: {user_id}")
            return True
        except Exception as e:
            logger.error(f"예측 결과 저장 중 DB 오류: {e}, 번호: {sorted_numbers}, 회차: {next_no}")
            return False

    @staticmethod
    async def save_draw_result(
        draw_no: int, numbers: List[int], bonus: Optional[int] = None
    ) -> bool:
        """새로운 당첨 결과를 result 테이블에 저장 (비동기)"""
        # 번호 정렬
        sorted_numbers = sorted(numbers)

        # 중복 저장 방지를 위해 기존 데이터 확인
        check_query = """
        SELECT no FROM result WHERE no = %s
        """

        existing = await AsyncDatabaseConnector.execute_query(check_query, (draw_no,))
        if existing:
            logger.warning(f"이미 존재하는 당첨 결과입니다 (회차: {draw_no})")
            return False

        # 새 결과 저장 (보너스 번호 포함)
        query = """
        INSERT INTO result (no, `1`, `2`, `3`, `4`, `5`, `6`, bonus) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        params = (draw_no, *sorted_numbers, bonus)

        try:
            result = await AsyncDatabaseConnector.execute_query(query, params, fetch=False)

            if result is None or result <= 0:
                logger.error(f"당첨 결과 저장 실패: {sorted_numbers}, 보너스: {bonus}, 회차: {draw_no}")
                return False

            logger.info(f"당첨 결과 저장 성공: {sorted_numbers}, 보너스: {bonus}, 회차: {draw_no}")
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
    async def get_recommendations_for_draw(
        cls, draw_no: int, user_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """특정 회차에 대한 예측 결과 조회

        Args:
            draw_no: 회차 번호
            user_id: 텔레그램 사용자 ID (None이면 전체 조회)
        """
        try:
            draw_no = int(draw_no)
            logger.info(f"회차 {draw_no}에 대한 예측 조회 시작 (user_id: {user_id})")
            
            pool = await AsyncDatabaseConnector.get_pool()
            
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    if user_id is not None:
                        query = """
                        SELECT id, next_no, user_id, `1`, `2`, `3`, `4`, `5`, `6`, create_at
                        FROM recommand
                        WHERE next_no = %s AND user_id = %s
                        ORDER BY id ASC
                        """
                        await cursor.execute(query, (draw_no, user_id))
                    else:
                        query = """
                        SELECT id, next_no, user_id, `1`, `2`, `3`, `4`, `5`, `6`, create_at
                        FROM recommand
                        WHERE next_no = %s
                        ORDER BY id ASC
                        """
                        await cursor.execute(query, (draw_no,))
                    
                    results = await cursor.fetchall()
                    
                    logger.info(f"조회된 결과 수: {len(results)} (draw_no: {draw_no}, user_id: {user_id})")
                    
                    if not results:
                        return []
                    
                    recommendations = []
                    for row in results:
                        try:
                            numbers = [row[f'{i}'] for i in range(1, 7)]
                            recommendations.append({
                                "id": row['id'],
                                "next_no": row['next_no'],
                                "user_id": row.get('user_id'),
                                "numbers": numbers,
                                "create_at": row['create_at']
                            })
                        except Exception as row_e:
                            logger.error(f"행 처리 중 오류: {row_e}, row: {row}")
                            continue
                    
                    return recommendations
                    
        except Exception as e:
            logger.error(f"예측 결과 조회 중 오류: {e}")
            raise DatabaseError(f"예측 결과 조회 중 오류: {e}")
            
    @staticmethod
    async def delete_recommendation(rec_id: int, user_id: int) -> bool:
        """예측 조합 1건 삭제 (본인 소유만 삭제 가능)

        Args:
            rec_id: recommand 테이블 PK
            user_id: 텔레그램 사용자 ID (소유자 검증용)

        Returns:
            삭제 성공 여부
        """
        query = "DELETE FROM recommand WHERE id = %s AND user_id = %s"

        try:
            rowcount = await AsyncDatabaseConnector.execute_query(
                query, (rec_id, user_id), fetch=False
            )
        except Exception as e:
            logger.error(f"예측 삭제 중 오류: {e}")
            raise DatabaseError(f"예측 삭제 중 오류: {e}")

        if not rowcount:
            logger.warning(f"삭제할 예측 없음 (id={rec_id}, user_id={user_id})")
            return False

        logger.info(f"예측 삭제 성공 (id={rec_id}, user_id={user_id})")
        return True

    @staticmethod
    async def get_scored_predictions() -> List[Dict[str, Any]]:
        """당첨 결과가 이미 나온 예측 전체 조회 (적중 통계용)

        Returns:
            [{"user_id", "numbers", "winning", "bonus"}, ...]
        """
        query = """
        SELECT r.user_id,
               r.`1` AS p1, r.`2` AS p2, r.`3` AS p3, r.`4` AS p4, r.`5` AS p5, r.`6` AS p6,
               d.`1` AS w1, d.`2` AS w2, d.`3` AS w3, d.`4` AS w4, d.`5` AS w5, d.`6` AS w6,
               d.bonus
        FROM recommand r
        JOIN result d ON d.no = r.next_no
        """

        try:
            rows = await AsyncDatabaseConnector.execute_query(query)
        except Exception as e:
            logger.error(f"적중 통계 조회 중 오류: {e}")
            raise DatabaseError(f"적중 통계 조회 중 오류: {e}")

        if not rows:
            logger.info("채점 가능한 예측이 없습니다")
            return []

        logger.info(f"채점 가능한 예측 {len(rows)}건 조회 성공")
        return [
            {
                "user_id": row["user_id"],
                "numbers": [row[f"p{i}"] for i in range(1, 7)],
                "winning": [row[f"w{i}"] for i in range(1, 7)],
                "bonus": row["bonus"],
            }
            for row in rows
        ]

    @classmethod
    async def execute_raw_query(cls, query: str, params: tuple = None):
        """임의의 쿼리 실행 (디버깅용)"""
        try:
            pool = await AsyncDatabaseConnector.get_pool()

            async with pool.acquire() as conn:
                # 호출처가 결과를 딕셔너리로 접근하므로 DictCursor 사용
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(query, params or ())
                    results = await cursor.fetchall()
                    return results

        except Exception as e:
            logger.error(f"쿼리 실행 중 오류: {e}")
            raise DatabaseError(f"쿼리 실행 중 오류: {e}")