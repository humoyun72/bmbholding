FROM python:3.12-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create uploads directory
RUN mkdir -p /app/uploads

EXPOSE 8000

# BOT_MODE=polling bo'lganda 1 worker, webhook bo'lganda 2 worker
CMD ["sh", "-c", "if [ \"$BOT_MODE\" = 'polling' ]; then uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1; else uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2; fi"]
