# ── Build stage ────────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

# Security: run as non-root
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Install dependencies first (layer cache optimization)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set ownership
RUN chown -R appuser:appuser /app

USER appuser

# ── Runtime ────────────────────────────────────────────────────────────────
# Cloud Run injects PORT env var; gunicorn binds to it
ENV PORT=8080
EXPOSE 8080

# Use gunicorn for production; 2 workers is appropriate for Cloud Run's
# single-core default (1 vCPU). Increase if you scale up.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", \
     "--timeout", "120", "--log-level", "info", "app:app"]
