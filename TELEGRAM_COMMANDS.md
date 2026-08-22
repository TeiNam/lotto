# Telegram Bot 명령어 빠른 참조

## 🚀 빠른 시작

1. Bot 찾기: https://t.me/Tei_Lotto_Bot
2. `/start` 입력
3. 명령어 사용!

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
