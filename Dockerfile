FROM node:22-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    REFLEX_USE_NPM=true

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN python3 -m pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY . .
RUN python3 -m reflex init \
    && npm ci --prefix .web

CMD ["sh", "-c", "python3 -m reflex run --env prod --frontend-port ${PORT:-3000} --backend-port ${PORT:-3000} --backend-host 0.0.0.0"]
