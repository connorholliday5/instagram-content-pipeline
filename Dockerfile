FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
  && rm -rf /var/lib/apt/lists/*

COPY . /app

RUN pip install --no-cache-dir -U pip \
 && pip install --no-cache-dir -e ".[dev]"

# Keep container alive for docker compose up; we use `docker compose run` for commands
CMD ["sh", "-lc", "tail -f /dev/null"]
