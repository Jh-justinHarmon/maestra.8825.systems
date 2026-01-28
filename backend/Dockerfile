FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy system dependencies (from repo root context)
COPY system ./system

# Copy backend requirements and install
COPY apps/maestra.8825.systems/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY apps/maestra.8825.systems/backend/ .

# Add system and agents to PYTHONPATH
ENV PYTHONPATH="/app:/app/system:/app/system/agents:${PYTHONPATH}"

# Minimal mode flag (set to true to bypass system dependencies)
# Keep minimal code paths available but run in full mode
ENV MAESTRA_MINIMAL_MODE=false

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5).read()" || exit 1

# Run the application
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
