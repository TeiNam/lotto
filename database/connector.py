# database/connector.py
import aiomysql
import asyncio
import logging
from typing import List, Dict, Any, Optional
import time
from config.settings import DB_CONFIG
from utils.exceptions import DatabaseError

logger = logging.getLogger("lotto_prediction")


class AsyncDatabaseConnector:
    """비동기 데이터베이스 연결 관리"""

    _pool = None  # 연결 풀 싱글톤 인스턴스
    _max_retries = 3  # 최대 재시도 횟수
    _retry_delay = 1  # 재시도 간 지연 시간(초)

    @classmethod
    async def get_pool(cls):
        """비동기 커넥션 풀 가져오기 (필요시 생성)"""
        if cls._pool is None:
            retry_count = 0
            last_error = None

            while retry_count < cls._max_retries:
                try:
                    cls._pool = await aiomysql.create_pool(
                        host=DB_CONFIG["host"],
                        user=DB_CONFIG["user"],
                        password=DB_CONFIG["password"],
                        db=DB_CONFIG["database"],
                        port=DB_CONFIG.get("port", 3306),
                        charset='utf8mb4',
                        autocommit=True,
                        minsize=1,
                        maxsize=10,
                        echo=False
                    )
                    logger.info("데이터베이스 연결 풀 생성됨")
                    return cls._pool

                except (aiomysql.OperationalError, aiomysql.InternalError) as e:
                    retry_count += 1
                    last_error = e
                    logger.warning(f"데이터베이스 연결 실패 (시도 {retry_count}/{cls._max_retries}): {e}")

                    if retry_count < cls._max_retries:
                        # 지수 백오프 전략으로 지연 시간 증가
                        delay = cls._retry_delay * (2 ** (retry_count - 1))
                        logger.info(f"{delay}초 후 재시도...")
                        await asyncio.sleep(delay)

                except Exception as e:
                    # 재시도해도 도움이 되지 않는 오류 (설정 오류 등)
                    logger.error(f"데이터베이스 연결 치명적 오류: {e}")
                    raise DatabaseError(f"데이터베이스 연결 오류: {e}", original_error=e)

            # 최대 재시도 횟수를 초과한 경우
            logger.error(f"데이터베이스 연결 최대 재시도 횟수 초과: {last_error}")
            raise DatabaseError(f"데이터베이스 연결 실패: {last_error}", original_error=last_error)

        return cls._pool

    @classmethod
    async def close_pool(cls):
        """연결 풀 닫기"""
        if cls._pool is not None:
            cls._pool.close()
            await cls._pool.wait_closed()
            cls._pool = None
            logger.info("데이터베이스 연결 풀 종료됨")

    @classmethod
    async def execute_query(cls, query: str, params: tuple = None, fetch: bool = True) -> Optional[
        List[Dict[str, Any]]]:
        """비동기 쿼리 실행 및 결과 반환 (재시도 로직 포함)"""
        retry_count = 0
        last_error = None

        while retry_count < cls._max_retries:
            pool = await cls.get_pool()
            conn = None

            try:
                conn = await pool.acquire()
                cursor = await conn.cursor(aiomysql.DictCursor)

                await cursor.execute(query, params or ())

                if fetch:
                    result = await cursor.fetchall()
                    return result
                else:
                    return cursor.rowcount

            except (aiomysql.OperationalError, aiomysql.InternalError) as e:
                # 일시적 오류 - 재시도 가능
                retry_count += 1
                last_error = e
                logger.warning(f"쿼리 실행 실패 (시도 {retry_count}/{cls._max_retries}): {e}")
                logger.warning(f"쿼리: {query}, 파라미터: {params}")

                if retry_count < cls._max_retries:
                    delay = cls._retry_delay * (2 ** (retry_count - 1))
                    logger.info(f"{delay}초 후 재시도...")
                    await asyncio.sleep(delay)

            except Exception as e:
                # 재시도해도 도움이 되지 않는 오류
                logger.error(f"쿼리 실행 치명적 오류: {e}")
                logger.error(f"쿼리: {query}, 파라미터: {params}")
                raise DatabaseError(f"쿼리 실행 오류: {e}", original_error=e)

            finally:
                if conn:
                    pool.release(conn)

        # 최대 재시도 횟수를 초과한 경우
        logger.error(f"쿼리 실행 최대 재시도 횟수 초과: {last_error}")
        logger.error(f"쿼리: {query}, 파라미터: {params}")
        raise DatabaseError(f"쿼리 실행 실패: {last_error}", original_error=last_error)