#!/bin/bash
# docker/docker-entrypoint.sh

set -e

# 데이터베이스 연결 대기
echo "데이터베이스 연결 대기 중..."
until nc -z -v -w30 $DB_HOST $DB_PORT; do
  echo "데이터베이스($DB_HOST:$DB_PORT)에 연결할 수 없습니다. 대기 중..."
  sleep 2
done
echo "데이터베이스 연결 준비 완료!"

# 환경 변수 확인
if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "ANTHROPIC_API_KEY가 설정되지 않았습니다."
  exit 1
fi

# 필요한 디렉토리 생성
mkdir -p logs

# 명령어 실행
exec "$@"