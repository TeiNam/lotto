# api/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import logging
from config.settings import verify_required_env_vars
from database.connector import AsyncDatabaseConnector

from api.routers import prediction

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

    logger.info("애플리케이션 초기화 완료")

    yield  # FastAPI 애플리케이션 실행

    # 종료 시 실행
    logger.info("애플리케이션 종료 중...")

    # 데이터베이스 연결 풀 종료
    await AsyncDatabaseConnector.close_pool()

    logger.info("모든 리소스가 정상적으로 종료되었습니다.")


# FastAPI 앱 생성 (lifespan 컨텍스트 매니저 적용)
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