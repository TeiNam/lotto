# Implementation Plan: Lotto Algorithm Simplification

## Overview

로또 예측 시스템의 알고리즘을 복잡한 통계 분석에서 완전 랜덤 생성 방식으로 단순화하고, Slack 알림을 Telegram으로 전환합니다. 구현은 기존 코드 제거, 새 컴포넌트 구현, 테스트 작성, API 통합 순서로 진행됩니다.

## Tasks

- [x] 1. 프로젝트 준비 및 의존성 설정
  - Python 환경 확인 (Python 3.8+)
  - 필요한 패키지 설치: `aiohttp`, `hypothesis` (테스트용)
  - 환경 변수 템플릿 업데이트 (.env.example)
  - _Requirements: 5.4, 11.7_

- [x] 2. 기존 복잡한 코드 제거
  - [x] 2.1 AnalysisService 제거
    - `services/analysis_service.py` 파일 삭제
    - 관련 import 문 제거
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_
  
  - [x] 2.2 RAGService 제거
    - `services/rag_service.py` 파일 삭제
    - Anthropic API 관련 설정 제거
    - 관련 import 문 제거
    - _Requirements: 5.1, 5.2, 5.3_
  
  - [x] 2.3 Slack 알림 코드 제거
    - Slack 관련 코드 및 설정 제거
    - Slack 환경 변수 제거
    - _Requirements: 11.1_

- [x] 3. 핵심 컴포넌트 구현
  - [x] 3.1 RandomGenerator 구현
    - `services/random_generator.py` 생성
    - `generate_combination()` 메서드 구현
    - `is_extreme_pattern()` 메서드 구현 (극단적 패턴 필터링)
    - `secrets.SystemRandom()` 사용하여 암호학적으로 안전한 난수 생성
    - 1-45 범위에서 6개 고유 숫자 선택
    - 극단적 패턴 필터링 적용:
      - 연속 숫자 5개 이상 거부
      - 등차수열 (모든 간격 동일) 거부
      - 극단적 합계 (< 80 또는 > 200) 거부
      - 홀수만/짝수만 거부
      - 한 구간에 5개 이상 몰림 거부
    - 결과를 정렬하여 반환
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 12.1, 12.2, 12.3, 12.4, 12.5_
  
  - [x] 3.2 RandomGenerator 단위 테스트 작성
    - `tests/unit/test_random_generator.py` 생성
    - 6개 숫자 생성 검증
    - 숫자 범위 검증 (1-45)
    - 고유성 검증
    - 정렬 검증
    - 극단적 패턴 필터링 검증:
      - 연속 숫자 5개 이상 감지 테스트
      - 등차수열 감지 테스트
      - 극단적 합계 감지 테스트
      - 홀수만/짝수만 감지 테스트
      - 구간 편중 감지 테스트
    - _Requirements: 1.1, 1.4, 12.1, 12.2, 12.3, 12.4, 12.5_
  
  - [x] 3.3 RandomGenerator 속성 기반 테스트 작성
    - `tests/property/test_combination_properties.py` 생성
    - **Property 1: Valid Combination Generation**
    - **Property 2: Sorted Combination Output**
    - **Property 12: Extreme Pattern Filtering** (새로 추가)
    - **Validates: Requirements 1.1, 1.4, 12.1, 12.2, 12.3, 12.4, 12.5**

- [x] 4. 중복 검증 컴포넌트 구현
  - [x] 4.1 DuplicateChecker 구현
    - `services/duplicate_checker.py` 생성
    - `is_duplicate()` 메서드 구현
    - `is_new_combination()` 메서드 구현
    - 데이터베이스에서 과거 당첨 번호 조회
    - 조합을 정렬된 튜플로 변환하여 비교
    - 캐싱 로직 구현 (1시간 TTL)
    - _Requirements: 2.1, 2.2, 2.3, 2.4_
  
  - [x] 4.2 DuplicateChecker 단위 테스트 작성
    - `tests/unit/test_duplicate_checker.py` 생성
    - 중복 조합 감지 테스트
    - 새로운 조합 감지 테스트
    - 순서 무관 비교 테스트
    - 캐싱 동작 테스트
    - _Requirements: 2.2, 2.3_
  
  - [x] 4.3 DuplicateChecker 속성 기반 테스트 작성
    - `tests/property/test_duplicate_properties.py` 생성
    - **Property 3: Duplicate Detection and Regeneration**
    - **Property 4: Order-Independent Duplicate Checking**
    - **Validates: Requirements 2.2, 2.3**

- [x] 5. Checkpoint - 기본 컴포넌트 검증
  - 모든 테스트 실행 및 통과 확인
  - 코드 리뷰 및 리팩토링
  - 사용자에게 진행 상황 보고

- [x] 6. 단순화된 예측 서비스 구현
  - [x] 6.1 SimplifiedPredictionService 구현
    - `services/simplified_prediction_service.py` 생성
    - `generate_predictions()` 메서드 구현
    - `_generate_single_prediction()` 메서드 구현
    - 입력 유효성 검증 (1-20 범위)
    - 중복 방지 로직 (최대 100회 재시도)
    - 배치 생성 시 상호 고유성 보장
    - _Requirements: 1.1, 2.2, 6.1, 6.2, 6.5, 9.4_
  
  - [x] 6.2 SimplifiedPredictionService 단위 테스트 작성
    - `tests/unit/test_prediction_service.py` 생성
    - 입력 유효성 검증 테스트
    - 요청된 개수만큼 생성 테스트
    - 최대 재시도 초과 에러 테스트
    - 배치 고유성 테스트
    - _Requirements: 6.1, 6.2, 9.4_
  
  - [x] 6.3 SimplifiedPredictionService 속성 기반 테스트 작성
    - `tests/property/test_batch_properties.py` 생성
    - **Property 8: Batch Uniqueness**
    - **Property 9: Input Validation**
    - **Property 10: Historical Duplicate Prevention**
    - **Validates: Requirements 6.1, 6.2, 6.5**

- [x] 7. Telegram 알림 서비스 구현
  - [x] 7.1 TelegramNotifier 구현
    - `services/telegram_notifier.py` 생성
    - `send_predictions()` 메서드 구현
    - `_format_message()` 메서드 구현
    - `_send_message()` 메서드 구현
    - aiohttp를 사용한 비동기 HTTP 요청
    - Telegram Bot API sendMessage 엔드포인트 호출
    - 메시지 포맷팅 (이모지, 타임스탬프 포함)
    - 에러 처리 (알림 실패 시 로깅만)
    - _Requirements: 11.2, 11.3, 11.4, 11.5, 11.6, 11.8_
  
  - [x] 7.2 TelegramNotifier 단위 테스트 작성
    - `tests/unit/test_telegram_notifier.py` 생성
    - 메시지 포맷팅 테스트
    - API 호출 테스트 (mock 사용)
    - 에러 처리 테스트
    - _Requirements: 11.4, 11.5, 11.6_
  
  - [x] 7.3 TelegramNotifier 속성 기반 테스트 작성
    - **Property 11: Telegram Message Formatting**
    - **Validates: Requirements 11.4, 11.5**

- [x] 8. 데이터베이스 연동 유지 및 개선
  - [x] 8.1 DataService 검토 및 업데이트
    - `get_all_winning_combinations()` 메서드 확인
    - `save_prediction()` 메서드 확인
    - 파라미터화된 쿼리 사용 확인
    - 에러 처리 개선
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_
  
  - [x] 8.2 DataService 단위 테스트 작성
    - `tests/unit/test_data_service.py` 생성 (없는 경우)
    - 당첨 번호 조회 테스트
    - 예측 저장 테스트
    - 에러 처리 테스트
    - _Requirements: 7.5_
  
  - [x] 8.3 데이터베이스 통합 테스트 작성
    - `tests/integration/test_database_operations.py` 생성
    - 실제 데이터베이스 연결 테스트
    - 트랜잭션 테스트
    - _Requirements: 7.1, 7.2, 7.3_

- [x] 9. Checkpoint - 서비스 계층 검증
  - 모든 서비스 컴포넌트 테스트 실행
  - 통합 테스트 실행
  - 코드 커버리지 확인 (목표: 80% 이상)
  - 사용자에게 진행 상황 보고

- [x] 10. API 엔드포인트 업데이트
  - [x] 10.1 API 라우터 업데이트
    - `api/routes/prediction.py` (또는 해당 파일) 수정
    - SimplifiedPredictionService 의존성 주입
    - TelegramNotifier 의존성 주입
    - 기존 엔드포인트 시그니처 유지
    - 응답 형식 호환성 확인
    - _Requirements: 8.1, 8.2, 8.3, 8.4_
  
  - [x] 10.2 예측 생성 플로우 통합
    - 예측 생성 → 데이터베이스 저장 → Telegram 알림 순서로 연결
    - Graceful degradation 구현 (알림 실패 시에도 예측 반환)
    - 에러 처리 및 로깅 추가
    - _Requirements: 3.1, 3.4, 11.6_
  
  - [x] 10.3 API 엔드포인트 테스트 작성
    - `tests/unit/test_api_endpoints.py` 업데이트
    - 엔드포인트 호출 테스트
    - 요청/응답 형식 테스트
    - 에러 응답 테스트
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [x] 11. 전체 플로우 통합 테스트
  - [x] 11.1 전체 예측 플로우 통합 테스트 작성
    - `tests/integration/test_full_prediction_flow.py` 생성
    - 실제 데이터베이스 연결 사용
    - 예측 생성 → 저장 → 조회 플로우 테스트
    - Telegram 알림 테스트 (mock 또는 실제 테스트 봇)
    - _Requirements: 1.1, 2.2, 3.1, 6.1, 11.3_
  
  - [x] 11.2 Telegram 통합 테스트 작성
    - `tests/integration/test_telegram_integration.py` 생성
    - 실제 Telegram Bot API 호출 테스트 (테스트 봇 사용)
    - 메시지 전송 및 수신 확인
    - _Requirements: 11.2, 11.3, 11.4_

- [ ] 12. 환경 설정 및 문서화
  - [ ] 12.1 환경 변수 설정
    - `.env.example` 업데이트
    - TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID 추가
    - Anthropic API 관련 변수 제거
    - Slack 관련 변수 제거
    - _Requirements: 11.7_
  
  - [ ] 12.2 README 업데이트
    - 알고리즘 변경 사항 문서화
    - Telegram Bot 설정 방법 추가
    - 환경 변수 설명 업데이트
    - 의존성 목록 업데이트
    - _Requirements: 11.7_
  
  - [ ] 12.3 마이그레이션 가이드 작성
    - 기존 시스템에서 새 시스템으로 전환 방법
    - 데이터 마이그레이션 필요 여부 확인
    - 롤백 계획 문서화

- [ ] 13. Checkpoint - 최종 검증
  - 모든 테스트 실행 (단위, 속성, 통합)
  - 코드 커버리지 확인 (목표: 80% 이상)
  - 성능 테스트 (단일 예측 < 100ms, 20개 예측 < 500ms)
  - 사용자에게 최종 검토 요청

- [ ] 14. 배포 준비
  - [ ] 14.1 스테이징 환경 배포
    - 스테이징 환경에 코드 배포
    - 환경 변수 설정 확인
    - 데이터베이스 연결 확인
    - Telegram Bot 연결 확인
  
  - [ ] 14.2 스테이징 환경 테스트
    - 실제 예측 생성 테스트
    - Telegram 알림 수신 확인
    - 성능 측정
    - 에러 로그 확인
  
  - [ ] 14.3 프로덕션 배포 계획
    - 배포 시간 결정
    - 롤백 계획 준비
    - 모니터링 설정 확인
    - 사용자 공지 (필요시)

- [ ] 15. 최종 정리
  - [ ] 15.1 사용하지 않는 코드 정리
    - 주석 처리된 코드 제거
    - 사용하지 않는 import 제거
    - 코드 포맷팅 (black, isort)
  
  - [ ] 15.2 로깅 및 모니터링 확인
    - 로그 레벨 확인
    - 중요 이벤트 로깅 확인
    - 에러 추적 설정 확인
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_
  
  - [ ] 15.3 문서 최종 검토
    - README 검토
    - API 문서 검토
    - 마이그레이션 가이드 검토

## Notes

- 모든 태스크는 필수이며, 처음부터 완전한 테스트 커버리지를 확보합니다
- 각 태스크는 특정 요구사항을 참조하여 추적 가능성을 보장합니다
- Checkpoint 태스크는 점진적 검증을 위한 중간 확인 지점입니다
- Property-based tests는 각 property당 최소 100회 반복 실행됩니다
- 통합 테스트는 실제 데이터베이스 및 Telegram Bot을 사용합니다

## Testing Strategy

- **단위 테스트**: 각 컴포넌트의 개별 기능 검증
- **속성 기반 테스트**: 보편적 속성을 다양한 입력으로 검증
- **통합 테스트**: 전체 플로우 및 외부 시스템 연동 검증
- **목표 커버리지**: 전체 80% 이상, 핵심 로직 95% 이상

## Dependencies

새로 추가되는 패키지:
- `aiohttp`: Telegram API 비동기 HTTP 요청
- `hypothesis`: Property-based testing

제거되는 패키지:
- `anthropic`: Anthropic API 클라이언트
- Slack 관련 패키지 (있는 경우)
