# Telegram Bot 사용 가이드

## 🤖 Bot 정보
- **Bot 이름**: Tei_Lotto_Bot
- **Bot 링크**: https://t.me/Tei_Lotto_Bot

## 📱 Bot 시작하기

### 1. Telegram에서 Bot 찾기
1. Telegram 앱 열기
2. 검색창에 `@Tei_Lotto_Bot` 입력
3. 또는 링크 클릭: https://t.me/Tei_Lotto_Bot
4. `/start` 명령어로 시작

### 2. Bot 서버 실행

```bash
# 의존성 설치 (uv)
uv sync

# Bot 실행
uv run python telegram_bot_handler.py

# 또는 스크립트 사용
./run_telegram_bot.sh
```

## 📋 사용 가능한 명령어

### 🎲 예측 생성
```
/generate
```
- 5개 조합 생성 (기본)
- 자동으로 데이터베이스에 저장됨

```
/generate 10
```
- 원하는 개수만큼 생성 (최대 20개)

### 🎯 당첨 번호 확인
```
/winning
```
- 최신 회차 당첨 번호 확인
- 회차 번호, 추첨일, 당첨 번호, 보너스 번호 표시

### 📊 결과 확인
```
/result
```
- 최신 회차에 대한 내 예측 결과 확인
- 매칭 개수별로 정렬하여 표시
- 3개 이상 일치 시 등수 표시

```
/result 1150
```
- 특정 회차 결과 확인

### ❓ 도움말
```
/help
```
- 사용 가능한 모든 명령어 안내

## 🎰 사용 예시

### 예측 생성
```
사용자: /generate 5

Bot: 🎰 로또 예측 결과 🎰

📅 생성 시각: 2024-01-15 10:30:00
🎯 예측 회차: 1151회
📊 생성 개수: 5개
💾 저장 완료: 5개

1️⃣ [3, 12, 23, 28, 35, 42]
2️⃣ [5, 14, 19, 27, 33, 41]
3️⃣ [7, 11, 22, 29, 36, 44]
4️⃣ [2, 15, 24, 31, 38, 45]
5️⃣ [8, 16, 20, 30, 37, 43]

행운을 빕니다! 🍀
```

### 당첨 번호 확인
```
사용자: /winning

Bot: 🎯 최신 회차 당첨 번호 🎯

📅 회차: 1150회
📆 추첨일: 2024-01-13

🎰 당첨 번호: [5, 12, 18, 25, 33, 41]
⭐ 보너스: 7

다음 회차는 1151회입니다.
```

### 결과 확인
```
사용자: /result

Bot: 📊 1150회차 결과 확인 📊

🎯 당첨 번호: [5, 12, 18, 25, 33, 41]
📝 내 예측: 10개

🎉 최고 매칭: 4개 일치!
   🥉 4등

📋 상세 결과:
1. [5, 12, 18, 25, 30, 40] - 4개 일치 ✅
2. [5, 12, 25, 33, 35, 42] - 4개 일치 ✅
3. [3, 12, 23, 28, 33, 41] - 3개 일치 ✅
4. [7, 11, 22, 29, 36, 44] - 0개 일치 ❌
...
```

## 🔧 설정

### 환경 변수 (.env)
```bash
# Telegram 설정
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# 데이터베이스 설정
DB_HOST=localhost
DB_USER=lotto
DB_PASSWORD=your_password
DB_NAME=lotto
DB_PORT=3306
```

## 🤖 자동화 기능

Bot 서버가 실행 중일 때 다음 작업이 자동으로 수행됩니다:

### 1. 주간 예측 자동 생성
- **실행 시간**: 매주 금요일 정오 (12:00)
- **동작**: 
  - 다음 회차 예측 10개 자동 생성
  - 데이터베이스에 자동 저장
  - 텔레그램으로 예측 결과 전송
- **알림 예시**:
  ```
  🎰 주간 로또 예측 🎰

  📅 생성 시각: 2024-01-19 12:00:00
  🎯 예측 회차: 1151회
  📊 생성 개수: 10개
  💾 저장 완료: 10개

  1️⃣ [3, 12, 23, 28, 35, 42]
  2️⃣ [5, 14, 19, 27, 33, 41]
  ...
  🔟 [8, 16, 20, 30, 37, 43]

  행운을 빕니다! 🍀
  ```

### 2. 당첨번호 자동 업데이트
- **실행 시간**: 매주 토요일 밤 9시 (21:00)
- **동작**: 
  - 최신 회차 당첨번호를 lotto.oot.kr에서 크롤링
  - 데이터베이스에 자동 저장
  - 데이터 서비스 새로고침
- **로그 기록**: 업데이트 성공/실패 로그 자동 기록

### 스케줄러 상태 확인
Bot 시작 시 로그에서 다음 실행 시간을 확인할 수 있습니다:
```
📅 스케줄러 시작됨
   - 매주 금요일 12:00: 예측 생성 및 텔레그램 전송
   - 매주 토요일 21:00: 당첨번호 업데이트
   [토요일 밤 9시 당첨번호 업데이트] 다음 실행: 2026-01-17 21:00:00
   [금요일 정오 예측 생성] 다음 실행: 2026-01-23 12:00:00
```

## 📝 주의사항

1. **Bot 서버 실행 필요**
   - Bot이 메시지를 받으려면 `telegram_bot_handler.py`가 실행 중이어야 합니다
   - 서버를 종료하면 Bot이 응답하지 않습니다

2. **데이터베이스 연결**
   - Bot이 정상 작동하려면 데이터베이스 연결이 필요합니다
   - `.env` 파일에 올바른 데이터베이스 정보를 설정하세요

3. **자동화 스케줄**
   - **금요일 정오 (12:00)**: 다음 회차 예측 10개 자동 생성 및 텔레그램 전송
   - **토요일 저녁 9시 (21:00)**: 당첨 번호 자동 업데이트
   - Bot 서버가 실행 중이어야 자동화가 작동합니다

4. **생성 개수 제한**
   - 한 번에 최대 20개까지 생성 가능합니다
   - 더 많이 필요하면 여러 번 명령어를 실행하세요

## 🚀 고급 사용법

### 백그라운드 실행
```bash
# nohup으로 백그라운드 실행
nohup python telegram_bot_handler.py > telegram_bot.log 2>&1 &

# 프로세스 확인
ps aux | grep telegram_bot_handler

# 종료
pkill -f telegram_bot_handler
```

### systemd 서비스 등록 (Linux)
```bash
# /etc/systemd/system/telegram-lotto-bot.service
[Unit]
Description=Telegram Lotto Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/lotto
ExecStart=/path/to/lotto/.venv/bin/python telegram_bot_handler.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# 서비스 시작
sudo systemctl start telegram-lotto-bot
sudo systemctl enable telegram-lotto-bot

# 상태 확인
sudo systemctl status telegram-lotto-bot
```

## 🐛 문제 해결

### Bot이 응답하지 않음
1. Bot 서버가 실행 중인지 확인
2. 환경 변수가 올바르게 설정되었는지 확인
3. 데이터베이스 연결 확인
4. 로그 확인: `tail -f telegram_bot.log`

### "알 수 없는 명령어" 메시지
- 명령어 철자 확인
- `/도움말` 명령어로 사용 가능한 명령어 확인

### 예측 생성 실패
- 데이터베이스 연결 확인
- 과거 당첨 데이터가 로드되었는지 확인

## 📞 지원

문제가 발생하면 로그를 확인하거나 개발자에게 문의하세요.

행운을 빕니다! 🍀
