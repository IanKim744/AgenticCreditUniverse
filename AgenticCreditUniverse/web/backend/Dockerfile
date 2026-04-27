# HuggingFace Spaces (Docker SDK) 배포용.
# Build context: HF Space git repo 루트 (Dockerfile 옆에 backend/, output/, _workspace/ 가 같이 있음).
# Spaces 무료 티어는 영구 디스크 없음 — 데이터는 baked-in, 쓰기는 ephemeral.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 의존성 먼저 설치 — 코드 변경 시 캐시 재사용
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# 백엔드 소스
COPY backend /app

# 초기 데이터 (baked-in, 컨테이너 라이프타임 동안 사용)
COPY output     /app/output
COPY _workspace /app/_workspace

# HF Spaces 가 컨테이너를 non-root 1000 유저로 실행 → /app 내 쓰기 권한 필요.
# 검수 확정 시 review_status.json + Excel 갱신 + output/backup 자동 백업 생성됨.
RUN chown -R 1000:1000 /app
USER 1000

ENV PYTHONPATH=/app \
    WORKSPACE_DIR=/app/_workspace \
    EXCEL_PATH="/app/output/26.1H 유니버스.xlsx" \
    EXCEL_BACKUP_DIR=/app/output/backup

EXPOSE 8787
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8787"]
