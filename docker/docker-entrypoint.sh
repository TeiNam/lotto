#!/bin/bash
# API 서버용 entrypoint

set -e

# 데이터베이스 연결 대기
echo "데이터베이스 연결 대기 중..."
until nc -z -v -w30 $DB_HOST $DB_PORT; do
  echo "데이터베이스($DB_HOST:$DB_PORT)에 연결할 수 없습니다. 대기 중..."
  sleep 2
done
echo "데이터베이스 연결 준비 완료!"

# 환경 변수 확인 (선택적)
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
  echo "⚠️  TELEGRAM_BOT_TOKEN이 설정되지 않았습니다. (알림 기능 비활성화)"
fi

echo "✅ API 서버 시작 준비 완료"

# 명령어 실행
exec "$@"