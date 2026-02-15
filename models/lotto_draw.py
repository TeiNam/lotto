# models/lotto_draw.py - 오류 처리 개선
from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple, Dict, Any
from utils.exceptions import ValidationError
import logging

logger = logging.getLogger("lotto_prediction")


@dataclass
class LottoDraw:
    """로또 당첨 번호 모델"""
    draw_no: int
    numbers: List[int]
    draw_date: datetime
    bonus: int = None

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]):
        """DB 결과에서 LottoDraw 객체 생성"""
        try:
            # 필수 필드 검증
            if 'no' not in row:
                raise ValidationError("회차 번호(no) 필드가 없습니다")

            for i in range(1, 7):
                if str(i) not in row:
                    raise ValidationError(f"{i}번 필드가 없습니다")

            # 번호 추출 및 검증
            numbers = []
            for i in range(1, 7):
                num = row[str(i)]
                if not isinstance(num, int):
                    raise ValidationError(f"{i}번 필드가 정수가 아닙니다: {num}")
                if num < 1 or num > 45:
                    raise ValidationError(f"{i}번 필드가 유효한 범위(1-45)를 벗어났습니다: {num}")
                numbers.append(num)

            # 중복 번호 검증
            if len(set(numbers)) != 6:
                raise ValidationError(f"중복된 번호가 있습니다: {numbers}")

            # 날짜 필드 검증
            if 'create_at' not in row:
                logger.warning(f"날짜 필드(create_at)가 없습니다. 현재 시간을 사용합니다. 회차: {row['no']}")
                draw_date = datetime.now()
            else:
                draw_date = row['create_at']
                if not isinstance(draw_date, datetime):
                    try:
                        draw_date = datetime.fromisoformat(str(draw_date))
                    except:
                        logger.warning(f"날짜 변환 실패. 현재 시간을 사용합니다. 회차: {row['no']}")
                        draw_date = datetime.now()

            return cls(
                draw_no=row['no'],
                numbers=numbers,
                draw_date=draw_date,
                bonus=row.get('bonus')
            )
        except ValidationError:
            # 검증 오류 전파
            raise
        except Exception as e:
            # 기타 오류는 ValidationError로 래핑
            logger.error(f"당첨 번호 객체 생성 오류: {e}")
            raise ValidationError(f"로또 당첨 데이터 변환 오류: {e}")

    def get_numbers_tuple(self) -> Tuple[int, ...]:
        """정렬된 번호 튜플 반환 (중복 확인용)"""
        return tuple(sorted(self.numbers))