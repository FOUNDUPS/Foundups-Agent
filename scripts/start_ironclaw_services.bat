@echo off
REM scripts\start_ironclaw_services.bat
REM Auto-Remediates the OpenClaw Supervisor by booting required LLM runtimes
echo [IronClaw] Verifying requisite runtimes for OpenClaw Supervisor...

REM 1. Check if Ollama is running
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I /N "ollama.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo [IronClaw] Ollama is already running.
) else (
    echo [IronClaw] Ollama not found. Attempting to start Ollama...
    REM Using start to boot it in the background
    start "" "ollama" serve
    timeout /t 3 /nobreak > NUL
)

REM 2. Check if Docker is running (Optional depending on precise nano-claw needs, but requested)
docker info >NUL 2>&1
if "%ERRORLEVEL%"=="0" (
    echo [IronClaw] Docker engine is running.
) else (
    echo [IronClaw] Docker engine not running. Attempting to start Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    REM Wait for docker to begin initializing
    echo [IronClaw] Waiting for Docker to initialize (this may take a moment)...
    timeout /t 10 /nobreak > NUL
)

echo [IronClaw] Services initialization routine complete.
exit /b 0
