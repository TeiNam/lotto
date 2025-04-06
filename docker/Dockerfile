# docker/Dockerfile
FROM python:3.13.2-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 설치 및 시간대 설정
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
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
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

# 가상 환경 생성 (선택 사항)
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

# 의존성 설치를 위한 requirements.txt 복사
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 소스 코드 복사
COPY . .

# 실행 스크립트 복사 및 권한 설정
COPY docker/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# 실행할 기본 명령어
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]