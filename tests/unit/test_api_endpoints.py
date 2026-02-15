"""API 엔드포인트 단위 테스트

단순화된 예측 API 엔드포인트의 동작을 검증합니다.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime

from api.main import app
from models.prediction import LottoPrediction
from utils.exceptions import ValidationError, PredictionGenerationError


# TestClient 생성
client = TestClient(app)


class TestSimplifiedPredictionEndpoint:
    """단순화된 예측 엔드포인트 테스트"""
    
    @pytest.mark.asyncio
    async def test_predict_simple_success(self):
        """정상적인 예측 요청 테스트"""
        # Mock 설정
        with patch('api.routers.prediction.AsyncLottoRepository') as mock_repo, \
             patch('api.routers.prediction.get_simplified_prediction_service') as mock_service_dep:
            
            # Mock 데이터 설정 - async 메서드는 AsyncMock 사용
            mock_repo.get_last_draw = AsyncMock(return_value={
                "no": 1165,
                "1": 1, "2": 5, "3": 12, "4": 23, "5": 34, "6": 45,
                "create_at": datetime(2024, 1, 15)
            })
            
            mock_repo.save_recommendation = AsyncMock(return_value=True)
            
            # Mock 예측 서비스
            mock_service = AsyncMock()
            mock_predictions = [
                LottoPrediction(combination=[3, 12, 23, 28, 35, 42], score=0.0, common_with_last=0),
                LottoPrediction(combination=[5, 14, 19, 27, 33, 41], score=0.0, common_with_last=0),
            ]
            mock_service.generate_predictions.return_value = mock_predictions
            mock_service_dep.return_value = mock_service
            
            # API 호출
            response = client.post("/api/predict", json={"count": 2})
            
            # 검증
            assert response.status_code == 200
            data = response.json()
            
            assert "predictions" in data
            assert len(data["predictions"]) == 2
            assert "last_draw" in data
            assert data["last_draw"]["draw_no"] == 1165
            assert "next_draw_no" in data
            assert data["next_draw_no"] == 1166
            assert "performance_metrics" in data
    
    @pytest.mark.asyncio
    async def test_predict_simple_invalid_count(self):
        """유효하지 않은 예측 개수 테스트"""
        # count가 범위를 벗어난 경우
        response = client.post("/api/predict", json={"count": 0})
        assert response.status_code == 422  # Validation error
        
        response = client.post("/api/predict", json={"count": 21})
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_predict_simple_database_error(self):
        """데이터베이스 오류 처리 테스트"""
        with patch('api.routers.prediction.AsyncLottoRepository') as mock_repo:
            # 데이터베이스 오류 시뮬레이션
            from utils.exceptions import DatabaseError
            mock_repo.get_last_draw.side_effect = DatabaseError("Connection failed")
            
            response = client.post("/api/predict", json={"count": 5})
            
            assert response.status_code == 503
            assert "데이터베이스" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_predict_simple_prediction_generation_error(self):
        """예측 생성 실패 테스트"""
        with patch('api.routers.prediction.AsyncLottoRepository') as mock_repo, \
             patch('api.dependencies.SimplifiedPredictionService') as mock_service_class:
            
            # Mock 데이터 설정
            mock_repo.get_last_draw = AsyncMock(return_value={
                "no": 1165,
                "1": 1, "2": 5, "3": 12, "4": 23, "5": 34, "6": 45,
                "create_at": datetime(2024, 1, 15)
            })
            
            # 예측 생성 실패 시뮬레이션
            mock_service = AsyncMock()
            mock_service.generate_predictions = AsyncMock(
                side_effect=PredictionGenerationError("최대 재시도 횟수 초과")
            )
            mock_service_class.return_value = mock_service
            
            response = client.post("/api/predict", json={"count": 5})
            
            assert response.status_code == 500
            assert "예측 생성" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_predict_simple_graceful_degradation_save_failure(self):
        """저장 실패 시 Graceful Degradation 테스트"""
        with patch('api.routers.prediction.AsyncLottoRepository') as mock_repo, \
             patch('api.routers.prediction.get_simplified_prediction_service') as mock_service_dep:
            
            # Mock 데이터 설정
            mock_repo.get_last_draw = AsyncMock(return_value={
                "no": 1165,
                "1": 1, "2": 5, "3": 12, "4": 23, "5": 34, "6": 45,
                "create_at": datetime(2024, 1, 15)
            })
            
            # 저장 실패 시뮬레이션
            mock_repo.save_recommendation = AsyncMock(return_value=False)
            
            # Mock 예측 서비스
            mock_service = AsyncMock()
            mock_predictions = [
                LottoPrediction(combination=[3, 12, 23, 28, 35, 42], score=0.0, common_with_last=0),
            ]
            mock_service.generate_predictions.return_value = mock_predictions
            mock_service_dep.return_value = mock_service
            
            # API 호출
            response = client.post("/api/predict", json={"count": 1})
            
            # 저장 실패해도 예측 결과는 반환되어야 함
            assert response.status_code == 200
            data = response.json()
            assert len(data["predictions"]) == 1
    

class TestHealthCheckEndpoint:
    """헬스 체크 엔드포인트 테스트"""
    
    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """정상적인 헬스 체크 테스트"""
        with patch('api.routers.prediction.AsyncDatabaseConnector') as mock_connector:
            mock_connector.get_pool = AsyncMock(return_value=MagicMock())
            
            response = client.get("/api/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["database"] == "connected"
            assert "timestamp" in data
    
    @pytest.mark.asyncio
    async def test_health_check_database_failure(self):
        """데이터베이스 연결 실패 시 헬스 체크 테스트"""
        with patch('api.routers.prediction.AsyncDatabaseConnector') as mock_connector:
            mock_connector.get_pool.side_effect = Exception("Connection failed")
            
            response = client.get("/api/health")
            
            assert response.status_code == 503
            assert "이용 불가능" in response.json()["detail"]


class TestDrawResultEndpoint:
    """당첨 결과 저장 엔드포인트 테스트"""
    
    @pytest.mark.asyncio
    async def test_save_draw_result_success(self):
        """정상적인 당첨 결과 저장 테스트"""
        with patch('api.routers.prediction.AsyncLottoRepository') as mock_repo:
            mock_repo.save_draw_result = AsyncMock(return_value=True)
            
            response = client.post(
                "/api/results",
                json={
                    "draw_no": 1166,
                    "numbers": [1, 15, 19, 23, 28, 42]
                }
            )
            
            assert response.status_code == 201
            data = response.json()
            assert data["success"] is True
            assert data["draw_no"] == 1166
            assert len(data["numbers"]) == 6
    
    @pytest.mark.asyncio
    async def test_save_draw_result_invalid_numbers(self):
        """유효하지 않은 번호로 저장 시도 테스트"""
        # 번호가 6개가 아닌 경우
        response = client.post(
            "/api/results",
            json={
                "draw_no": 1166,
                "numbers": [1, 15, 19, 23, 28]  # 5개만
            }
        )
        assert response.status_code == 422
        
        # 중복 번호가 있는 경우
        response = client.post(
            "/api/results",
            json={
                "draw_no": 1166,
                "numbers": [1, 1, 19, 23, 28, 42]  # 1이 중복
            }
        )
        assert response.status_code == 422
        
        # 범위를 벗어난 번호
        response = client.post(
            "/api/results",
            json={
                "draw_no": 1166,
                "numbers": [1, 15, 19, 23, 28, 46]  # 46은 범위 초과
            }
        )
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_save_draw_result_duplicate_draw_no(self):
        """이미 존재하는 회차 저장 시도 테스트"""
        with patch('api.routers.prediction.AsyncLottoRepository') as mock_repo:
            mock_repo.save_draw_result = AsyncMock(return_value=False)
            
            response = client.post(
                "/api/results",
                json={
                    "draw_no": 1165,
                    "numbers": [1, 15, 19, 23, 28, 42]
                }
            )
            
            assert response.status_code == 201  # 여전히 201이지만
            data = response.json()
            assert data["success"] is False  # success는 False
            assert "이미 존재" in data["message"]
