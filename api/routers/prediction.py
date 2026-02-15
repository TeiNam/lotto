# api/routers/prediction.py
import logging
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import (
    get_async_data_service,
    get_simplified_prediction_service,
)
from api.schemas.prediction import (
    PredictionRequest,
    PredictionResponse,
    PredictionResult,
    PerformanceMetrics,
    DrawResultResponse,
    DrawResultRequest
)
from database.connector import AsyncDatabaseConnector
from database.repositories.lotto_repository import AsyncLottoRepository
from services.data_service import AsyncDataService
from services.simplified_prediction_service import SimplifiedPredictionService
from utils.exceptions import (
    DatabaseError, DataLoadError,
    PredictionGenerationError, ValidationError
)

router = APIRouter()
logger = logging.getLogger("lotto_prediction")


@router.post("/predict", response_model=PredictionResponse, status_code=status.HTTP_200_OK)
async def predict_lotto_numbers(
        request: PredictionRequest,
        data_service: AsyncDataService = Depends(get_async_data_service),
        prediction_service: SimplifiedPredictionService = Depends(get_simplified_prediction_service),
):
    """로또 번호 예측 API - 완전 랜덤 생성 방식

    과거 당첨 번호와의 중복은 자동으로 방지됩니다.
    """
    start_time = time.time()
    logger.info(f"로또 예측 시작 (요청 예측 개수: {request.count})")

    try:
        # 최신 회차 정보
        try:
            last_draw_data = await AsyncLottoRepository.get_last_draw()
            if not last_draw_data:
                raise DataLoadError("최근 회차 데이터를 찾을 수 없습니다")

            last_draw_no = last_draw_data["no"]
            last_draw_numbers = [
                last_draw_data[str(i)] for i in range(1, 7)
            ]
            last_draw_date = last_draw_data["create_at"]

        except DatabaseError as e:
            logger.error(f"데이터베이스 오류: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="데이터베이스 서비스를 일시적으로 사용할 수 없습니다."
            )

        # 예측 생성
        try:
            predictions = await prediction_service.generate_predictions(
                num_predictions=request.count
            )
            if not predictions:
                raise PredictionGenerationError("예측 결과가 비어있습니다")

        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except PredictionGenerationError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="예측 생성에 실패했습니다"
            )

        prediction_results = [
            PredictionResult(
                combination=pred.combination,
                score=pred.score,
                common_with_last=pred.common_with_last
            )
            for pred in predictions
        ]

        # DB 저장
        next_draw_no = last_draw_no + 1
        try:
            success_count = 0
            for pred in predictions:
                success = await AsyncLottoRepository.save_recommendation(
                    numbers=pred.combination,
                    next_no=next_draw_no
                )
                if success:
                    success_count += 1

            logger.info(f"예측 결과 {success_count}/{len(predictions)}개 저장 완료")
        except Exception as e:
            logger.warning(f"예측 결과 저장 중 오류: {e}")

        elapsed_time = time.time() - start_time

        return PredictionResponse(
            predictions=prediction_results,
            last_draw={
                "draw_no": last_draw_no,
                "numbers": last_draw_numbers,
                "draw_date": last_draw_date.isoformat() if hasattr(last_draw_date, 'isoformat') else str(last_draw_date)
            },
            next_draw_no=next_draw_no,
            analysis_summary={
                "method": "random",
                "description": "완전 랜덤 생성 방식",
            },
            performance_metrics=PerformanceMetrics(
                elapsed_time=elapsed_time,
                total_tokens=0,
                prompt_tokens=0,
                completion_tokens=0,
                api_calls=0,
                estimated_cost=0.0
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"예상치 못한 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="내부 서버 오류가 발생했습니다."
        )


@router.post("/results", response_model=DrawResultResponse, status_code=status.HTTP_201_CREATED)
async def save_draw_result(request: DrawResultRequest):
    """로또 당첨 결과 저장 API"""
    logger.info(f"당첨 결과 저장 요청 (회차: {request.draw_no})")

    try:
        sorted_numbers = sorted(request.numbers)
        success = await AsyncLottoRepository.save_draw_result(
            draw_no=request.draw_no,
            numbers=sorted_numbers
        )

        if success:
            logger.info(f"당첨 결과 저장 성공 (회차: {request.draw_no})")
            return DrawResultResponse(
                success=True,
                draw_no=request.draw_no,
                numbers=sorted_numbers,
                message="당첨 결과가 성공적으로 저장되었습니다."
            )
        else:
            return DrawResultResponse(
                success=False,
                draw_no=request.draw_no,
                numbers=sorted_numbers,
                message="당첨 결과 저장에 실패했습니다. 이미 존재하는 회차일 수 있습니다."
            )

    except DatabaseError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="데이터베이스 서비스를 일시적으로 사용할 수 없습니다."
        )
    except Exception as e:
        logger.exception(f"당첨 결과 저장 중 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="내부 서버 오류가 발생했습니다."
        )


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """API 헬스 체크"""
    try:
        await AsyncDatabaseConnector.get_pool()
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"헬스 체크 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="시스템이 현재 이용 불가능합니다"
        )
