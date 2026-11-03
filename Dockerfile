FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    REFLEX_USE_NPM=true

RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN python -m reflex init \
    && npm ci --prefix .web

CMD ["sh", "-c", "python -m reflex run --env prod --frontend-port ${PORT:-3000} --backend-port ${PORT:-3000} --backend-host 0.0.0.0"]
