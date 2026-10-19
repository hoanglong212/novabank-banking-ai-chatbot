FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    LLM_PROVIDER=mock GATEWAY_MODE=local \
    FRONTEND_DIST=/app/frontend/dist DB_PATH=/data/novabank_demo.sqlite3
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --uid 10001 --create-home demo \
    && mkdir /data && chown demo:demo /data
COPY backend/app/ ./app/
COPY --from=frontend /build/dist /app/frontend/dist
USER demo
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/ready', timeout=8)"
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
