"""Integration tests configuration

이 모듈은 통합 테스트를 위한 pytest fixtures를 제공합니다.
"""

import pytest
import pytest_asyncio
import asyncio
from database.connector import AsyncDatabaseConnector


@pytest_asyncio.fixture(scope="function", autouse=True)
async def reset_db_pool():
    """각 테스트 전후로 데이터베이스 연결 풀을 초기화합니다."""
    # 테스트 전: 기존 풀 정리
    await AsyncDatabaseConnector.close_pool()
    
    yield
    
    # 테스트 후: 풀 정리
    await AsyncDatabaseConnector.close_pool()
