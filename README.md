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

## 🔍 예측 방법론

이 시스템은 다음과 같은 단계로 로또 번호를 예측합니다:

1. **데이터 수집**: MySQL 데이터베이스에서 601~1165회차의 당첨 데이터 조회
2. **데이터 분석**:
   - 번호별 출현 빈도 분석
   - 연속성 분석(이전 회차와의 중복 번호 수)
   - 홀짝 분포 분석
   - 번호 합계 범위 분석
3. **RAG 기반 예측**:
   - 분석 결과를 Claude AI 모델에 전달하여 번호 조합 생성
   - 조합 검증 및 필터링 (기존 당첨 이력과 중복 확인)
   - 조합 평가 및 점수 부여
4. **결과 저장**: 예측 결과를 `recommand` 테이블에 저장

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
