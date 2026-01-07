FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy 8825_core (when building from repo root)
COPY users/justin_harmon/8825-Jh/8825_core /app/8825_core

# Copy backend requirements and install
COPY apps/maestra.8825.systems/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY apps/maestra.8825.systems/backend/ .

# Add 8825_core to PYTHONPATH
ENV PYTHONPATH="/app/8825_core:${PYTHONPATH}"

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5).read()" || exit 1

# Run the application
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
