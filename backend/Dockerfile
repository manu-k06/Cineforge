FROM python:3.12-slim

# Install FFmpeg, FFprobe and curl (for health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face Spaces runs as user with UID 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PORT=7860

WORKDIR $HOME/app

# Install python dependencies
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy backend application source code
COPY --chown=user . .

EXPOSE 7860

# Run FastAPI via uvicorn binding to 0.0.0.0 and dynamic PORT
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
