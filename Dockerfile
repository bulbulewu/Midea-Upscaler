# Media Toolkit Pro V3 — Multi-Marketplace Engine Dockerfile
# Optimized for free hosting on Render.com & cloud containers
# Made By Munajat International

FROM python:3.11-slim

# Install system dependencies & FFmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Ensure upload/output directories exist
RUN mkdir -p uploads outputs

# Render dynamically sets $PORT (defaults to 5000)
ENV PORT=5000
EXPOSE 5000

CMD python app.py --no-browser --host 0.0.0.0 --port ${PORT}
