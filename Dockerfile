# Use an official Python runtime as a parent image
FROM python:3.10-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
# The pinned llama-cpp-python builds native C/C++ code on the slim image.
# Install and remove the compiler in one layer; retain its runtime libraries.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential libgomp1 libstdc++6 \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . .

# The root .dockerignore excludes local credentials and runtime state before COPY.
# Supply credentials at runtime using a read-only mount or Docker secrets.
# Example: docker run -v "$(pwd)/credentials:/app/credentials:ro" ...
# Mount writable memory separately when persistence is required.
# These directories are mount points, not permission to bake secrets into layers.
RUN mkdir -p /app/credentials && mkdir -p /app/memory

# Command to run the application
CMD ["python", "main.py"]
