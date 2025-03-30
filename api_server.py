#!/usr/bin/env python3
# api_server.py - API 서버 실행 스크립트
import uvicorn
import logging
from config.logging_config import setup_logging


def main():
    """API 서버 실행을 위한 진입점"""
    # 로깅 설정
    logger = setup_logging()
    logger.info("로또 예측 시스템 API 서버 시작")

    # FastAPI 애플리케이션 실행
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()