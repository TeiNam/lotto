# Synology NAS 배포 가이드

## 📋 사전 준비

### 1. Synology 패키지 설치
- **Container Manager** (구 Docker 패키지)
- **SSH 서비스 활성화** (제어판 → 터미널 및 SNMP → SSH 서비스 활성화)

### 2. 필요한 정보
- Synology NAS IP 주소
- 관리자 계정 (admin)
- GitHub Personal Access Token (공개 이미지는 선택사항)

---

## 🚀 배포 방법

### 방법 1: SSH + Docker Compose (추천)

#### 1단계: NAS에 접속

```bash
# SSH로 Synology NAS 접속
ssh admin@192.168.1.100  # NAS IP로 변경

# Docker 디렉토리 생성
sudo mkdir -p /volume1/docker/lotto
cd /volume1/docker/lotto
```

#### 2단계: 설정 파일 준비

```bash
# .env 파일 생성
sudo vi .env
```

`.env` 파일 내용:
```bash
# 데이터베이스 설정
DB_USER=lotto
DB_PASSWORD=your_secure_password
DB_NAME=lotto
MYSQL_ROOT_PASSWORD=your_root_password

# Telegram Bot 설정
TELEGRAM_BOT_TOKEN=your_bot_token        # @BotFather 에서 발급
TELEGRAM_CHAT_ID=your_chat_id
TELEGRAM_ADMIN_IDS=123456789             # 봇 사용을 허용할 user_id (비우면 전원 차단)

# 동행복권 연동 (선택) — 설정하면 예치금 조회·구매 기능이 활성화됩니다
DHL_USERNAME=
DHL_PASSWORD=
```

#### 3단계: docker-compose.yml 다운로드

```bash
# GitHub에서 다운로드
sudo wget https://raw.githubusercontent.com/TeiNam/lotto/main/docker/docker-compose.synology.yml -O docker-compose.yml

# 또는 직접 생성
sudo vi docker-compose.yml
# (파일 내용 붙여넣기)
```

#### 4단계: MySQL 초기화 스크립트 준비

```bash
# 초기화 스크립트 디렉토리 생성
sudo mkdir -p mysql/init

# 스키마 파일 다운로드
sudo wget https://raw.githubusercontent.com/TeiNam/lotto/main/docker/mysql/init/01-schema.sql -O mysql/init/01-schema.sql
```

#### 5단계: 컨테이너 실행

```bash
# GHCR 로그인 (공개 이미지는 생략 가능)
docker login ghcr.io

# 이미지 Pull 및 실행
sudo docker-compose up -d

# 로그 확인
sudo docker-compose logs -f
```

---

### 방법 2: Container Manager UI 사용

#### 1단계: 레지스트리 설정

1. **Container Manager** 열기
2. **레지스트리** → **설정** 클릭
3. **추가** 클릭:
   - 레지스트리 이름: `GitHub Container Registry`
   - 레지스트리 URL: `ghcr.io`
   - 사용자명: (공개 이미지는 비워둠)
   - 비밀번호: (공개 이미지는 비워둠)

#### 2단계: 이미지 다운로드

1. **레지스트리** → **ghcr.io** 선택
2. 검색창에 입력:
   - `teinam/lotto-api`
   - `teinam/lotto-bot`
3. **다운로드** 클릭 → `latest` 태그 선택

#### 3단계: MySQL 컨테이너 생성

1. **레지스트리** → `mysql` 검색 → `8.0.40` 다운로드
2. **이미지** → `mysql:8.0.40` 선택 → **실행**
3. 설정:
   - 컨테이너 이름: `lotto-db`
   - 포트: `3306:3306`
   - 환경 변수:
     - `MYSQL_ROOT_PASSWORD=your_root_password`
     - `MYSQL_DATABASE=lotto`
     - `MYSQL_USER=lotto`
     - `MYSQL_PASSWORD=your_password`
   - 볼륨:
     - `/volume1/docker/lotto/mysql` → `/var/lib/mysql`

#### 4단계: API 컨테이너 생성

1. **이미지** → `ghcr.io/teinam/lotto-api:latest` 선택 → **실행**
2. 설정:
   - 컨테이너 이름: `lotto-api`
   - 포트: `8000:8000`
   - 환경 변수:
     - `DB_HOST=lotto-db`
     - `DB_USER=lotto`
     - `DB_PASSWORD=your_password`
     - `DB_NAME=lotto`
     - `DB_PORT=3306`
     - `TELEGRAM_BOT_TOKEN=your_token`
     - `TELEGRAM_CHAT_ID=your_chat_id`
   - 링크: `lotto-db` 선택

#### 5단계: Bot 컨테이너 생성

1. **이미지** → `ghcr.io/teinam/lotto-bot:latest` 선택 → **실행**
2. 설정:
   - 컨테이너 이름: `lotto-bot`
   - 환경 변수: (API와 동일)
   - 링크: `lotto-db` 선택

---

## 🔧 관리 명령어

### SSH 접속 후

```bash
# 컨테이너 상태 확인
sudo docker ps

# 로그 확인
sudo docker logs -f lotto-api
sudo docker logs -f lotto-bot
sudo docker logs -f lotto-db

# 컨테이너 재시작
sudo docker restart lotto-api
sudo docker restart lotto-bot

# 컨테이너 중지
sudo docker-compose down

# 이미지 업데이트
sudo docker-compose pull
sudo docker-compose up -d
```

### Container Manager UI

1. **컨테이너** 탭에서 상태 확인
2. 컨테이너 선택 → **세부 정보** → **로그** 탭
3. 컨테이너 선택 → **작업** → 재시작/중지/시작

---

## 📊 접속 확인

### API 서버
```bash
# 헬스체크
curl http://192.168.1.100:8000/health

# API 문서
http://192.168.1.100:8000/docs
```

### Telegram Bot
- Telegram에서 `/start` 명령어 전송
- `/generate` 명령어로 예측 생성 테스트

---

## 🔄 자동 업데이트 설정

### Watchtower 사용 (선택사항)

```bash
# Watchtower 컨테이너 추가
sudo docker run -d \
  --name watchtower \
  --restart unless-stopped \
  -v /var/run/docker.sock:/var/run/docker.sock \
  containrrr/watchtower \
  --interval 3600 \
  lotto-api lotto-bot
```

Watchtower가 1시간마다 이미지를 확인하고 자동으로 업데이트합니다.

---

## 🐛 트러블슈팅

### 데이터베이스 연결 실패

```bash
# 데이터베이스 로그 확인
sudo docker logs lotto-db

# 네트워크 확인
sudo docker network ls
sudo docker network inspect lotto_lotto-network

# 연결 테스트
sudo docker exec lotto-api nc -zv lotto-db 3306
```

### 권한 문제

```bash
# Docker 그룹에 사용자 추가
sudo synogroup --add docker admin

# 재로그인 후 sudo 없이 실행 가능
docker ps
```

### 포트 충돌

```bash
# 사용 중인 포트 확인
sudo netstat -tulpn | grep 8000
sudo netstat -tulpn | grep 3306

# docker-compose.yml에서 포트 변경
ports:
  - "8001:8000"  # 호스트 포트 변경
```

---

## 📱 Synology 모바일 앱

**DS file** 또는 **DS cloud** 앱으로 NAS 파일 관리 가능:
- 로그 파일 확인
- 설정 파일 수정
- 백업 관리

---

## 🔐 보안 권장사항

1. **방화벽 설정**:
   - 제어판 → 보안 → 방화벽
   - 필요한 포트만 개방 (8000, 3306)

2. **SSL/TLS 설정**:
   - 역방향 프록시 사용 (제어판 → 로그인 포털 → 고급)
   - Let's Encrypt 인증서 자동 갱신

3. **정기 백업**:
   - Hyper Backup으로 Docker 볼륨 백업
   - 데이터베이스 덤프 자동화

---

## 📞 지원

문제 발생 시:
1. 로그 확인: `sudo docker-compose logs`
2. GitHub Issues에 문의
3. Synology 커뮤니티 포럼 참고

---

## 🎉 완료!

이제 Synology NAS에서 로또 예측 시스템이 실행됩니다:
- ✅ API 서버: http://your-nas-ip:8000
- ✅ Telegram Bot: 자동 실행
- ✅ 자동화 스케줄러: 금요일 12시, 토요일 21시
