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

ENV DATABASE_URL=sqlite:///./data/idshield.db
ENV UPLOAD_DIR=./data/uploads
ENV CORS_ORIGINS=""
ENV LOG_LEVEL=INFO

EXPOSE 8000
WORKDIR /app/backend

# PORT is honored by platforms that inject it (Render, Fly, Cloud Run...)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
