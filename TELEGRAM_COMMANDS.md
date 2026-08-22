# Telegram Bot 명령어 빠른 참조

## 🚀 빠른 시작

이 봇은 **직접 배포해서 자신의 봇으로 운영**한다. 공개 봇은 제공하지 않는다.

1. `@BotFather` 에서 `/newbot` 으로 봇을 만들고 토큰 발급
2. `.env` 에 `TELEGRAM_BOT_TOKEN` 과 `TELEGRAM_ADMIN_IDS`(자신의 user ID) 설정
3. 봇 실행 후 `/start` 입력

자세한 절차는 `TELEGRAM_BOT_GUIDE.md` 참고.

## 📝 명령어 목록

| 명령어 | 설명 | 예시 |
|--------|------|------|
| `/generate` | 5개 조합 생성 (기본) | `/generate` |
| `/generate [개수]` | 원하는 개수만큼 생성 | `/generate 10` |
| `/mylist` | 이번 회차 내 번호 전체 보기 | `/mylist` |
| `/delete [순번]` | `/mylist` 의 특정 번호 삭제 | `/delete 3 5` |
| `/winning` | 최신 회차 당첨 번호 확인 | `/winning` |
| `/result` | 내 예측 결과 확인 | `/result` |
| `/result [회차]` | 특정 회차 결과 확인 | `/result 1150` |
| `/stats` | 누적 적중 통계 | `/stats` |
| `/help` | 도움말 | `/help` |

## 💡 사용 팁

- **생성 개수**: 1~20개까지 가능
- **자동 저장**: 생성한 조합은 자동으로 DB에 저장됨
- **매칭 확인**: 3개 이상 일치 시 등수 표시
- **토요일 9시**: 당첨 번호는 토요일 저녁 9시 이후 업데이트

## 🎯 사용 예시

```
/generate          → 5개 조합 생성
/generate 10       → 10개 조합 생성
/winning           → 당첨 번호 확인
/result            → 최신 회차 결과 확인
/result 1150       → 1150회차 결과 확인
/delete 3 5        → /mylist 의 3번·5번 조합 삭제
/stats             → 누적 적중 통계 확인
```

## 🔧 Bot 서버 실행

```bash
# 실행
uv run python telegram_bot_handler.py

# 또는
./run_telegram_bot.sh
```

자세한 내용은 `TELEGRAM_BOT_GUIDE.md` 참고!
