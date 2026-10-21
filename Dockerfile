# Use an official Python runtime as a parent image
FROM python:3.10-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

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
