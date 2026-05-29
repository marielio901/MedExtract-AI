FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FLASK_ENV=production \
    PORT=5000 \
    DATABASE_URL=sqlite:////app/data/medextract_ai.db \
    UPLOAD_ORIGINAL_FOLDER=/app/uploads/original \
    UPLOAD_PROCESSED_FOLDER=/tmp/medextract-processed \
    PADDLE_PDX_CACHE_HOME=/app/.paddlex-cache

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        libsm6 \
        libxext6 \
        libxrender1 \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY . .

RUN chmod +x scripts/docker-entrypoint.sh \
    && mkdir -p /app/data /app/uploads/original /app/.paddlex-cache /tmp/medextract-processed \
    && useradd --create-home --uid 10001 medextract \
    && chown -R medextract:medextract /app

USER medextract

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT}/healthz" || exit 1

ENTRYPOINT ["scripts/docker-entrypoint.sh"]
CMD ["web"]
