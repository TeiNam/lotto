#!/usr/bin/env python3
# cli_runner.py - CLI 실행 스크립트
import os
import sys
import logging
from config.logging_config import setup_logging
from cli.commands import CLI


def main():
    """CLI 인터페이스 실행을 위한 진입점"""
    # 로깅 설정
    logger = setup_logging()
    logger.info("로또 예측 시스템 CLI 시작")

    try:
        # CLI 실행
        cli = CLI()
        cli.run()
    except KeyboardInterrupt:
        logger.info("사용자에 의해 종료됨")
    except Exception as e:
        logger.exception(f"예상치 못한 오류 발생: {e}")
    finally:
        logger.info("로또 예측 시스템 CLI 종료")


if __name__ == "__main__":
    main()