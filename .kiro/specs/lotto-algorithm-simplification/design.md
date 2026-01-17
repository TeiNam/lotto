# Design Document: Lotto Algorithm Simplification

## Overview

이 설계는 로또 예측 시스템의 알고리즘을 복잡한 통계 분석에서 완전 랜덤 생성 방식으로 단순화합니다. 주요 목표는 코드 복잡도 감소, 외부 API 의존성 제거, 유지보수성 향상입니다.

### Design Goals

1. **단순성**: 복잡한 통계 알고리즘을 제거하고 순수 랜덤 생성으로 대체
2. **독립성**: Anthropic API 의존성 제거로 외부 서비스 장애 영향 최소화
3. **성능**: 단순한 로직으로 빠른 응답 시간 보장
4. **호환성**: 기존 API 인터페이스 유지로 클라이언트 영향 최소화
5. **신뢰성**: 중복 조합 방지로 사용자에게 유효한 예측 제공

## Architecture

### High-Level Architecture

```mermaid
graph TB
    Client[Client Application] --> API[FastAPI Endpoint]
    API --> PS[Prediction Service]
    PS --> RG[Random Generator]
    PS --> DC[Duplicate Checker]
    PS --> DS[Data Service]
    DC --> DS
    DS --> DB[(MySQL Database)]
    
    style PS fill:#e1f5ff
    style RG fill:#fff4e1
    style DC fill:#fff4e1
    style DS fill:#e8f5e9
```

### Component Layers

1. **API Layer**: FastAPI 엔드포인트 (변경 최소화)
2. **Service Layer**: 비즈니스 로직 (대폭 단순화)
3. **Data Layer**: 데이터베이스 접근 (유지)

### Removed Components

- `AnalysisService`: 모든 통계 분석 로직 제거
- `RAGService`: Anthropic API 호출 로직 제거
- 점수 계산 로직
- 베이지안 확률 계산
- 마르코프 체인 분석
- 빈도 분석
- Slack 알림 서비스

### New Components

- `RandomGenerator`: 완전 랜덤 번호 생성
- `DuplicateChecker`: 중복 조합 검증
- `SimplifiedPredictionService`: 단순화된 예측 서비스
- `TelegramNotifier`: Telegram 알림 서비스

## Components and Interfaces

### 1. Random Generator

**책임**: 완전 랜덤 로또 번호 조합 생성 및 극단적 패턴 필터링

```python
class RandomGenerator:
    """완전 랜덤 로또 번호 생성기"""
    
    def generate_combination(self) -> List[int]:
        """
        1-45 범위에서 6개의 고유한 숫자를 랜덤으로 선택
        극단적 패턴은 자동으로 필터링됨
        
        Returns:
            정렬된 6개 숫자 리스트 [n1, n2, n3, n4, n5, n6] (n1 < n2 < ... < n6)
        """
        pass
    
    def is_extreme_pattern(self, combination: List[int]) -> bool:
        """
        극단적 패턴 감지
        
        Args:
            combination: 검증할 6개 숫자 조합
            
        Returns:
            극단적 패턴이면 True, 정상이면 False
        """
        pass
```

**구현 세부사항**:
- `secrets.SystemRandom()` 사용 (암호학적으로 안전한 난수)
- `random.sample(range(1, 46), 6)` 로 중복 없이 선택
- 결과를 `sorted()` 로 정렬하여 반환
- 극단적 패턴 필터링 적용

**극단적 패턴 필터링 규칙**:
1. **연속 숫자 5개 이상**: [1,2,3,4,5,10] 같은 조합 거부
2. **등차수열**: 모든 간격이 동일하고 1보다 큰 경우 (예: [5,10,15,20,25,30]) 거부
3. **극단적 합계**: 합계가 80 미만 또는 200 초과인 경우 거부
4. **홀수만/짝수만**: 6개 모두 홀수 또는 모두 짝수인 경우 거부
5. **구간 편중**: 한 10개 단위 구간에 5개 이상 몰린 경우 거부

```python
def is_extreme_pattern(self, combination: List[int]) -> bool:
    """극단적 패턴 감지"""
    sorted_combo = sorted(combination)
    
    # 1. 연속 숫자 5개 이상 체크
    consecutive_count = 0
    max_consecutive = 0
    for i in range(5):
        if sorted_combo[i+1] - sorted_combo[i] == 1:
            consecutive_count += 1
            max_consecutive = max(max_consecutive, consecutive_count + 1)
        else:
            consecutive_count = 0
    if max_consecutive >= 5:
        return True
    
    # 2. 등차수열 체크 (모든 간격이 동일하고 1보다 큼)
    gaps = [sorted_combo[i+1] - sorted_combo[i] for i in range(5)]
    if len(set(gaps)) == 1 and gaps[0] > 1:
        return True
    
    # 3. 극단적 합계 체크
    total_sum = sum(combination)
    if total_sum < 80 or total_sum > 200:
        return True
    
    # 4. 홀수만 또는 짝수만 체크
    odd_count = sum(1 for n in combination if n % 2 == 1)
    if odd_count == 0 or odd_count == 6:
        return True
    
    # 5. 구간 편중 체크 (한 구간에 5개 이상)
    ranges = {
        "1-10": sum(1 for n in combination if 1 <= n <= 10),
        "11-20": sum(1 for n in combination if 11 <= n <= 20),
        "21-30": sum(1 for n in combination if 21 <= n <= 30),
        "31-40": sum(1 for n in combination if 31 <= n <= 40),
        "41-45": sum(1 for n in combination if 41 <= n <= 45),
    }
    if max(ranges.values()) >= 5:
        return True
    
    return False
```

### 2. Duplicate Checker

**책임**: 생성된 조합이 과거 당첨 번호와 중복되는지 검증

```python
class DuplicateChecker:
    """중복 조합 검증기"""
    
    def __init__(self, data_service: DataService):
        self.data_service = data_service
    
    async def is_duplicate(self, combination: List[int]) -> bool:
        """
        조합이 과거 당첨 번호와 중복되는지 확인
        
        Args:
            combination: 검증할 6개 숫자 조합
            
        Returns:
            중복이면 True, 아니면 False
        """
        pass
    
    async def is_new_combination(self, combination: List[int]) -> bool:
        """
        조합이 새로운(중복되지 않은) 조합인지 확인
        
        Args:
            combination: 검증할 6개 숫자 조합
            
        Returns:
            새로운 조합이면 True, 중복이면 False
        """
        pass
```

**구현 세부사항**:
- 데이터베이스에서 모든 과거 당첨 번호 조회
- 조합을 정렬된 문자열로 변환하여 비교 (예: "1,5,12,23,34,45")
- 효율성을 위해 당첨 번호를 Set으로 캐싱 고려

### 3. Simplified Prediction Service

**책임**: 예측 생성 오케스트레이션 (대폭 단순화)

```python
class SimplifiedPredictionService:
    """단순화된 예측 서비스"""
    
    def __init__(
        self,
        random_generator: RandomGenerator,
        duplicate_checker: DuplicateChecker,
        data_service: DataService
    ):
        self.random_generator = random_generator
        self.duplicate_checker = duplicate_checker
        self.data_service = data_service
        self.max_retries = 100  # 무한 루프 방지
    
    async def generate_predictions(
        self,
        num_predictions: int,
        user_id: Optional[int] = None
    ) -> List[LottoPrediction]:
        """
        요청된 개수만큼 예측 생성
        
        Args:
            num_predictions: 생성할 예측 개수 (1-20)
            user_id: 사용자 ID (선택)
            
        Returns:
            생성된 예측 리스트
            
        Raises:
            ValidationError: num_predictions가 유효하지 않은 경우
            PredictionGenerationError: 예측 생성 실패 시
        """
        pass
    
    async def _generate_single_prediction(self) -> List[int]:
        """
        중복되지 않은 단일 예측 생성
        
        Returns:
            유효한 6개 숫자 조합
            
        Raises:
            PredictionGenerationError: 최대 재시도 횟수 초과 시
        """
        pass
```

**알고리즘**:
```
for i in range(num_predictions):
    retry_count = 0
    while retry_count < max_retries:
        combination = random_generator.generate_combination()
        
        if not duplicate_checker.is_duplicate(combination):
            # 이미 생성된 조합과도 중복 확인
            if combination not in generated_combinations:
                generated_combinations.add(combination)
                predictions.append(combination)
                break
        
        retry_count += 1
    
    if retry_count >= max_retries:
        raise PredictionGenerationError("최대 재시도 횟수 초과")

return predictions
```

### 4. Data Service (유지)

**책임**: 데이터베이스 접근 (기존 유지)

```python
class DataService:
    """데이터베이스 접근 서비스"""
    
    async def get_all_winning_combinations(self) -> List[List[int]]:
        """
        모든 과거 당첨 번호 조회
        
        Returns:
            과거 당첨 번호 리스트
        """
        pass
    
    async def save_prediction(
        self,
        combination: List[int],
        user_id: Optional[int] = None
    ) -> int:
        """
        예측 결과를 recommand 테이블에 저장
        
        Args:
            combination: 저장할 조합
            user_id: 사용자 ID
            
        Returns:
            저장된 레코드의 ID
        """
        pass
```

### 5. API Endpoint (최소 변경)

**책임**: HTTP 요청 처리

```python
@router.post("/api/v1/predict")
async def predict_numbers(
    request: PredictionRequest,
    prediction_service: SimplifiedPredictionService = Depends(get_prediction_service)
) -> PredictionResponse:
    """
    로또 번호 예측 API
    
    Args:
        request: 예측 요청 (num_predictions)
        
    Returns:
        예측 결과 리스트
    """
    pass
```

### 6. Telegram Notifier

**책임**: Telegram을 통한 예측 결과 알림

```python
import aiohttp
from typing import List, Optional

class TelegramNotifier:
    """Telegram 알림 서비스"""
    
    def __init__(self, bot_token: str, chat_id: str):
        """
        Args:
            bot_token: Telegram Bot API 토큰
            chat_id: 메시지를 보낼 채팅방 ID
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
    
    async def send_predictions(
        self,
        predictions: List[List[int]],
        timestamp: Optional[str] = None
    ) -> bool:
        """
        예측 결과를 Telegram으로 전송
        
        Args:
            predictions: 예측 번호 리스트
            timestamp: 생성 시각 (선택)
            
        Returns:
            전송 성공 여부
        """
        pass
    
    def _format_message(
        self,
        predictions: List[List[int]],
        timestamp: Optional[str] = None
    ) -> str:
        """
        Telegram 메시지 포맷팅
        
        Args:
            predictions: 예측 번호 리스트
            timestamp: 생성 시각
            
        Returns:
            포맷된 메시지 문자열
        """
        pass
    
    async def _send_message(self, text: str) -> bool:
        """
        Telegram API를 통해 메시지 전송
        
        Args:
            text: 전송할 메시지
            
        Returns:
            전송 성공 여부
        """
        pass
```

**메시지 포맷 예시**:
```
🎰 로또 예측 결과 🎰

생성 시각: 2024-01-15 10:30:00

1️⃣ [3, 12, 23, 28, 35, 42]
2️⃣ [5, 14, 19, 27, 33, 41]
3️⃣ [7, 11, 22, 29, 36, 44]

행운을 빕니다! 🍀
```

**구현 세부사항**:
- `aiohttp`를 사용한 비동기 HTTP 요청
- Telegram Bot API의 `sendMessage` 엔드포인트 사용
- 에러 발생 시 로깅만 하고 예측 생성은 계속 진행
- 환경 변수에서 bot_token과 chat_id 로드
- 메시지 길이 제한 고려 (Telegram 최대 4096자)

## Data Models

### Request/Response Models

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class PredictionRequest(BaseModel):
    """예측 요청 모델"""
    num_predictions: int = Field(
        default=5,
        ge=1,
        le=20,
        description="생성할 예측 개수"
    )

class LottoPrediction(BaseModel):
    """로또 예측 모델"""
    combination: List[int] = Field(
        description="6개 숫자 조합",
        min_length=6,
        max_length=6
    )
    generated_at: datetime = Field(
        default_factory=datetime.now,
        description="생성 시각"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "combination": [3, 12, 23, 28, 35, 42],
                "generated_at": "2024-01-15T10:30:00"
            }
        }

class PredictionResponse(BaseModel):
    """예측 응답 모델"""
    predictions: List[LottoPrediction] = Field(
        description="생성된 예측 리스트"
    )
    count: int = Field(
        description="생성된 예측 개수"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "predictions": [
                    {
                        "combination": [3, 12, 23, 28, 35, 42],
                        "generated_at": "2024-01-15T10:30:00"
                    }
                ],
                "count": 1
            }
        }
```

### Database Schema (유지)

**lotto_draws 테이블**: 과거 당첨 번호 저장
```sql
CREATE TABLE lotto_draws (
    draw_no INT PRIMARY KEY,
    num1 TINYINT NOT NULL,
    num2 TINYINT NOT NULL,
    num3 TINYINT NOT NULL,
    num4 TINYINT NOT NULL,
    num5 TINYINT NOT NULL,
    num6 TINYINT NOT NULL,
    bonus_num TINYINT,
    draw_date DATE NOT NULL,
    create_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;
```

**recommand 테이블**: 예측 결과 저장
```sql
CREATE TABLE recommand (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    num1 TINYINT NOT NULL,
    num2 TINYINT NOT NULL,
    num3 TINYINT NOT NULL,
    num4 TINYINT NOT NULL,
    num5 TINYINT NOT NULL,
    num6 TINYINT NOT NULL,
    create_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX recommand_user_id_IDX (user_id),
    INDEX recommand_create_at_IDX (create_at)
) ENGINE=InnoDB;
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Valid Combination Generation

*For any* generated combination, all 6 numbers should be unique, within the range 1-45, and the combination should contain exactly 6 numbers.

**Validates: Requirements 1.1**

### Property 2: Sorted Combination Output

*For any* generated combination, the numbers should be in ascending order (n1 < n2 < n3 < n4 < n5 < n6).

**Validates: Requirements 1.4**

### Property 3: Duplicate Detection and Regeneration

*For any* combination that matches a historical winning combination, the system should discard it and generate a new combination until a non-duplicate is found.

**Validates: Requirements 2.2**

### Property 4: Order-Independent Duplicate Checking

*For any* two combinations with the same numbers in different orders, the duplicate checker should consider them as identical.

**Validates: Requirements 2.3**

### Property 5: Prediction Persistence

*For any* valid generated combination, when saved to the database, it should be retrievable from the recommand table.

**Validates: Requirements 3.1**

### Property 6: Timestamp Recording

*For any* saved prediction, the record should include a timestamp indicating when it was generated.

**Validates: Requirements 3.2**

### Property 7: User Association

*For any* prediction request with a user_id, all generated predictions should be associated with that user_id in the database.

**Validates: Requirements 3.3**

### Property 8: Batch Uniqueness

*For any* request for N predictions (1 ≤ N ≤ 20), the system should generate exactly N combinations, and all N combinations should be unique from each other.

**Validates: Requirements 6.1**

### Property 9: Input Validation

*For any* request with num_predictions outside the range [1, 20], the system should reject the request with a validation error.

**Validates: Requirements 6.2**

### Property 10: Historical Duplicate Prevention

*For any* batch of N generated predictions, none of the combinations should match any historical winning combination in the database.

**Validates: Requirements 6.5**

### Property 11: Telegram Message Formatting

*For any* set of predictions sent to Telegram, the message should include all prediction numbers and a timestamp in a readable format.

**Validates: Requirements 11.4, 11.5**

### Property 12: Extreme Pattern Filtering

*For any* generated combination, the system should reject extreme patterns including: 5+ consecutive numbers, arithmetic sequences (all gaps equal and > 1), extreme sums (< 80 or > 200), all odd/even numbers, and 5+ numbers in a single 10-number range.

**Validates: Requirements 12.1, 12.2, 12.3, 12.4, 12.5**


## Error Handling

### Error Types

```python
from utils.exceptions import (
    ValidationError,
    PredictionGenerationError,
    DataLoadError,
    DatabaseError
)

class ValidationError(Exception):
    """입력 유효성 검증 실패"""
    pass

class PredictionGenerationError(Exception):
    """예측 생성 실패 (최대 재시도 초과 등)"""
    pass

class DataLoadError(Exception):
    """데이터 로드 실패"""
    pass

class DatabaseError(Exception):
    """데이터베이스 작업 실패"""
    pass

class TelegramNotificationError(Exception):
    """Telegram 알림 전송 실패"""
    pass
```

### Error Handling Strategy

#### 1. Input Validation Errors

```python
# num_predictions 범위 검증
if not 1 <= num_predictions <= 20:
    raise ValidationError(
        f"num_predictions must be between 1 and 20, got {num_predictions}"
    )
```

**HTTP Response**: 400 Bad Request
```json
{
    "error": "ValidationError",
    "message": "num_predictions must be between 1 and 20, got 25"
}
```

#### 2. Prediction Generation Errors

```python
# 최대 재시도 횟수 초과
if retry_count >= self.max_retries:
    logger.error(
        f"Failed to generate unique combination after {self.max_retries} attempts"
    )
    raise PredictionGenerationError(
        f"Could not generate unique combination after {self.max_retries} attempts"
    )
```

**HTTP Response**: 500 Internal Server Error
```json
{
    "error": "PredictionGenerationError",
    "message": "Could not generate unique combination after 100 attempts"
}
```

#### 3. Database Errors

```python
# 데이터베이스 연결 실패
try:
    winning_combinations = await self.data_service.get_all_winning_combinations()
except Exception as e:
    logger.exception(f"Failed to load winning combinations: {e}")
    raise DataLoadError(f"Failed to load historical data: {str(e)}")
```

**HTTP Response**: 503 Service Unavailable
```json
{
    "error": "DataLoadError",
    "message": "Failed to load historical data: Connection timeout"
}
```

#### 4. Graceful Degradation

```python
# 데이터베이스 저장 실패 시에도 예측 결과는 반환
try:
    await self.data_service.save_prediction(combination, user_id)
except Exception as e:
    logger.error(f"Failed to save prediction: {e}")
    # 저장 실패해도 예측 결과는 반환
    # 클라이언트는 예측을 받을 수 있음
```

#### 5. Telegram Notification Errors

```python
# Telegram 알림 실패 시에도 예측 생성은 성공
try:
    await telegram_notifier.send_predictions(predictions)
except Exception as e:
    logger.error(f"Failed to send Telegram notification: {e}")
    # 알림 실패해도 예측 결과는 정상 반환
    # 사용자는 API 응답으로 예측을 받을 수 있음
```

**HTTP Response**: 200 OK (알림 실패해도 예측은 성공)
```json
{
    "predictions": [...],
    "count": 5,
    "notification_sent": false
}
```

### Logging Strategy

```python
import logging

logger = logging.getLogger("lotto_prediction")

# 요청 로깅
logger.info(
    f"Prediction request: num_predictions={num_predictions}, user_id={user_id}"
)

# 중복 감지 로깅
logger.debug(
    f"Duplicate combination detected: {combination}, retry_count={retry_count}"
)

# 성공 로깅
logger.info(
    f"Generated {len(predictions)} predictions in {elapsed_time:.2f}ms"
)

# 에러 로깅
logger.exception(f"Prediction generation failed: {e}")
```

## Testing Strategy

### Dual Testing Approach

이 프로젝트는 **단위 테스트**와 **속성 기반 테스트(Property-Based Testing)**를 모두 사용합니다:

- **단위 테스트**: 특정 예제, 엣지 케이스, 에러 조건 검증
- **속성 기반 테스트**: 모든 입력에 대한 보편적 속성 검증

두 접근 방식은 상호 보완적이며 포괄적인 테스트 커버리지를 제공합니다.

### Property-Based Testing Configuration

- **라이브러리**: `hypothesis` (Python)
- **최소 반복 횟수**: 100회 (랜덤 입력 생성)
- **태그 형식**: `# Feature: lotto-algorithm-simplification, Property {number}: {property_text}`

각 correctness property는 단일 property-based test로 구현되어야 합니다.

### Test Structure

```
tests/
├── unit/
│   ├── test_random_generator.py
│   ├── test_duplicate_checker.py
│   ├── test_prediction_service.py
│   ├── test_telegram_notifier.py
│   └── test_api_endpoints.py
├── integration/
│   ├── test_full_prediction_flow.py
│   ├── test_database_operations.py
│   └── test_telegram_integration.py
└── property/
    ├── test_combination_properties.py
    ├── test_duplicate_properties.py
    └── test_batch_properties.py
```

### Unit Tests (Examples and Edge Cases)

#### 1. Random Generator Tests

```python
import pytest
from services.random_generator import RandomGenerator

def test_generate_combination_returns_six_numbers():
    """단일 조합 생성 테스트"""
    generator = RandomGenerator()
    combination = generator.generate_combination()
    
    assert len(combination) == 6

def test_generate_combination_numbers_in_valid_range():
    """숫자 범위 검증"""
    generator = RandomGenerator()
    combination = generator.generate_combination()
    
    assert all(1 <= num <= 45 for num in combination)

def test_generate_combination_numbers_are_unique():
    """숫자 고유성 검증"""
    generator = RandomGenerator()
    combination = generator.generate_combination()
    
    assert len(set(combination)) == 6

def test_generate_combination_is_sorted():
    """정렬 검증"""
    generator = RandomGenerator()
    combination = generator.generate_combination()
    
    assert combination == sorted(combination)
```

#### 2. Duplicate Checker Tests

```python
import pytest
from services.duplicate_checker import DuplicateChecker
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_is_duplicate_returns_true_for_matching_combination():
    """중복 조합 감지"""
    mock_data_service = AsyncMock()
    mock_data_service.get_all_winning_combinations.return_value = [
        [1, 2, 3, 4, 5, 6],
        [7, 8, 9, 10, 11, 12]
    ]
    
    checker = DuplicateChecker(mock_data_service)
    result = await checker.is_duplicate([1, 2, 3, 4, 5, 6])
    
    assert result is True

@pytest.mark.asyncio
async def test_is_duplicate_returns_false_for_new_combination():
    """새로운 조합 감지"""
    mock_data_service = AsyncMock()
    mock_data_service.get_all_winning_combinations.return_value = [
        [1, 2, 3, 4, 5, 6]
    ]
    
    checker = DuplicateChecker(mock_data_service)
    result = await checker.is_duplicate([7, 8, 9, 10, 11, 12])
    
    assert result is False

@pytest.mark.asyncio
async def test_is_duplicate_ignores_order():
    """순서 무관 중복 검증"""
    mock_data_service = AsyncMock()
    mock_data_service.get_all_winning_combinations.return_value = [
        [1, 2, 3, 4, 5, 6]
    ]
    
    checker = DuplicateChecker(mock_data_service)
    result = await checker.is_duplicate([6, 5, 4, 3, 2, 1])
    
    assert result is True
```

#### 3. Prediction Service Tests

```python
import pytest
from services.simplified_prediction_service import SimplifiedPredictionService
from utils.exceptions import ValidationError, PredictionGenerationError

@pytest.mark.asyncio
async def test_generate_predictions_validates_input():
    """입력 유효성 검증"""
    service = create_test_service()
    
    with pytest.raises(ValidationError):
        await service.generate_predictions(num_predictions=0)
    
    with pytest.raises(ValidationError):
        await service.generate_predictions(num_predictions=21)

@pytest.mark.asyncio
async def test_generate_predictions_returns_requested_count():
    """요청된 개수만큼 생성"""
    service = create_test_service()
    
    predictions = await service.generate_predictions(num_predictions=5)
    
    assert len(predictions) == 5

@pytest.mark.asyncio
async def test_generate_predictions_raises_error_on_max_retries():
    """최대 재시도 초과 시 에러"""
    # 모든 조합이 중복인 상황 시뮬레이션
    mock_checker = AsyncMock()
    mock_checker.is_duplicate.return_value = True
    
    service = SimplifiedPredictionService(
        random_generator=RandomGenerator(),
        duplicate_checker=mock_checker,
        data_service=AsyncMock()
    )
    service.max_retries = 10
    
    with pytest.raises(PredictionGenerationError):
        await service.generate_predictions(num_predictions=1)
```

#### 4. Telegram Notifier Tests

```python
import pytest
from services.telegram_notifier import TelegramNotifier
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_format_message_includes_all_predictions():
    """메시지 포맷팅 테스트"""
    notifier = TelegramNotifier(bot_token="test_token", chat_id="test_chat")
    
    predictions = [
        [1, 2, 3, 4, 5, 6],
        [7, 8, 9, 10, 11, 12]
    ]
    
    message = notifier._format_message(predictions, timestamp="2024-01-15 10:30:00")
    
    # 모든 예측이 메시지에 포함되어야 함
    assert "[1, 2, 3, 4, 5, 6]" in message
    assert "[7, 8, 9, 10, 11, 12]" in message
    assert "2024-01-15 10:30:00" in message

@pytest.mark.asyncio
async def test_send_predictions_calls_telegram_api():
    """Telegram API 호출 테스트"""
    notifier = TelegramNotifier(bot_token="test_token", chat_id="test_chat")
    
    with patch.object(notifier, '_send_message', new=AsyncMock(return_value=True)) as mock_send:
        predictions = [[1, 2, 3, 4, 5, 6]]
        result = await notifier.send_predictions(predictions)
        
        assert result is True
        mock_send.assert_called_once()

@pytest.mark.asyncio
async def test_send_predictions_handles_api_failure():
    """API 실패 처리 테스트"""
    notifier = TelegramNotifier(bot_token="test_token", chat_id="test_chat")
    
    with patch.object(notifier, '_send_message', new=AsyncMock(side_effect=Exception("API Error"))):
        predictions = [[1, 2, 3, 4, 5, 6]]
        
        # 예외가 발생해도 False 반환 (크래시 안 함)
        result = await notifier.send_predictions(predictions)
        assert result is False
```

### Property-Based Tests

#### 1. Combination Properties

```python
from hypothesis import given, strategies as st
import pytest

@given(st.integers(min_value=1, max_value=20))
@pytest.mark.asyncio
async def test_property_valid_combination_generation(num_predictions):
    """
    Feature: lotto-algorithm-simplification, Property 1: Valid Combination Generation
    
    For any number of predictions (1-20), all generated combinations should have
    exactly 6 unique numbers in the range 1-45.
    """
    service = create_test_service()
    
    predictions = await service.generate_predictions(num_predictions)
    
    for prediction in predictions:
        combination = prediction.combination
        # 정확히 6개
        assert len(combination) == 6
        # 모두 고유
        assert len(set(combination)) == 6
        # 범위 내
        assert all(1 <= num <= 45 for num in combination)

@given(st.integers(min_value=1, max_value=20))
@pytest.mark.asyncio
async def test_property_sorted_combination_output(num_predictions):
    """
    Feature: lotto-algorithm-simplification, Property 2: Sorted Combination Output
    
    For any generated combination, numbers should be in ascending order.
    """
    service = create_test_service()
    
    predictions = await service.generate_predictions(num_predictions)
    
    for prediction in predictions:
        combination = prediction.combination
        assert combination == sorted(combination)
```

#### 2. Duplicate Properties

```python
from hypothesis import given, strategies as st

@given(
    st.lists(
        st.lists(st.integers(min_value=1, max_value=45), min_size=6, max_size=6),
        min_size=1,
        max_size=10
    )
)
@pytest.mark.asyncio
async def test_property_order_independent_duplicate_checking(winning_combinations):
    """
    Feature: lotto-algorithm-simplification, Property 4: Order-Independent Duplicate Checking
    
    For any combination, different orderings should be considered identical.
    """
    mock_data_service = AsyncMock()
    mock_data_service.get_all_winning_combinations.return_value = winning_combinations
    
    checker = DuplicateChecker(mock_data_service)
    
    for combo in winning_combinations:
        # 원본 순서
        is_dup_original = await checker.is_duplicate(combo)
        # 역순
        is_dup_reversed = await checker.is_duplicate(list(reversed(combo)))
        
        assert is_dup_original == is_dup_reversed
```

#### 3. Batch Properties

```python
from hypothesis import given, strategies as st

@given(st.integers(min_value=1, max_value=20))
@pytest.mark.asyncio
async def test_property_batch_uniqueness(num_predictions):
    """
    Feature: lotto-algorithm-simplification, Property 8: Batch Uniqueness
    
    For any N predictions, all N combinations should be unique from each other.
    """
    service = create_test_service()
    
    predictions = await service.generate_predictions(num_predictions)
    
    # 조합을 튜플로 변환하여 비교
    combinations = [tuple(p.combination) for p in predictions]
    
    # 모든 조합이 고유해야 함
    assert len(set(combinations)) == len(combinations)

@given(st.integers(min_value=1, max_value=20))
@pytest.mark.asyncio
async def test_property_historical_duplicate_prevention(num_predictions):
    """
    Feature: lotto-algorithm-simplification, Property 10: Historical Duplicate Prevention
    
    For any batch of N predictions, none should match historical winning combinations.
    """
    # 실제 데이터베이스에서 당첨 번호 로드
    data_service = AsyncDataService()
    winning_combinations = await data_service.get_all_winning_combinations()
    winning_set = {tuple(sorted(combo)) for combo in winning_combinations}
    
    service = create_test_service()
    predictions = await service.generate_predictions(num_predictions)
    
    for prediction in predictions:
        combo_tuple = tuple(prediction.combination)
        assert combo_tuple not in winning_set
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_full_prediction_flow():
    """전체 예측 플로우 통합 테스트"""
    # 실제 데이터베이스 연결
    data_service = AsyncDataService()
    random_generator = RandomGenerator()
    duplicate_checker = DuplicateChecker(data_service)
    
    service = SimplifiedPredictionService(
        random_generator=random_generator,
        duplicate_checker=duplicate_checker,
        data_service=data_service
    )
    
    # 예측 생성
    predictions = await service.generate_predictions(num_predictions=5, user_id=1)
    
    # 검증
    assert len(predictions) == 5
    assert all(len(p.combination) == 6 for p in predictions)
    
    # 데이터베이스에 저장되었는지 확인
    # (실제 구현에서는 저장된 레코드 조회)
```

### Test Coverage Goals

- **전체 커버리지**: 80% 이상
- **핵심 비즈니스 로직**: 95% 이상
- **Property-based tests**: 각 property당 최소 100회 반복

### Running Tests

```bash
# 모든 테스트 실행
pytest

# 단위 테스트만
pytest tests/unit/

# Property-based tests만
pytest tests/property/

# 커버리지 리포트
pytest --cov=services --cov-report=html

# 특정 property test 실행
pytest tests/property/test_combination_properties.py -v
```

## Migration Strategy

### Phase 1: 코드 제거 및 단순화

1. `AnalysisService` 제거
2. `RAGService` 제거
3. `PredictionService`를 `SimplifiedPredictionService`로 교체
4. Anthropic API 관련 설정 제거

### Phase 2: 새로운 컴포넌트 구현

1. `RandomGenerator` 구현
2. `DuplicateChecker` 구현
3. `SimplifiedPredictionService` 구현

### Phase 3: 테스트 작성

1. 단위 테스트 작성
2. Property-based tests 작성
3. 통합 테스트 작성

### Phase 4: API 엔드포인트 업데이트

1. 기존 엔드포인트를 새로운 서비스로 연결
2. 응답 형식 호환성 확인
3. 에러 처리 업데이트

### Phase 5: 배포 및 모니터링

1. 스테이징 환경 배포
2. 성능 테스트
3. 프로덕션 배포
4. 모니터링 및 로그 확인

## Performance Considerations

### Expected Performance

- **단일 예측**: < 100ms
- **20개 예측**: < 500ms
- **메모리 사용**: 최소 (복잡한 분석 제거)

### Optimization Strategies

1. **당첨 번호 캐싱**: 데이터베이스 조회 최소화
```python
class DuplicateChecker:
    def __init__(self, data_service: DataService):
        self.data_service = data_service
        self._winning_cache: Optional[Set[Tuple[int, ...]]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = timedelta(hours=1)
    
    async def _get_winning_combinations(self) -> Set[Tuple[int, ...]]:
        """캐시된 당첨 번호 반환 (1시간 TTL)"""
        now = datetime.now()
        
        if (self._winning_cache is None or 
            self._cache_timestamp is None or
            now - self._cache_timestamp > self._cache_ttl):
            
            combinations = await self.data_service.get_all_winning_combinations()
            self._winning_cache = {tuple(sorted(combo)) for combo in combinations}
            self._cache_timestamp = now
        
        return self._winning_cache
```

2. **배치 저장**: 여러 예측을 한 번에 저장
```python
async def save_predictions_batch(
    self,
    predictions: List[List[int]],
    user_id: Optional[int] = None
) -> List[int]:
    """배치로 예측 저장"""
    # 단일 트랜잭션으로 처리
    pass
```

3. **비동기 처리**: 모든 I/O 작업을 비동기로
```python
# 병렬 중복 체크 (필요시)
async def check_duplicates_parallel(combinations: List[List[int]]) -> List[bool]:
    tasks = [checker.is_duplicate(combo) for combo in combinations]
    return await asyncio.gather(*tasks)
```

## Security Considerations

### Input Validation

- `num_predictions` 범위 검증 (1-20)
- SQL injection 방지 (parameterized queries)
- Rate limiting (API 레벨)

### Data Protection

- 사용자 예측 데이터 보호
- 데이터베이스 연결 정보 환경 변수로 관리
- 로그에 민감 정보 제외

## Monitoring and Observability

### Metrics to Track

- 예측 생성 요청 수
- 평균 응답 시간
- 중복 감지 횟수
- 에러 발생 빈도
- 데이터베이스 쿼리 시간

### Logging

```python
# 구조화된 로깅
logger.info(
    "prediction_generated",
    extra={
        "num_predictions": num_predictions,
        "user_id": user_id,
        "elapsed_time_ms": elapsed_time,
        "duplicate_retries": retry_count
    }
)
```

### Alerts

- 에러율 > 5%
- 평균 응답 시간 > 1초
- 데이터베이스 연결 실패

## Conclusion

이 설계는 로또 예측 시스템을 복잡한 통계 분석에서 단순한 랜덤 생성으로 전환합니다. 주요 이점:

1. **단순성**: 코드 복잡도 대폭 감소
2. **독립성**: 외부 API 의존성 제거 (Anthropic API)
3. **성능**: 빠른 응답 시간
4. **유지보수성**: 이해하기 쉬운 코드
5. **비용 절감**: Anthropic API 비용 제거
6. **알림 개선**: Slack에서 Telegram으로 전환하여 모바일 접근성 향상

시스템은 여전히 중복 조합을 방지하여 사용자에게 유효한 예측을 제공하며, 기존 API 인터페이스를 유지하여 클라이언트 영향을 최소화합니다.

## Environment Variables

시스템 운영에 필요한 환경 변수:

```bash
# 데이터베이스 설정
DATABASE_URL=mysql://user:password@localhost:3306/lotto_db
DATABASE_POOL_SIZE=10

# Telegram 설정
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# 애플리케이션 설정
MAX_PREDICTIONS=20
MAX_RETRY_ATTEMPTS=100
CACHE_TTL_HOURS=1

# 로깅 설정
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Telegram Bot 설정 방법

1. **Bot 생성**:
   - Telegram에서 @BotFather와 대화
   - `/newbot` 명령으로 새 봇 생성
   - Bot token 받기

2. **Chat ID 확인**:
   - 봇을 채팅방에 추가
   - `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates` 접속
   - `chat.id` 값 확인

3. **환경 변수 설정**:
   ```bash
   export TELEGRAM_BOT_TOKEN="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
   export TELEGRAM_CHAT_ID="-1001234567890"
   ```

