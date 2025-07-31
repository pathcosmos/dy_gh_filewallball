# 멀티스테이지 Dockerfile - FastAPI 애플리케이션 최적화
# 빌드 스테이지
FROM python:3.11-slim as builder

WORKDIR /app

# 시스템 패키지 업데이트 및 빌드 도구 설치
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# uv 설치
RUN pip install --no-cache-dir uv

# 의존성 파일 복사 (레이어 캐싱 최적화)
COPY pyproject.toml uv.lock README.md ./

# Python 의존성 설치
RUN uv sync --frozen

# 런타임 스테이지
FROM python:3.11-slim as runtime

# 보안 강화: non-root 사용자 생성
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

WORKDIR /app

# 런타임에 필요한 시스템 패키지만 설치 (최적화)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && apt-get autoremove -y

# uv 설치 (런타임에서도 필요)
RUN pip install --no-cache-dir uv

# 빌드 스테이지에서 Python 환경 복사
COPY --from=builder /app/.venv /app/.venv

# 빌드 시 주입 가능한 환경 변수
ARG DATABASE_URL
ARG REDIS_URL
ARG SECRET_KEY

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    LOG_LEVEL=INFO \
    WORKERS=1 \
    TIMEOUT=30 \
    MAX_CONNECTIONS=100

# 애플리케이션 코드 복사
COPY app/ ./app/

# 업로드 디렉토리 및 uv 캐시 디렉토리 생성 및 권한 설정
RUN mkdir -p /app/uploads && \
    mkdir -p /home/appuser/.cache/uv && \
    chown -R appuser:appuser /app && \
    chown -R appuser:appuser /home/appuser && \
    chmod 755 /app/uploads

# 포트 노출
EXPOSE 8000

# 헬스체크 추가 (최적화된 설정)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

# non-root 사용자로 전환
USER appuser

# 애플리케이션 실행
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
