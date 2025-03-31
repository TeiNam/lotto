# api/routers/lottery.py
import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional, Dict, Any

from services.lottery_service import LotteryService
from utils.exceptions import DatabaseError

router = APIRouter()
logger = logging.getLogger("lotto_prediction")


# 응답 모델
class LotteryUpdateResponse(BaseModel):
    success: bool
    message: str
    draw_no: Optional[int] = None
    draw_date: Optional[str] = None
    numbers: Optional[list] = None


class DrawNoRequest(BaseModel):
    draw_no: int


@router.post("/lottery/update-latest", response_model=LotteryUpdateResponse)
async def update_latest_draw():
    """최신 회차 로또 당첨 정보 업데이트"""
    try:
        success = await LotteryService.update_latest_draw()

        if success:
            return LotteryUpdateResponse(
                success=True,
                message="최신 로또 당첨 정보 업데이트 성공",
                draw_no=None  # 간단한 응답을 위해 번호 정보 생략
            )
        else:
            return LotteryUpdateResponse(
                success=False,
                message="최신 로또 당첨 정보가 아직 발표되지 않았거나 API 오류 발생"
            )

    except Exception as e:
        logger.exception(f"당첨 정보 업데이트 중 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"당첨 정보 업데이트 실패: {str(e)}"
        )


@router.post("/lottery/update", response_model=LotteryUpdateResponse)
async def update_specific_draw(request: DrawNoRequest):
    """특정 회차 로또 당첨 정보 업데이트"""
    try:
        # 회차 번호 유효성 검증
        if request.draw_no < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="유효하지 않은 회차 번호입니다"
            )

        # 특정 회차 당첨 정보 조회 및 저장
        success = await LotteryService.save_draw_result(request.draw_no)

        if success:
            # 성공 시 상세 정보 조회
            data = await LotteryService.fetch_draw_result(request.draw_no)

            numbers = [
                data.get("drwtNo1"),
                data.get("drwtNo2"),
                data.get("drwtNo3"),
                data.get("drwtNo4"),
                data.get("drwtNo5"),
                data.get("drwtNo6")
            ]

            return LotteryUpdateResponse(
                success=True,
                message=f"{request.draw_no}회차 로또 당첨 정보 업데이트 성공",
                draw_no=request.draw_no,
                draw_date=data.get("drwNoDate"),
                numbers=sorted(numbers)
            )
        else:
            return LotteryUpdateResponse(
                success=False,
                message=f"{request.draw_no}회차 로또 당첨 정보가 발표되지 않았거나 API 오류 발생",
                draw_no=request.draw_no
            )

    except HTTPException:
        raise

    except DatabaseError as e:
        logger.error(f"데이터베이스 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="데이터베이스 서비스를 일시적으로 사용할 수 없습니다. 잠시 후 다시 시도해주세요."
        )

    except Exception as e:
        logger.exception(f"당첨 정보 업데이트 중 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"당첨 정보 업데이트 실패: {str(e)}"
        )