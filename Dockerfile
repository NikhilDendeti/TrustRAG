# syntax=docker/dockerfile:1

# --- Stage 1: build the React frontend -------------------------------------
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Stage 2: Python runtime -------------------------------------------------
FROM python:3.12-slim AS runtime
WORKDIR /app

# Keep Python output unbuffered so logs show up immediately on Railway.
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements-server.txt .
RUN pip install --no-cache-dir -r requirements-server.txt

# App code (see .dockerignore for what's excluded: secrets, local venvs,
# node_modules, and local runtime state under data/).
COPY . .

# The built frontend from stage 1 — server.py serves this directly as a
# single process alongside the API (see server.py's static-mount section).
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Railway injects $PORT at runtime; default 8000 for local `docker run`.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT}"]
