# ── Market Pulse Terminal — Fly.io Dockerfile ─────────────────────────────────
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (needed by some Python packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for quantlab run outputs
RUN mkdir -p quantlab_runs

# Expose the port Fly.io will route to
EXPOSE 8050

# Run with gunicorn — 2 workers, threads for concurrent users
# main:server references the Flask server object inside main.py
CMD ["gunicorn", "--bind", "0.0.0.0:8050", "--workers", "2", "--threads", "4", "--timeout", "120", "main:server"]
