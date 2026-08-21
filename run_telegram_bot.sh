#!/bin/bash

# Telegram Bot 실행 스크립트

set -e

echo "🤖 Telegram Bot 시작 중..."
echo ""

# uv 설치 확인
if ! command -v uv >/dev/null 2>&1; then
    echo "❌ uv 가 설치되어 있지 않습니다."
    echo "   설치: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# 의존성 동기화 (uv.lock 기준, 없으면 .venv 자동 생성)
echo "패키지 동기화 중..."
uv sync --frozen

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
uv run python telegram_bot_handler.py
