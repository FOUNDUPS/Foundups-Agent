# SSE Server for FoundUps Cube Events
# Deploy to Cloud Run: gcloud run deploy sse-foundups --source .

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements-sse.txt .
# Self-contained hash bootstrap: this image uses a module-local build context.
RUN python -m pip --isolated install --upgrade --no-deps --require-hashes \
    'https://files.pythonhosted.org/packages/3f/06/3e4420302363fbb71be3c7f35ce042f54bfca330e3e66b3a2e3c4cca579f/pip-26.2.2-py3-none-any.whl#sha256=fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70' \
    'https://files.pythonhosted.org/packages/c4/51/29046e48f693c54e5b7412216d447a1d8362c9653148d98c02cdf65fa733/certifi-2026.10.19-py3-none-any.whl#sha256=42d35340cc5b9ba78e818ddbff0c5b1c2b779de448a340fd1b989f5fa8670e1b' \
    && python -m pip install --no-cache-dir -r requirements-sse.txt

# Copy application code
COPY sse_server.py .

# Cloud Run uses PORT env var
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Run with simulate mode by default (FAMDaemon not available in Cloud Run)
CMD ["python", "sse_server.py", "--simulate"]
