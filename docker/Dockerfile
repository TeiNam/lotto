# Multi-stage build for optimized image size
FROM python:3.13-slim AS builder

# uv 바이너리만 가져온다 (빌더 스테이지에서만 사용)
COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /bin/uv

WORKDIR /app

# uv 설정
#  - UV_PROJECT_ENVIRONMENT: supervisord.conf 가 참조하는 /venv 경로에 그대로 생성
#  - UV_COMPILE_BYTECODE: 런타임 첫 import 를 빠르게
#  - UV_PYTHON_DOWNLOADS=never: 베이스 이미지의 python 을 그대로 사용
ENV UV_PROJECT_ENVIRONMENT=/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

# 의존성만 먼저 설치 (소스가 바뀌어도 이 레이어는 캐시된다)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Runtime stage
FROM python:3.13-slim

WORKDIR /app

# 런타임 패키지 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    netcat-traditional \
    tzdata \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 시간대 설정 (KST)
ENV TZ=Asia/Seoul
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 파이썬 환경 설정
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random

# 빌더 스테이지에서 가상 환경 복사
COPY --from=builder /venv /venv
ENV PATH="/venv/bin:$PATH"

# 소스 코드 복사
COPY api/ ./api/
COPY config/ ./config/
COPY database/ ./database/
COPY models/ ./models/
COPY services/ ./services/
COPY utils/ ./utils/
COPY telegram_bot_handler.py .

# Supervisor 설정 파일 복사
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# 실행 스크립트 복사 및 권한 설정
COPY docker/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# 로그 디렉토리 생성
RUN mkdir -p /var/log/supervisor logs

# 헬스체크 (API 서버 확인)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 포트 노출
EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["/venv/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
