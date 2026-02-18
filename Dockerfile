FROM python:3.11-slim

# Install system dependencies for PostGIS, Redis, and Celery
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    gdal-bin \
    libgdal-dev \
    python3-gdal \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Copy entrypoint script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Expose port
EXPOSE 8000

# Note: ENTRYPOINT is NOT set here - it's set per-service in docker-compose.yml
# This allows the web service to use the entrypoint script for migrations/collectstatic
# Default command (can be overridden in docker-compose)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

