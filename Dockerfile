FROM node:22-alpine AS dashboard-build

WORKDIR /dashboard
COPY dashboard/package*.json ./
RUN npm ci
COPY dashboard/index.html ./index.html
COPY dashboard/styles.css ./styles.css
COPY dashboard/vite.config.js ./vite.config.js
COPY dashboard/src ./src
RUN npm run build

FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY config ./config
COPY --from=dashboard-build /dashboard/dist ./dashboard/dist

RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .

ENV THERAVOICE_ENV=production
EXPOSE 8000

CMD ["uvicorn", "theravoice.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
