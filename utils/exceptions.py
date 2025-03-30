# utils/exceptions.py
class LottoPredictionError(Exception):
    """로또 예측 시스템의 기본 예외 클래스"""
    def __init__(self, message, original_error=None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)

class DatabaseError(LottoPredictionError):
    """데이터베이스 관련 오류"""
    pass

class DataLoadError(LottoPredictionError):
    """데이터 로드 오류"""
    pass

class AnalysisError(LottoPredictionError):
    """데이터 분석 오류"""
    pass

class PredictionGenerationError(LottoPredictionError):
    """예측 생성 오류"""
    pass

class APIServiceError(LottoPredictionError):
    """외부 API 서비스(Anthropic 등) 호출 오류"""
    pass

class ConfigurationError(LottoPredictionError):
    """설정 오류"""
    pass

class ValidationError(LottoPredictionError):
    """입력 데이터 유효성 검증 오류"""
    pass