# Use a slim Python image for smaller size
FROM python:3.11-slim

# Make logs show up immediately
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# System dependencies:
# - ffmpeg: helps with mp4 encode/decode reliability
# - libglib2.0-0, libsm6, libxext6, libxrender1: common OpenCV runtime deps in slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Default command (you can override in docker-compose)
CMD ["python", "main.py", "--video", "/app/input/sample_video_clip.mp4", "--output", "/app/output", "--config", "/app/config.ini"]
