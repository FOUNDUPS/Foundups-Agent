#!/bin/bash
# scripts/start_ironclaw_services.sh
# Auto-Remediates the OpenClaw Supervisor by booting required LLM runtimes

echo "[IronClaw] Verifying requisite runtimes for OpenClaw Supervisor..."

# 1. Check if Ollama is running
if pgrep -x "ollama" > /dev/null
then
    echo "[IronClaw] Ollama is already running."
else
    echo "[IronClaw] Ollama not found. Attempting to start Ollama..."
    ollama serve > /dev/null 2>&1 &
    sleep 3
fi

# 2. Check if Docker is running
if docker info > /dev/null 2>&1
then
    echo "[IronClaw] Docker engine is running."
else
    echo "[IronClaw] Docker engine not running. Attempting to start Docker daemon..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open -a Docker
    else
        sudo systemctl start docker
    fi
    echo "[IronClaw] Waiting for Docker to initialize..."
    sleep 10
fi

echo "[IronClaw] Services initialization routine complete."
exit 0
