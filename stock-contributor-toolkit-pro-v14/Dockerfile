# Free hosting on Render.com (free tier: 750 hrs/month, sleeps when idle)
FROM python:3.12-slim

# FFmpeg (SVG->Video + Motion Studio) + Cairo (cairosvg) + fonts (drawtext titles)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libcairo2 libpango-1.0-0 libgdk-pixbuf-2.0-0 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Render provides $PORT
CMD python app.py --no-browser --host 0.0.0.0 --port ${PORT:-5000}
