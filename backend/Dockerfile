FROM python:3.12-slim

# Install FFmpeg, FFprobe and curl (for health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application source code
COPY . .

# Render exposes PORT environment variable (defaults to 8000)
ENV PORT=8000
EXPOSE ${PORT}

# Run FastAPI via uvicorn binding to 0.0.0.0 and dynamic PORT
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
