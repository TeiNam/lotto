# api/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import logging
from config.settings import verify_required_env_vars
from database.connector import AsyncDatabaseConnector

from api.routers import prediction, scheduler, lottery

# 로깅 설정
logger = logging.getLogger("lotto_prediction")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    애플리케이션 라이프스팬 컨텍스트 매니저
    - 시작 시 리소스 초기화
    - 종료 시 리소스 정리
    """
    # 시작 시 실행
    logger.info("애플리케이션 시작 중...")

    # 환경 변수 검증
    verify_required_env_vars()

    # 데이터베이스 연결 테스트
    try:
        pool = await AsyncDatabaseConnector.get_pool()
        logger.info("데이터베이스 연결 성공")
    except Exception as e:
        logger.error(f"데이터베이스 연결 실패: {e}")

    # 스케줄러 초기화 및 시작
    try:
        # 필요한 서비스들을 직접 생성
        from services.data_service import AsyncDataService
        from services.prediction_service import AsyncPredictionService
        # TODO: SlackNotifier 제거됨 - Telegram으로 전환 예정
        # from services.slack_service import SlackNotifier
        from services.scheduler_service import PredictionScheduler

        # 서비스 인스턴스 생성
        data_service = AsyncDataService()
        prediction_service = AsyncPredictionService(data_service)
        # TODO: SlackNotifier 제거됨 - Telegram으로 전환 예정
        # slack_notifier = SlackNotifier()

        # 스케줄러 초기화
        # TODO: slack_notifier 파라미터 제거됨
        scheduler = PredictionScheduler(
            data_service=data_service,
            prediction_service=prediction_service,
            slack_notifier=None  # 임시로 None 전달
        )

        # 전역 변수로 스케줄러 인스턴스 설정 (api/routers/scheduler.py에서 접근 가능하도록)
        from api.routers.scheduler import set_scheduler_instance
        set_scheduler_instance(scheduler)

        # 스케줄러 시작 (비동기)
        await scheduler.start()
        logger.info("예측 스케줄러 자동 시작됨")
    except Exception as e:
        logger.exception(f"스케줄러 초기화 실패: {e}")
        logger.info("스케줄러 없이 애플리케이션 실행 중...")

    logger.info("애플리케이션 초기화 완료")

    yield  # FastAPI 애플리케이션 실행

    # 종료 시 실행
    logger.info("애플리케이션 종료 중...")

    # 스케줄러 중지
    try:
        from api.routers.scheduler import get_scheduler_instance
        scheduler_instance = get_scheduler_instance()
        if scheduler_instance and scheduler_instance.running:
            scheduler_instance.stop()
            logger.info("예측 스케줄러 정상 종료됨")
    except Exception as e:
        logger.error(f"스케줄러 종료 실패: {e}")

    # 데이터베이스 연결 풀 종료
    await AsyncDatabaseConnector.close_pool()

    logger.info("모든 리소스가 정상적으로 종료되었습니다.")


app = FastAPI(
    title="Lotto Prediction API",
    description="로또 번호 예측 시스템 API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션 환경에서는 특정 도메인으로 제한하세요
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(prediction.router, prefix="/api", tags=["prediction"])
app.include_router(scheduler.router, prefix="/api", tags=["scheduler"])
app.include_router(lottery.router, prefix="/api", tags=["lottery"])

@app.get("/", tags=["root"])
async def root():
    """API 루트 엔드포인트"""
    return {
        "message": "로또 예측 시스템 API에 오신 것을 환영합니다!",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)