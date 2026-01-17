# Requirements Document

## Introduction

로또 예측 시스템의 알고리즘을 단순화하여 복잡한 통계 분석을 제거하고 완전 랜덤 번호 생성 방식으로 전환합니다. 이를 통해 시스템의 복잡도를 낮추고, 외부 API 의존성을 제거하며, 유지보수성을 향상시킵니다.

## Glossary

- **System**: 로또 예측 시스템
- **Prediction_Service**: 번호 예측을 담당하는 서비스 계층
- **Data_Service**: 데이터베이스 접근을 담당하는 서비스 계층
- **Combination**: 1부터 45까지의 숫자 중 6개를 선택한 로또 번호 조합
- **Winning_Combination**: 데이터베이스에 저장된 과거 당첨 번호 조합
- **Random_Generator**: 완전 랜덤 방식으로 번호를 생성하는 컴포넌트
- **Duplicate_Checker**: 생성된 조합이 기존 당첨 조합과 중복되는지 검증하는 컴포넌트
- **Recommand_Table**: 예측 결과를 저장하는 데이터베이스 테이블

## Requirements

### Requirement 1: 완전 랜덤 번호 생성

**User Story:** As a system, I want to generate lottery numbers using pure randomization, so that the prediction logic is simple and maintainable.

#### Acceptance Criteria

1. WHEN generating a combination, THE Random_Generator SHALL select 6 unique numbers from the range 1 to 45
2. THE Random_Generator SHALL use cryptographically secure random number generation
3. THE Random_Generator SHALL ensure all 6 numbers in a combination are unique
4. THE Random_Generator SHALL sort the numbers in ascending order before returning

### Requirement 2: 중복 조합 검증

**User Story:** As a system, I want to verify that generated combinations are not duplicates of past winning combinations, so that users receive novel predictions.

#### Acceptance Criteria

1. WHEN a combination is generated, THE Duplicate_Checker SHALL query the database for matching Winning_Combinations
2. IF a generated combination matches a Winning_Combination, THEN THE System SHALL discard it and generate a new combination
3. THE Duplicate_Checker SHALL compare combinations regardless of number order
4. WHEN checking for duplicates, THE System SHALL query all historical winning data from the database

### Requirement 3: 예측 결과 저장

**User Story:** As a system, I want to save prediction results to the database, so that users can retrieve their predictions later.

#### Acceptance Criteria

1. WHEN a valid combination is generated, THE System SHALL save it to the Recommand_Table
2. THE System SHALL store the prediction timestamp with each combination
3. THE System SHALL associate predictions with the requesting user
4. WHEN saving fails, THE System SHALL log the error and return an appropriate error response

### Requirement 4: 복잡한 알고리즘 제거

**User Story:** As a developer, I want to remove all complex statistical algorithms, so that the codebase is simpler and easier to maintain.

#### Acceptance Criteria

1. THE System SHALL NOT use Bayesian probability calculations
2. THE System SHALL NOT use Markov chain analysis
3. THE System SHALL NOT use frequency analysis algorithms
4. THE System SHALL NOT use odd-even distribution analysis
5. THE System SHALL NOT use sum range analysis
6. THE System SHALL NOT calculate prediction scores or confidence values

### Requirement 5: 외부 API 의존성 제거

**User Story:** As a system administrator, I want to eliminate external API dependencies, so that operational costs are reduced and system reliability is improved.

#### Acceptance Criteria

1. THE System SHALL NOT call the Anthropic Claude API
2. THE System SHALL NOT use RAG (Retrieval-Augmented Generation) for number generation
3. THE System SHALL NOT require API keys for prediction functionality
4. WHEN the Anthropic API is removed, THE System SHALL maintain the same API endpoint structure for backward compatibility

### Requirement 6: 배치 예측 생성

**User Story:** As a user, I want to request multiple predictions at once, so that I can get several lottery combinations in a single request.

#### Acceptance Criteria

1. WHEN a user requests N predictions, THE System SHALL generate N unique combinations
2. THE System SHALL validate that N is between 1 and 20
3. IF N is invalid, THEN THE System SHALL return a validation error
4. THE System SHALL ensure all N combinations are different from each other
5. THE System SHALL ensure all N combinations are different from historical Winning_Combinations

### Requirement 7: 데이터베이스 연동 유지

**User Story:** As a system, I want to maintain existing database connectivity, so that historical data and user predictions are properly managed.

#### Acceptance Criteria

1. THE System SHALL continue using the existing MySQL database connection
2. THE System SHALL query the lotto_draws table for historical winning combinations
3. THE System SHALL insert predictions into the recommand table
4. THE System SHALL use parameterized queries to prevent SQL injection
5. WHEN database operations fail, THE System SHALL handle exceptions gracefully and log errors

### Requirement 8: API 엔드포인트 호환성

**User Story:** As a client application, I want the API endpoints to remain unchanged, so that existing integrations continue to work without modification.

#### Acceptance Criteria

1. THE System SHALL maintain the existing POST /api/v1/predict endpoint
2. THE System SHALL accept the same request parameters (num_predictions)
3. THE System SHALL return responses in the same JSON format
4. THE System SHALL maintain the same HTTP status codes for success and error cases
5. WHEN the simplified algorithm is deployed, THE System SHALL not break existing client integrations

### Requirement 9: 성능 요구사항

**User Story:** As a system, I want prediction generation to be fast, so that users receive responses quickly.

#### Acceptance Criteria

1. WHEN generating a single prediction, THE System SHALL respond within 100 milliseconds
2. WHEN generating 20 predictions, THE System SHALL respond within 500 milliseconds
3. THE System SHALL handle concurrent requests without performance degradation
4. IF duplicate checking takes too long, THE System SHALL implement a maximum retry limit of 100 attempts

### Requirement 10: 로깅 및 모니터링

**User Story:** As a system administrator, I want comprehensive logging, so that I can monitor system behavior and troubleshoot issues.

#### Acceptance Criteria

1. THE System SHALL log each prediction generation request with timestamp and user information
2. THE System SHALL log when duplicate combinations are detected and regenerated
3. THE System SHALL log database query errors with full error details
4. THE System SHALL log performance metrics for prediction generation time
5. WHEN errors occur, THE System SHALL log stack traces for debugging

### Requirement 11: Telegram 알림 통합

**User Story:** As a user, I want to receive lottery predictions via Telegram, so that I can easily access my predictions on my mobile device.

#### Acceptance Criteria

1. THE System SHALL NOT use Slack for sending notifications
2. THE System SHALL use the Telegram Bot API to send prediction notifications
3. WHEN predictions are generated, THE System SHALL send them to a specified Telegram chat
4. THE System SHALL format prediction messages in a readable format with all 6 numbers
5. THE System SHALL include the generation timestamp in Telegram messages
6. WHEN Telegram API calls fail, THE System SHALL log the error but not fail the prediction generation
7. THE System SHALL store Telegram bot token and chat ID in environment variables
8. THE System SHALL support sending multiple predictions in a single message or separate messages

### Requirement 12: 극단적 패턴 필터링

**User Story:** As a user, I want the system to filter out statistically improbable extreme patterns, so that I receive realistic lottery combinations.

#### Acceptance Criteria

1. THE System SHALL reject combinations with 5 or more consecutive numbers (e.g., [1,2,3,4,5,10])
2. THE System SHALL reject combinations where all gaps between numbers are identical and greater than 1 (arithmetic sequences like [5,10,15,20,25,30])
3. THE System SHALL reject combinations with sum less than 80 or greater than 200
4. THE System SHALL reject combinations with all odd numbers or all even numbers
5. THE System SHALL reject combinations where 5 or more numbers fall within a single 10-number range
6. WHEN an extreme pattern is detected, THE System SHALL regenerate a new combination
7. THE System SHALL limit extreme pattern filtering attempts to prevent infinite loops
