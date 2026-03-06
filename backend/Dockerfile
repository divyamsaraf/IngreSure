# Use python 3.10 slim
FROM python:3.10-slim

# Install system dependencies (for PaddleOCR/OpenCV)
# On newer Debian (trixie), libgl1-mesa-glx is replaced by libgl1.
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first to leverage cache
COPY requirements.txt .

# Upgrade packaging tooling to prefer/install manylinux wheels cleanly
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (FastAPI default)
EXPOSE 8000

# Long-running server: do not use --reload in production; keep-alive for proxies
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "75"]
