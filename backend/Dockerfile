FROM docker.io/library/python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

# Bagimliliklarin tek kaynagi pyproject.toml -- burada liste tekrarlama.
# Bos app/ paketi, kod degistiginde bu katmanin cache'ini bozmamak icin.
COPY pyproject.toml requirements.lock ./
RUN mkdir -p app && touch app/__init__.py \
 && pip install --no-cache-dir -c requirements.lock -e ".[dev]"

COPY . .
