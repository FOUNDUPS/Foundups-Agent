# Use an official Python runtime as a parent image
FROM python:3.10-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt requirements-trust-bootstrap.txt ./
RUN python -m pip --isolated install --upgrade --no-deps --require-hashes -r requirements-trust-bootstrap.txt \
    && python -m pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# --- Security Note ---
# The 'credentials' directory containing sensitive OAuth tokens
# SHOULD NOT be copied into the image in production.
# Mount it as a volume or use Docker secrets instead.
# For local dev, ensure credentials dir exists before building or running.
# Example: docker run -v $(pwd)/credentials:/app/credentials ...
# Ensure the 'memory' directory is also mounted as a volume to persist logs.
# Example: docker run -v $(pwd)/memory:/app/memory ...

# Ensure credentials and memory directories exist in the container context
# These will be mount points for volumes
RUN mkdir -p /app/credentials && mkdir -p /app/memory

# Command to run the application
CMD ["python", "main.py"]
