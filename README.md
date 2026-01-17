# 🎰 로또 번호 예측 시스템

![Python](https://img.shields.io/badge/Python-3.13-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)
![MySQL](https://img.shields.io/badge/MySQL-8.0-orange.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

로또 번호 예측 시스템은 암호학적으로 안전한 난수 생성과 극단적 패턴 필터링을 통해 로또 번호를 생성하고, Telegram Bot을 통해 자동화된 예측 및 알림 서비스를 제공합니다.

## ✨ 주요 기능

- 🎲 **랜덤 번호 생성**: 암호학적으로 안전한 난수 생성 (`secrets.SystemRandom`)
- 🔍 **극단적 패턴 필터링**: 연속 숫자, 등차수열, 극단적 합계 등 비정상 패턴 제거
- 🤖 **Telegram Bot**: 대화형 봇을 통한 예측 생성 및 결과 확인
- ⏰ **자동화 스케줄러**: 
  - 금요일 12시: 예측 10개 자동 생성 및 전송
  - 토요일 21시: 당첨번호 자동 업데이트
- 🌐 **REST API**: FastAPI 기반 비동기 API
- 🐳 **Docker 지원**: 원클릭 배포 (API + Bot + MySQL)
- 📊 **당첨 결과 매칭**: 생성한 번호와 당첨 번호 자동 비교

## 🚀 빠른 시작

### Docker로 실행 (추천)

```bash
# 1. 저장소 클론
git clone https://github.com/TeiNam/lotto.git
cd lotto

# 2. 환경 변수 설정
cp .env.example .env
# .env 파일 편집 (DB 정보, Telegram Bot 토큰 등)

# 3. Docker Compose로 실행
cd docker
docker-compose up -d

# 4. 로그 확인
docker-compose logs -f
```

### GHCR 이미지 사용

```bash
# 이미지 Pull
docker pull ghcr.io/teinam/lotto:latest

# 실행
docker run -d \
  --name lotto-app \
  -p 8000:8000 \
  -e DB_HOST=your-db-host \
  -e DB_USER=lotto \
  -e DB_PASSWORD=your-password \
  -e TELEGRAM_BOT_TOKEN=your-token \
  -e TELEGRAM_CHAT_ID=your-chat-id \
  ghcr.io/teinam/lotto:latest
```

## 📱 Telegram Bot 사용법

### 명령어

- `/start` - 봇 시작 및 환영 메시지
- `/generate [개수]` - 로또 번호 생성 (기본 5개, 최대 20개)
- `/winning` - 최신 회차 당첨 번호 확인
- `/result [회차]` - 예측 결과와 당첨 번호 매칭
- `/help` - 명령어 도움말

### 사용 예시

```
/generate 10
→ 10개 조합 생성 및 데이터베이스 저장

/winning
→ 최신 회차 당첨 번호 확인

/result
→ 내가 생성한 번호와 당첨 번호 매칭 결과
```

## 🔧 환경 변수 설정

`.env` 파일 예시:

```bash
# 데이터베이스
DB_HOST=localhost
DB_USER=lotto
DB_PASSWORD=your_secure_password
DB_NAME=lotto
DB_PORT=3306

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# MySQL Root (Docker 사용 시)
MYSQL_ROOT_PASSWORD=your_root_password
```

## 📡 API 엔드포인트

### 예측 생성
```http
POST /api/predict
Content-Type: application/json

{
  "count": 5
}
```

### 당첨 번호 조회
```http
GET /api/lottery/latest
```

### 헬스체크
```http
GET /health
```

**API 문서**: http://localhost:8000/docs

## 🎯 예측 알고리즘

### 1. 랜덤 생성
- `secrets.SystemRandom()` 사용 (암호학적으로 안전)
- 1-45 범위에서 6개 고유 숫자 선택
- 자동 정렬

### 2. 극단적 패턴 필터링

시스템은 다음 패턴을 자동으로 필터링합니다:

- ❌ **연속 숫자 5개 이상**: `[1, 2, 3, 4, 5, 6]`
- ❌ **등차수열**: `[5, 10, 15, 20, 25, 30]`
- ❌ **극단적 합계**: 합계 < 80 또는 > 200
- ❌ **홀수만/짝수만**: `[1, 3, 5, 7, 9, 11]`
- ❌ **구간 편중**: 한 구간에 5개 이상 몰림

### 3. 중복 검증
- 과거 당첨 번호와 중복 확인
- 배치 내 고유성 보장
- 캐싱으로 성능 최적화 (1시간 TTL)

## 🏗️ 프로젝트 구조

```
lotto/
├── api/                    # FastAPI 애플리케이션
│   ├── routers/            # API 라우터
│   └── main.py             # FastAPI 앱
├── config/                 # 설정 관리
├── database/               # 데이터베이스 연동
│   └── repositories/       # 데이터 접근 계층
├── docker/                 # Docker 설정
│   ├── Dockerfile          # 통합 이미지 (API + Bot)
│   ├── docker-compose.yml  # 로컬 개발용
│   └── docker-compose.synology.yml  # Synology NAS용
├── models/                 # 데이터 모델
├── services/               # 비즈니스 로직
│   ├── random_generator.py          # 난수 생성
│   ├── duplicate_checker.py         # 중복 검증
│   ├── simplified_prediction_service.py  # 예측 서비스
│   ├── telegram_notifier.py         # 텔레그램 알림
│   └── lottery_service.py           # 당첨번호 크롤링
├── tests/                  # 테스트
│   ├── unit/               # 단위 테스트
│   ├── property/           # 속성 기반 테스트
│   └── integration/        # 통합 테스트
├── telegram_bot_handler.py # Telegram Bot 핸들러
├── lotto_oot_crawler.py    # 당첨번호 크롤러
└── requirements.txt        # 의존성
```

## 🐳 Docker 구조

하나의 이미지에서 API와 Bot을 동시에 실행:

```yaml
services:
  app:    # API + Bot (Supervisor로 관리)
  db:     # MySQL 8.0
```

**Supervisor**가 두 프로세스를 자동으로 관리합니다:
- API 서버 (포트 8000)
- Telegram Bot (백그라운드)

## 📊 자동화 스케줄

### 금요일 12:00
- 다음 회차 예측 10개 자동 생성
- 데이터베이스에 저장
- Telegram으로 예측 결과 전송

### 토요일 21:00
- lotto.oot.kr에서 당첨번호 크롤링
- 데이터베이스에 자동 저장
- 데이터 서비스 새로고침

## 🧪 테스트

```bash
# 전체 테스트 실행
pytest

# 단위 테스트만
pytest tests/unit/

# 속성 기반 테스트 (Property-Based Testing)
pytest tests/property/

# 통합 테스트
pytest tests/integration/

# 커버리지 확인
pytest --cov=. --cov-report=html
```

## 📦 배포

### Synology NAS

상세한 가이드: [docker/SYNOLOGY_DEPLOYMENT.md](docker/SYNOLOGY_DEPLOYMENT.md)

```bash
# 이미지 Pull
docker pull ghcr.io/teinam/lotto:latest

# 실행
docker-compose -f docker-compose.synology.yml up -d
```

### 일반 서버

```bash
# GitHub Container Registry에서 Pull
docker pull ghcr.io/teinam/lotto:latest

# 실행
docker run -d \
  --name lotto-app \
  -p 8000:8000 \
  --env-file .env \
  ghcr.io/teinam/lotto:latest
```

## 🔄 업데이트

```bash
# 최신 이미지 Pull
docker pull ghcr.io/teinam/lotto:latest

# 컨테이너 재시작
docker-compose down
docker-compose up -d
```

## 🛠️ 기술 스택

- **언어**: Python 3.13
- **웹 프레임워크**: FastAPI 0.115
- **데이터베이스**: MySQL 8.0, aiomysql
- **Bot**: python-telegram-bot 21.10
- **스케줄러**: APScheduler 3.11
- **테스트**: pytest, hypothesis (Property-Based Testing)
- **컨테이너**: Docker, Supervisor
- **크롤링**: BeautifulSoup4

## 📝 참고 사항

- 로또 추첨은 본질적으로 무작위이므로 당첨을 보장하지 않습니다
- 이 시스템은 교육적, 실험적 목적으로 설계되었습니다
- 책임감 있는 게임 플레이를 권장합니다

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🤝 기여

이슈 및 풀 리퀘스트를 환영합니다!

## 📞 문의

- GitHub Issues: https://github.com/TeiNam/lotto/issues
- Telegram Bot: @Tei_Lotto_Bot

---

**Made with ❤️ by TeiNam**
