FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install poppler-utils for pdf2image
RUN apt-get update && apt-get install -y poppler-utils && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY init-storage.sh /app/init-storage.sh

# Make init script executable
RUN chmod +x /app/init-storage.sh

# Create storage directory with proper permissions
RUN mkdir -p /app/storage && chmod -R 777 /app/storage

# Run init script on container start (will be overridden by docker-compose command if needed)
CMD ["/bin/bash", "-c", "/app/init-storage.sh && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

