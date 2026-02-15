# api/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import logging
from config.settings import verify_required_env_vars
from database.connector import AsyncDatabaseConnector

from api.routers import prediction, lottery

logger = logging.getLogger("lotto_prediction")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프스팬 컨텍스트 매니저"""
    logger.info("애플리케이션 시작 중...")

    verify_required_env_vars()

    try:
        pool = await AsyncDatabaseConnector.get_pool()
        logger.info("데이터베이스 연결 성공")
    except Exception as e:
        logger.error(f"데이터베이스 연결 실패: {e}")

    logger.info("애플리케이션 초기화 완료")

    yield

    logger.info("애플리케이션 종료 중...")
    await AsyncDatabaseConnector.close_pool()
    logger.info("모든 리소스가 정상적으로 종료되었습니다.")


app = FastAPI(
    title="Lotto Prediction API",
    description="로또 번호 예측 시스템 API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(prediction.router, prefix="/api", tags=["prediction"])
app.include_router(lottery.router, prefix="/api", tags=["lottery"])


@app.get("/", tags=["root"])
async def root():
    """API 루트 엔드포인트"""
    return {
        "message": "로또 예측 시스템 API",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }


@app.get("/health", tags=["health"])
async def health_check():
    """헬스체크 엔드포인트"""
    try:
        pool = await AsyncDatabaseConnector.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT 1")
                await cursor.fetchone()

        return {
            "status": "healthy",
            "database": "connected",
            "service": "lotto-prediction-api"
        }
    except Exception as e:
        logger.error(f"헬스체크 실패: {e}")
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
