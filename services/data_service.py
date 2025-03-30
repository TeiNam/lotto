# services/data_service.py - 오류 처리 개선
import logging
from typing import List, Set, Dict, Optional
from database.repositories.lotto_repository import AsyncLottoRepository
from models.lotto_draw import LottoDraw
from utils.exceptions import DataLoadError, ValidationError

logger = logging.getLogger("lotto_prediction")


class AsyncDataService:
    """비동기 로또 데이터 관리 서비스"""

    def __init__(self):
        self.draws = []
        self.existing_combinations = set()

    async def load_historical_data(self, start_no=601, end_no=None):
        """역대 당첨 데이터 로드 (비동기)"""
        # 입력 검증
        if start_no <= 0:
            logger.error(f"잘못된 시작 회차: {start_no}")
            raise ValidationError("시작 회차는 1 이상이어야 합니다")

        if end_no is not None and end_no < start_no:
            logger.error(f"잘못된 회차 범위: {start_no}-{end_no}")
            raise ValidationError("종료 회차는 시작 회차보다 크거나 같아야 합니다")

        # end_no가 None이면 최신 회차 조회
        if end_no is None:
            try:
                last_draw_data = await AsyncLottoRepository.get_last_draw()
                if last_draw_data:
                    end_no = last_draw_data["no"]
                else:
                    logger.error("최근 회차 정보를 가져오는데 실패했습니다")
                    return False
            except Exception as e:
                logger.error(f"최근 회차 조회 오류: {e}")
                # 데이터베이스 예외는 상위로 전달하여 처리
                raise

        try:
            raw_data = await AsyncLottoRepository.get_draws_by_range(start_no, end_no)

            if not raw_data:
                logger.error(f"역대 데이터 로드 실패 (범위: {start_no}-{end_no})")
                return False

            # 데이터 유효성 검증
            invalid_draws = []
            valid_draws = []

            for row in raw_data:
                try:
                    draw = LottoDraw.from_db_row(row)
                    valid_draws.append(draw)
                except Exception as e:
                    logger.warning(f"유효하지 않은 회차 데이터 (회차: {row.get('no')}): {e}")
                    invalid_draws.append(row.get('no'))

            if invalid_draws:
                logger.warning(f"유효하지 않은 회차 데이터 {len(invalid_draws)}개 건너뜀: {invalid_draws}")

            if not valid_draws:
                logger.error("유효한 회차 데이터가 없습니다")
                return False

            self.draws = valid_draws
            self.existing_combinations = {draw.get_numbers_tuple() for draw in self.draws}

            logger.info(f"역대 데이터 {len(self.draws)}개 로드 성공 (범위: {start_no}-{end_no})")
            return True

        except Exception as e:
            logger.error(f"데이터 로드 오류: {e}")
            # 데이터베이스 예외는 상위로 전달하여 처리
            raise

    def get_last_draw(self) -> Optional[LottoDraw]:
        """마지막 회차 데이터 반환"""
        if not self.draws:
            return None
        return self.draws[-1]

    def get_all_draws(self) -> List[LottoDraw]:
        """모든 당첨 데이터 반환"""
        return self.draws

    def get_existing_combinations(self) -> Set[tuple]:
        """기존 당첨 조합 집합 반환"""
        return self.existing_combinations

    def is_new_combination(self, numbers: List[int]) -> bool:
        """새로운 조합인지 확인"""
        try:
            if not numbers or len(numbers) != 6:
                logger.warning(f"유효하지 않은 번호 조합: {numbers}")
                return False

            return tuple(sorted(numbers)) not in self.existing_combinations
        except Exception as e:
            logger.error(f"조합 확인 중 오류: {e}")
            # 기본적으로 중복으로 간주
            return False