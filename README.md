# 🎮 로또 번호 예측 시스템 (LottoPrediction AI)

![Python](https://img.shields.io/badge/Python-3.13-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)
![Anthropic](https://img.shields.io/badge/Claude-3.7--Sonnet-purple.svg)
![MySQL](https://img.shields.io/badge/MySQL-8.0-orange.svg)

로또 번호 예측 시스템은 역대 로또 당첨 데이터(601~1165회차)를 분석하고 Anthropic의 Claude API를 활용한 RAG(Retrieval Augmented Generation) 기법을 적용하여 다음 회차의 로또 번호를 예측하는 시스템입니다.

## 📋 주요 기능

- **역대 로또 데이터 분석**: 과거 로또 당첨 번호 패턴을 다양한 통계적 방법으로 분석
- **AI 기반 예측**: Anthropic Claude 3.7 모델을 활용한 RAG 기반 예측
- **비동기 처리**: FastAPI 비동기 처리로 빠른 응답 속도
- **예측 결과 저장**: 데이터베이스에 예측 결과 저장 및 관리
- **성능 지표 제공**: 토큰 사용량, 소요 시간, 예상 비용 등 성능 지표 제공
- **결과 검증**: 예측 결과의 정확도 검증 기능

## 🔍 예측 알고리즘 및 통계 모델

### 1. 통계 모델 및 분석 방법

#### 1.1 기본 통계 분석
- **번호별 출현 빈도 분석**: 각 번호(1-45)의 출현 횟수를 계산
- **연속성 분석**: 이전 회차와의 공통 번호 수 분포 계산
- **홀짝 분포 분석**: 각 조합의 홀수/짝수 번호 비율 분석 (e.g., 3홀 3짝)
- **합계 범위 분석**: 당첨 조합의 번호 합계 분포 및 통계(평균, 표준편차)
- **번호 간격 분석**: 정렬된 번호 사이의 간격 패턴 분석
- **구간 분포 분석**: 번호의 구간별(1-9, 10-19, 20-29, 30-39, 40-45) 분포 분석
- **연속 번호 분석**: 연속된 번호의 출현 패턴 분석

#### 1.2 고급 확률 모델
- **베이지안 확률 계산**: 단순 빈도가 아닌 베이지안 추론 기반 확률 계산
  ```python
  def calculate_bayesian_probabilities(self) -> Dict[int, float]:
      # 사전 확률은 균등 분포 (1/45)
      prior = {i: 1/45 for i in range(1, 46)}
      
      # 라플라스 스무딩 적용 (과적합 방지)
      alpha = 2  # 평활화 계수
      frequency = self.analyze_number_frequency()
      total_draws = len(self.draws)
      
      # 베이지안 갱신
      posterior = {}
      for num in range(1, 46):
          # 관측 빈도 + 스무딩 / 전체 관측 + 스무딩 * 가능한 결과 수
          posterior[num] = (frequency.get(num, 0) + alpha) / (total_draws * 6 + alpha * 45)
      
      return posterior
  ```

- **마르코프 체인 전이 확률**: 번호 간 전이 확률을 마르코프 체인으로 모델링
  ```python
  def build_markov_transition_matrix(self) -> Dict[int, Dict[int, float]]:
      # 번호별 등장 후 다음 회차 등장 확률 계산
      transition_matrix = {i: {j: 0 for j in range(1, 46)} for i in range(1, 46)}
      
      for i in range(1, len(self.draws)):
          prev_numbers = set(self.draws[i-1].numbers)
          curr_numbers = set(self.draws[i].numbers)
          
          # 이전 회차에 등장한 번호가 다음 회차에 등장할 확률
          for prev_num in prev_numbers:
              for curr_num in range(1, 46):
                  transition_matrix[prev_num][curr_num] += 1 if curr_num in curr_numbers else 0
      
      # 확률로 정규화
      for i in range(1, 46):
          total = sum(transition_matrix[i].values())
          if total > 0:
              for j in range(1, 46):
                  transition_matrix[i][j] /= total
      
      return transition_matrix
  ```

### 2. 번호 생성 알고리즘

#### 2.1 RAG 기반 생성 (주요 방법)
- **분석 데이터 컨텍스트 제공**: Claude AI 모델에 종합 분석 결과 전달
- **통계 기반 프롬프트 엔지니어링**: 베이지안 확률, 마르코프 체인, 홀짝 균형 등 통계적 원칙 지시
- **응답 파싱 및 검증**: 모델 응답에서 JSON 조합 추출 및 유효성 검사

#### 2.2 고급 통계 기반 생성 (대체 방법)
- **베이지안 가중치 적용**: 베이지안 확률에 기반한 번호 선택
- **연속성 분포 반영**: 이전 회차와의 공통 번호 수를 실제 분포에 맞게 선택
- **홀짝 균형 조정**: 실제 당첨 패턴의 홀짝 균형 분포를 반영
- **합계 범위 검증**: 번호 합계가 평균±2.5표준편차 범위 내에 있도록 조정

#### 2.3 향상된 랜덤 생성 (최후 대체 방법)
- **통계적 유효성 검사 적용**: 극단적인 합계 값을 가진 조합 필터링
- **홀짝 분포 검증**: 모든 홀수 또는 모든 짝수 조합 제외

### 3. 조합 평가 및 필터링 알고리즘

#### 3.1 복합 점수 시스템
- **가중치 기반 점수 계산**:
  ```
  final_score = (
      CONTINUITY_WEIGHT * continuity_score +
      FREQUENCY_WEIGHT * frequency_score +
      DISTRIBUTION_WEIGHT * distribution_score +
      PARITY_WEIGHT * parity_score +
      SUM_RANGE_WEIGHT * sum_score
  )
  ```
  - 연속성 점수(40%): 이전 회차와의 공통 번호 수 확률
  - 빈도 점수(20%): 베이지안 확률 기반 번호 빈도
  - 분포 점수(20%): 번호 간 간격 분포 유사도
  - 홀짝 점수(10%):
  - 합계 범위 점수(10%): 평균에서의 표준편차 기반 점수

#### 3.2 통계적 유효성 검증
- **홀짝 균형 검증**: 실제 확률 5% 미만의 홀짝 조합 필터링
- **합계 범위 검증**: 평균에서 2.5 표준편차 이상 벗어나는 합계 필터링
- **연속 번호 검증**: 비정상적인 연속 번호 패턴 필터링

#### 3.3 조합 다양성 확보
- **다양성 필터 적용**: 너무 유사한 조합 제거로 다양성 확보
  ```python
  def _apply_diversity_filter(self, predictions: List[LottoPrediction], min_distance=2):
      filtered_predictions = []
      
      # 항상 가장 높은 점수의 조합은 포함
      filtered_predictions.append(predictions[0])
      
      for pred in predictions[1:]:
          # 이미 선택된 조합들과의 유사도 체크
          too_similar = False
          
          for selected_pred in filtered_predictions:
              # 두 조합 간 공통 번호 수
              common_count = len(set(pred.combination).intersection(set(selected_pred.combination)))
              unique_count = 6 - common_count  # 서로 다른 번호 수
              
              # 공통 번호가 너무 많으면 유사하다고 판단
              if unique_count < min_distance:
                  too_similar = True
                  break
          
          # 충분히 다양하면 추가
          if not too_similar:
              filtered_predictions.append(pred)
      
      return filtered_predictions
  ```

### 4. 주요 가중치 및 매개변수

시스템은 다음과 같은 주요 가중치와 매개변수를 사용합니다:

- **연속성 가중치**: `CONTINUITY_WEIGHT = 0.4` (40% 반영)
- **빈도 가중치**: `FREQUENCY_WEIGHT = 0.2` (20% 반영)
- **분포 가중치**: `DISTRIBUTION_WEIGHT = 0.2` (20% 반영)
- **홀짝 가중치**: `PARITY_WEIGHT = 0.1` (10% 반영)
- **합계 범위 가중치**: `SUM_RANGE_WEIGHT = 0.1` (10% 반영)
- **라플라스 스무딩 계수**: `alpha = 2` (베이지안 계산 시)
- **최소 다양성 거리**: `min_distance = 2` (조합 간 최소 다른 번호 수)

## 🛠️ 기술 스택

- **백엔드**: Python 3.13, FastAPI
- **데이터베이스**: MySQL 8.0
- **AI 모델**: Anthropic Claude 3.7 Sonnet
- **데이터 분석**: NumPy, Pandas, Scikit-learn
- **비동기 처리**: asyncio, aiomysql, aiohttp
- **컨테이너화**: Docker, Docker Compose

## 🚀 설치 및 실행 방법

### 환경 변수 설정

`.env` 파일을 생성하여 필요한 환경 변수를 설정하세요:

```
DB_HOST=localhost
DB_USER=user
DB_PASSWORD=password
DB_NAME=lotto_db
DB_PORT=3306
ANTHROPIC_API_KEY=your_anthropic_api_key
ANTHROPIC_MODEL=claude-3-7-sonnet-20250219
SLACK_WEBHOOK_URL=webhook-url
```

### 일반 실행 방법

```bash
# 가상 환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 데이터베이스 스키마 설정 (MySQL 클라이언트 필요)
mysql -u username -p lotto_db < docker/mysql/init/01-schema.sql

# API 서버 실행
python api_server.py

# CLI 실행
python cli_runner.py load --start 601 --end 1165
python cli_runner.py predict --count 5 --output text --save
```

### Docker를 이용한 실행

```bash
# 서비스 빌드 및 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f api

# 서비스 중지
docker-compose down
```

## 📡 API 엔드포인트

### 로또 번호 예측 API
```http
POST /api/predict
Content-Type: application/json

{
  "count": 5
}
```

### 당첨 결과 저장 API
```http
POST /api/results
Content-Type: application/json

{
  "draw_no": 1166,
  "numbers": [1, 15, 19, 23, 28, 42]
}
```

### 헬스 체크 API
```http
GET /api/health
```

API 문서는 서버 실행 후 다음 URL에서 확인할 수 있습니다:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📊 프로젝트 구조

```
lotto_prediction_system/
├── api/                 # FastAPI 애플리케이션
│   ├── routers/         # API 라우터
│   ├── schemas/         # 요청/응답 모델
│   ├── dependencies.py  # 의존성 주입
│   └── main.py          # FastAPI 앱 정의
├── config/              # 설정 및 환경 변수 관리
├── database/            # 데이터베이스 관련 코드
│   ├── connector.py     # DB 연결 관리
│   └── repositories/    # 데이터 접근 로직
├── docker/              # Docker 관련 파일
├── models/              # 데이터 모델 클래스
├── services/            # 핵심 비즈니스 로직
│   ├── analysis_service.py  # 데이터 분석 서비스
│   ├── data_service.py      # 데이터 관리 서비스
│   ├── prediction_service.py # 예측 서비스
│   └── rag_service.py       # Claude RAG 서비스
├── utils/               # 유틸리티 함수 및 클래스
├── evaluation/          # 예측 결과 평가 로직
├── cli/                 # CLI 인터페이스
├── api_server.py        # API 서버 실행 스크립트
├── cli_runner.py        # CLI 실행 스크립트
└── requirements.txt     # 의존성 패키지 목록
```

## 📊 성능 지표

예측 API는 다음과 같은 성능 지표를 제공합니다:

- **소요 시간**: 전체 예측 과정에 걸린 시간(초)
- **토큰 사용량**: Claude API 사용 토큰 수
- **API 호출 횟수**: Anthropic API 호출 횟수
- **예상 비용**: 토큰 사용량에 따른 예상 비용(USD)

## 🧪 테스트

API 테스트는 `test_main.http` 파일을 통해 수행할 수 있습니다. 이 파일은 IntelliJ IDEA, WebStorm, PyCharm 등 JetBrains IDE나 VS Code(REST Client 확장 프로그램 설치 필요)에서 실행할 수 있습니다.

## 📝 참고 사항

이 시스템은 데이터 분석 및 AI 기반 예측을 통해 로또 번호 조합을 제안하지만, 로또 추첨은 본질적으로 무작위이므로 실제 당첨을 보장하지 않습니다. 이 시스템은 교육적, 실험적 목적으로 설계되었습니다.

## 📜 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.
