#!/bin/bash
# Telegram Bot용 entrypoint

set -e

# 데이터베이스 연결 대기
echo "데이터베이스 연결 대기 중..."
until nc -z -v -w30 $DB_HOST $DB_PORT; do
  echo "데이터베이스($DB_HOST:$DB_PORT)에 연결할 수 없습니다. 대기 중..."
  sleep 2
done
echo "데이터베이스 연결 준비 완료!"

# 환경 변수 확인
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
  echo "⚠️  TELEGRAM_BOT_TOKEN이 설정되지 않았습니다."
  exit 1
fi

if [ -z "$TELEGRAM_CHAT_ID" ]; then
  echo "⚠️  TELEGRAM_CHAT_ID가 설정되지 않았습니다."
  exit 1
fi

echo "✅ Telegram Bot 설정 확인 완료"
echo "📅 스케줄러 활성화:"
echo "   - 금요일 12:00: 예측 생성 및 전송"
echo "   - 토요일 21:00: 당첨번호 업데이트"

# 명령어 실행
exec "$@"
