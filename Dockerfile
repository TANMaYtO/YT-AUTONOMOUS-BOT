# Cronus Python Backend & Multi-Tenant Scheduler
FROM python:3.10-slim

# Install system dependencies required for FFmpeg video processing and ONNX runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgomp1 \
    libass9 \
    fonts-noto \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Ensure working directories exist
RUN mkdir -p assets/temp assets/characters assets/backgrounds assets/music models/kokoro

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Run the SaaS master scheduler 24/7
CMD ["python", "master_scheduler.py"]
