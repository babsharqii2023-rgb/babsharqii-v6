FROM python:3.12-slim

LABEL maintainer="BABSHARQII"
LABEL version="40.0"
LABEL description="BABSHARQII v40.0 Mamoun — Living AGI Backend"

WORKDIR /app

# Install system dependencies (minimal — no docker.io in production)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p /app/data /app/logs /app/sandbox /app/data/genome_archive /app/backups

# Expose API port
EXPOSE 8000

# Health check using urllib (no extra dependency needed)
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run with uvicorn
CMD ["uvicorn", "mamoun.main:app", "--host", "0.0.0.0", "--port", "8000"]
