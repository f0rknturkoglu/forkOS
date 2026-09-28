FROM docker.io/library/node:22-bookworm-slim AS node-runtime

FROM docker.io/library/python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node
RUN apt-get update && apt-get install -y --no-install-recommends git \
 && rm -rf /var/lib/apt/lists/*

# Bagimliliklarin tek kaynagi pyproject.toml -- burada liste tekrarlama.
# Bos app/ paketi, kod degistiginde bu katmanin cache'ini bozmamak icin.
COPY pyproject.toml requirements.lock ./
RUN mkdir -p app && touch app/__init__.py \
 && pip install --no-cache-dir -c requirements.lock -e ".[dev]"

COPY . .
