# api/routers/scheduler.py
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, List, Any, Optional

from api.dependencies import get_async_data_service, get_async_prediction_service
from services.data_service import AsyncDataService
from services.prediction_service import AsyncPredictionService
from services.scheduler_service import PredictionScheduler
from services.slack_service import SlackNotifier
from utils.exceptions import SchedulerError, SlackNotificationError

router = APIRouter()
logger = logging.getLogger("lotto_prediction")

# 전역 스케줄러 객체 (싱글톤)
_scheduler: Optional[PredictionScheduler] = None

# 스케줄러 인스턴스 설정 및 획득 함수
def set_scheduler_instance(scheduler: PredictionScheduler) -> None:
    """전역 스케줄러 인스턴스 설정"""
    global _scheduler
    _scheduler = scheduler
    logger.info("스케줄러 인스턴스가 전역적으로 설정되었습니다.")

def get_scheduler_instance() -> Optional[PredictionScheduler]:
    """전역 스케줄러 인스턴스 획득"""
    return _scheduler

# 스케줄러 객체 의존성 함수 - 간소화
def get_scheduler() -> PredictionScheduler:
    """스케줄러 의존성 함수"""
    if _scheduler is None:
        # 이 시점에서 스케줄러가 없다면 오류
        logger.error("스케줄러 인스턴스가 초기화되지 않았습니다.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="스케줄러 서비스가 초기화되지 않았습니다."
        )
    return _scheduler

# 스케줄러 객체 가져오기
def get_scheduler(
    data_service: AsyncDataService = Depends(get_async_data_service),
    prediction_service: AsyncPredictionService = Depends(get_async_prediction_service)
) -> PredictionScheduler:
    global _scheduler
    if _scheduler is None:
        try:
            slack_notifier = SlackNotifier()
            _scheduler = PredictionScheduler(
                data_service=data_service,
                prediction_service=prediction_service,
                slack_notifier=slack_notifier
            )
        except Exception as e:
            logger.exception(f"스케줄러 초기화 실패: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"스케줄러 초기화 실패: {str(e)}"
            )
    return _scheduler


# 응답 모델
class SchedulerStatusResponse(BaseModel):
    status: str
    running: bool
    next_runs: Optional[Dict[str, str]] = None
    message: str


class ManualPredictionRequest(BaseModel):
    count: int = 5


class ManualPredictionResponse(BaseModel):
    success: bool
    message: str
    predictions: Optional[List[Dict[str, Any]]] = None


@router.post("/scheduler/start", response_model=SchedulerStatusResponse)
async def start_scheduler(scheduler: PredictionScheduler = Depends(get_scheduler)):
    """예측 스케줄러 시작"""
    try:
        if scheduler.running:
            return SchedulerStatusResponse(
                status="already_running",
                running=True,
                next_runs=scheduler.get_next_run_times(),
                message="스케줄러가 이미 실행 중입니다."
            )

        # 비동기로 스케줄러 시작
        await scheduler.start()

        return SchedulerStatusResponse(
            status="started",
            running=True,
            next_runs=scheduler.get_next_run_times(),
            message="스케줄러가 시작되었습니다."
        )

    except SchedulerError as e:
        logger.error(f"스케줄러 시작 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"스케줄러 시작 실패: {str(e)}"
        )


@router.post("/scheduler/stop", response_model=SchedulerStatusResponse)
def stop_scheduler(scheduler: PredictionScheduler = Depends(get_scheduler)):
    """예측 스케줄러 중지"""
    try:
        if not scheduler.running:
            return SchedulerStatusResponse(
                status="not_running",
                running=False,
                message="스케줄러가 실행 중이 아닙니다."
            )

        scheduler.stop()
        return SchedulerStatusResponse(
            status="stopped",
            running=False,
            message="스케줄러가 중지되었습니다."
        )

    except SchedulerError as e:
        logger.error(f"스케줄러 중지 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"스케줄러 중지 실패: {str(e)}"
        )


@router.get("/scheduler/status", response_model=SchedulerStatusResponse)
def get_scheduler_status(scheduler: PredictionScheduler = Depends(get_scheduler)):
    """예측 스케줄러 상태 조회"""
    try:
        if scheduler.running:
            return SchedulerStatusResponse(
                status="running",
                running=True,
                next_runs=scheduler.get_next_run_times(),
                message="스케줄러가 실행 중입니다."
            )
        else:
            return SchedulerStatusResponse(
                status="stopped",
                running=False,
                message="스케줄러가 중지되었습니다."
            )

    except Exception as e:
        logger.error(f"스케줄러 상태 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"스케줄러 상태 조회 실패: {str(e)}"
        )


# 예측 실행은 비동기 작업이므로 async 유지
@router.post("/scheduler/predict-now", response_model=ManualPredictionResponse)
async def run_prediction_now(
        request: ManualPredictionRequest,
        scheduler: PredictionScheduler = Depends(get_scheduler)
):
    """예측 작업 즉시 실행 (수동 트리거)"""
    try:
        predictions = await scheduler.run_prediction_now(count=request.count)

        if predictions:
            return ManualPredictionResponse(
                success=True,
                message=f"{len(predictions)}개 예측 생성 및 슬랙 알림 전송 완료",
                predictions=predictions
            )
        else:
            return ManualPredictionResponse(
                success=False,
                message="예측 생성 또는 슬랙 알림 전송 실패",
                predictions=None
            )

    except SlackNotificationError as e:
        logger.error(f"슬랙 알림 전송 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"슬랙 알림 전송 실패: {str(e)}"
        )

    except Exception as e:
        logger.exception(f"수동 예측 실행 중 오류 발생: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"수동 예측 실행 실패: {str(e)}"
        )