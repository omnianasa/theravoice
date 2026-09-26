FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY config ./config

RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .

ENV THERAVOICE_ENV=production
EXPOSE 8000

CMD ["uvicorn", "theravoice.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
