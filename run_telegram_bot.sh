#!/bin/bash

# Telegram Bot 실행 스크립트

echo "🤖 Telegram Bot 시작 중..."
echo ""

# 가상환경 활성화 (필요한 경우)
if [ -d ".venv" ]; then
    echo "가상환경 활성화..."
    source .venv/bin/activate
fi

# 필요한 패키지 설치 확인
echo "패키지 확인 중..."
pip install python-telegram-bot==21.10 --quiet

echo ""
echo "✅ 준비 완료!"
echo ""
echo "사용 가능한 명령어:"
echo "  /generate - 5개 조합 생성"
echo "  /generate 10 - 10개 조합 생성"
echo "  /winning - 최신 회차 당첨 번호 확인"
echo "  /result - 내 예측과 당첨 번호 매칭 확인"
echo "  /help - 명령어 안내"
echo ""
echo "Bot 실행 중... (Ctrl+C로 종료)"
echo ""

# Bot 실행
python telegram_bot_handler.py
