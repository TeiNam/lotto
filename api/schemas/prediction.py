from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field, field_validator


class PredictionRequest(BaseModel):
    """예측 요청 모델"""
    count: int = Field(5, description="생성할 예측 조합 개수")

    @field_validator("count")
    @classmethod
    def validate_count(cls, v):
        if v < 1 or v > 20:
            raise ValueError("예측 개수는 1~20 사이여야 합니다")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "count": 5
            }
        }
    }


class PredictionResult(BaseModel):
    """예측 결과 항목"""
    combination: List[int] = Field(..., description="예측 번호 조합")
    score: float = Field(..., description="예측 점수")
    common_with_last: int = Field(..., description="이전 회차와 공통 번호 개수")

    def format_numbers(self) -> str:
        """번호 조합을 보기 좋게 형식화"""
        return ", ".join(str(n) for n in sorted(self.combination))


class PerformanceMetrics(BaseModel):
    """API 성능 및 사용량 지표"""
    elapsed_time: float = Field(..., description="총 소요 시간(초)")
    total_tokens: int = Field(0, description="사용된 총 토큰 수")
    prompt_tokens: int = Field(0, description="프롬프트 토큰 수")
    completion_tokens: int = Field(0, description="응답 토큰 수")
    api_calls: int = Field(0, description="API 호출 횟수")
    estimated_cost: float = Field(0.0, description="예상 비용(USD)")


class PredictionResponse(BaseModel):
    """예측 응답 모델"""
    predictions: List[PredictionResult] = Field(..., description="예측 결과 목록")
    last_draw: Dict[str, Any] = Field(..., description="마지막 회차 정보")
    next_draw_no: int = Field(..., description="예측 대상 회차")
    analysis_summary: Dict[str, Any] = Field(..., description="분석 결과 요약")
    performance_metrics: PerformanceMetrics = Field(..., description="성능 및 사용량 지표")


class DrawResultRequest(BaseModel):
    """당첨 결과 저장 요청 모델"""
    draw_no: int = Field(..., description="회차 번호")
    numbers: List[int] = Field(..., description="당첨 번호 6개")
    bonus: Optional[int] = Field(None, description="보너스 번호")

    @field_validator("draw_no")
    @classmethod
    def validate_draw_no(cls, v):
        if v < 1:
            raise ValueError("회차 번호는 1 이상이어야 합니다")
        return v

    @field_validator("numbers")
    @classmethod
    def validate_numbers(cls, v):
        if len(v) != 6:
            raise ValueError("당첨 번호는 정확히 6개여야 합니다")

        if len(set(v)) != 6:
            raise ValueError("당첨 번호에 중복이 있습니다")

        if any(n < 1 or n > 45 for n in v):
            raise ValueError("모든 번호는 1~45 사이여야 합니다")

        return v

    @field_validator("bonus")
    @classmethod
    def validate_bonus(cls, v):
        if v is not None and (v < 1 or v > 45):
            raise ValueError("보너스 번호는 1~45 사이여야 합니다")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "draw_no": 1166,
                "numbers": [1, 15, 19, 23, 28, 42],
                "bonus": 7
            }
        }
    }


class DrawResultResponse(BaseModel):
    """당첨 결과 저장 응답 모델"""
    success: bool = Field(..., description="저장 성공 여부")
    draw_no: int = Field(..., description="저장된 회차 번호")
    numbers: List[int] = Field(..., description="저장된 당첨 번호")
    bonus: Optional[int] = Field(None, description="보너스 번호")
    message: str = Field(..., description="결과 메시지")