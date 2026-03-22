# ── Market Pulse Terminal — Render.com Dockerfile ─────────────────────────────
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

# Run with gunicorn — 1 worker on free tier (limited CPU), more threads for concurrency
# Timeout raised to 300s to handle slow yfinance fetches on cold start
CMD ["gunicorn", "--bind", "0.0.0.0:8050", "--workers", "1", "--threads", "8", "--timeout", "300", "--keep-alive", "5", "main:server"]
