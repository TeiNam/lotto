# Docker 배포 가이드

## 📦 개요

이 프로젝트는 Docker를 사용하여 다음 서비스를 컨테이너화합니다:
- **API 서버**: FastAPI 기반 REST API
- **Telegram Bot**: 자동화된 예측 생성 및 알림
- **MySQL 데이터베이스**: 당첨 번호 및 예측 데이터 저장

## 🚀 빠른 시작

### 1. 환경 변수 설정

`.env` 파일을 생성하고 필요한 환경 변수를 설정합니다:

```bash
# 데이터베이스 설정
DB_HOST=db
DB_USER=lotto
DB_PASSWORD=your_secure_password
DB_NAME=lotto
DB_PORT=3306
MYSQL_ROOT_PASSWORD=your_root_password

# Telegram Bot 설정
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### 2. Docker Compose로 실행

```bash
# 프로젝트 루트에서 실행
cd docker
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 특정 서비스 로그만 확인
docker-compose logs -f api
docker-compose logs -f bot
docker-compose logs -f db
```

### 3. 서비스 확인

- **API 서버**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs
- **헬스체크**: http://localhost:8000/health
- **MySQL**: localhost:3306

## 🏗️ 이미지 빌드

### 개별 이미지 빌드

```bash
# API 서버 이미지
docker build -f docker/Dockerfile -t lotto-api:latest .

# Telegram Bot 이미지
docker build -f docker/Dockerfile.bot -t lotto-bot:latest .
```

### Multi-platform 빌드 (ARM64/AMD64)

```bash
# Buildx 설정
docker buildx create --use

# API 서버 (multi-platform)
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -f docker/Dockerfile \
  -t lotto-api:latest \
  --push .

# Telegram Bot (multi-platform)
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -f docker/Dockerfile.bot \
  -t lotto-bot:latest \
  --push .
```

## 📋 Docker Compose 명령어

### 기본 명령어

```bash
# 서비스 시작 (백그라운드)
docker-compose up -d

# 서비스 중지
docker-compose stop

# 서비스 재시작
docker-compose restart

# 서비스 중지 및 컨테이너 제거
docker-compose down

# 볼륨까지 제거 (데이터 삭제 주의!)
docker-compose down -v
```

### 개별 서비스 제어

```bash
# API 서버만 재시작
docker-compose restart api

# Bot만 재시작
docker-compose restart bot

# 데이터베이스만 재시작
docker-compose restart db
```

### 로그 및 모니터링

```bash
# 전체 로그 확인
docker-compose logs -f

# 최근 100줄만 확인
docker-compose logs --tail=100 -f

# 특정 서비스 로그
docker-compose logs -f api
docker-compose logs -f bot

# 컨테이너 상태 확인
docker-compose ps

# 리소스 사용량 확인
docker stats
```

## 🔧 개발 환경

개발 시에는 볼륨 마운트를 사용하여 코드 변경사항을 즉시 반영할 수 있습니다:

```yaml
# docker-compose.dev.yml
services:
  api:
    volumes:
      - ../:/app
    command: uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

```bash
# 개발 모드 실행
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## 🐛 트러블슈팅

### 데이터베이스 연결 실패

```bash
# 데이터베이스 로그 확인
docker-compose logs db

# 데이터베이스 컨테이너 접속
docker-compose exec db mysql -u root -p

# 연결 테스트
docker-compose exec api nc -zv db 3306
```

### Bot이 시작되지 않음

```bash
# Bot 로그 확인
docker-compose logs bot

# 환경 변수 확인
docker-compose exec bot env | grep TELEGRAM

# Bot 컨테이너 재시작
docker-compose restart bot
```

### 포트 충돌

```bash
# 사용 중인 포트 확인
lsof -i :8000
lsof -i :3306

# docker-compose.yml에서 포트 변경
ports:
  - "8001:8000"  # 호스트:컨테이너
```

## 📊 헬스체크

각 서비스는 헬스체크를 지원합니다:

```bash
# API 헬스체크
curl http://localhost:8000/health

# 컨테이너 헬스 상태 확인
docker-compose ps
```

## 🔐 보안 권장사항

1. **환경 변수 보호**
   - `.env` 파일을 `.gitignore`에 추가
   - 프로덕션에서는 Docker Secrets 또는 환경 변수 관리 도구 사용

2. **네트워크 격리**
   - 프로덕션에서는 API만 외부에 노출
   - 데이터베이스는 내부 네트워크만 접근 가능하도록 설정

3. **이미지 보안**
   - 정기적으로 베이스 이미지 업데이트
   - 취약점 스캔 도구 사용 (Trivy, Snyk 등)

## 🚢 프로덕션 배포

### GitHub Container Registry 사용

```bash
# 이미지 pull
docker pull ghcr.io/teinam/lotto-api:latest
docker pull ghcr.io/teinam/lotto-bot:latest

# docker-compose.prod.yml 사용
docker-compose -f docker-compose.prod.yml up -d
```

### 환경별 설정

```bash
# 개발 환경
docker-compose -f docker-compose.yml up

# 스테이징 환경
docker-compose -f docker-compose.yml -f docker-compose.staging.yml up

# 프로덕션 환경
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up
```

## 📈 모니터링

### 로그 수집

```bash
# 로그를 파일로 저장
docker-compose logs > logs/docker-$(date +%Y%m%d).log

# 실시간 로그 모니터링
docker-compose logs -f --tail=100
```

### 리소스 모니터링

```bash
# 컨테이너별 리소스 사용량
docker stats

# 특정 컨테이너만 모니터링
docker stats lotto-api lotto-bot lotto-db
```

## 🔄 업데이트 및 롤백

### 이미지 업데이트

```bash
# 최신 이미지 pull
docker-compose pull

# 서비스 재시작 (다운타임 최소화)
docker-compose up -d --no-deps --build api
docker-compose up -d --no-deps --build bot
```

### 롤백

```bash
# 특정 버전으로 롤백
docker-compose down
docker pull ghcr.io/teinam/lotto-api:v1.0.0
docker-compose up -d
```

## 📚 추가 리소스

- [Docker 공식 문서](https://docs.docker.com/)
- [Docker Compose 문서](https://docs.docker.com/compose/)
- [FastAPI Docker 가이드](https://fastapi.tiangolo.com/deployment/docker/)
