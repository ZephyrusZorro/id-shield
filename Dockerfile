# ID-SHIELD — production container (UI + API in one process)

# --- Stage 1: Build Frontend ---
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --prefer-offline --no-audit || npm install
COPY frontend/ ./
RUN npm run build

# --- Stage 2: Runtime Backend & Unified Server ---
FROM python:3.11-slim

# Tesseract OCR for the pipeline; runtime libs for OpenCV headless
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Ensure runtime directories exist and have open permissions for non-root containers
RUN mkdir -p /app/data /app/backend/data /app/data/uploads /app/backend/data/uploads && chmod -R 777 /app

ENV DATABASE_URL=sqlite:////app/data/idshield.db
ENV UPLOAD_DIR=/app/data/uploads
ENV CORS_ORIGINS=""
ENV LOG_LEVEL=INFO

EXPOSE 7860 8000
WORKDIR /app/backend

# Runs on injected $PORT or defaults to 7860 (standard for Hugging Face / cloud containers)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
