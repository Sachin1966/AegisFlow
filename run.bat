@echo off
setlocal EnableDelayedExpansion
title AegisFlow - Real-Time Payment Fraud Scoring and Agentic AML Platform
cd /d "%~dp0"

echo ===============================================================================
echo                 AegisFlow Real-Time Payment Fraud Scoring
echo                 and Agentic Anti-Money-Laundering Platform
echo ===============================================================================
echo.

:: 1. Check Virtual Environment or Python
if exist ".venv\Scripts\python.exe" (
    echo [*] Found virtual environment in .venv
    set "PYTHON_EXE=.venv\Scripts\python.exe"
    call .venv\Scripts\activate.bat
) else (
    where python >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        echo [*] Using system Python
        set "PYTHON_EXE=python"
    ) else (
        echo [!] ERROR: Python 3.10+ was not found in PATH or in .venv.
        echo Please install Python 3.10 or higher and add it to your PATH.
        pause
        exit /b 1
    )
)

:: 2. Check Environment Configuration (.env)
if not exist ".env" (
    if exist ".env.example" (
        echo [*] Creating .env from .env.example template...
        copy /Y .env.example .env >nul
    )
)

:: 3. Check Local Ollama Daemon Status
curl.exe -s --connect-timeout 2 http://localhost:11434/api/tags >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    echo [*] Ollama LLM Daemon is ONLINE on localhost:11434 [GenAI Reports Active]
) else (
    echo [i] Ollama LLM Daemon is OFFLINE [Deterministic regulatory synthesis active]
)

echo.
echo Select an option to launch:
echo   [1] Launch AegisFlow Unified Platform (API Gateway + AML Workbench + ML Scoring)
echo   [2] Launch with Vite Frontend Dev Server (Frontend :3000 + Backend :8000)
echo   [3] Start Containerized Infrastructure (Docker Compose: Redis, Postgres, Qdrant)
echo   [4] Run Automated Unit and Integration Test Suite (pytest)
echo   [5] Pull Recommended Ollama Model (llama3.2:latest)
echo   [6] Exit
echo.

choice /C 123456 /T 4 /D 1 /M "Select option (Auto-starting [1] in 4 seconds): "
set "CHOICE_VAL=!ERRORLEVEL!"

if "!CHOICE_VAL!"=="1" goto launch_unified
if "!CHOICE_VAL!"=="2" goto launch_vite
if "!CHOICE_VAL!"=="3" goto launch_docker
if "!CHOICE_VAL!"=="4" goto run_tests
if "!CHOICE_VAL!"=="5" goto pull_ollama
if "!CHOICE_VAL!"=="6" goto exit_script

:launch_unified
echo.
echo ===============================================================================
echo [*] Launching AegisFlow Unified Server on http://localhost:8000 ...
echo [*] Opening browser to http://localhost:8000 ...
echo ===============================================================================
start "" http://localhost:8000
"!PYTHON_EXE!" run_server.py
goto end

:launch_vite
echo.
echo ===============================================================================
echo [*] Starting Backend Unified Server in new window...
start "AegisFlow Backend" cmd /c ""!PYTHON_EXE!" run_server.py"
timeout /t 2 >nul
echo [*] Starting Vite Frontend on http://localhost:3000 ...
start "" http://localhost:3000
cd frontend
call npm run dev
cd ..
goto end

:launch_docker
echo.
echo ===============================================================================
echo [*] Starting Docker Compose services...
echo ===============================================================================
docker-compose up -d
echo [*] Docker services launched. You can now run option [1] to start the platform.
pause
goto end

:run_tests
echo.
echo ===============================================================================
echo [*] Running Pytest Unit and Integration Test Suite...
echo ===============================================================================
"!PYTHON_EXE!" -m pytest tests/unit -v
pause
goto end

:pull_ollama
echo.
echo ===============================================================================
echo [*] Pulling recommended model llama3.2:latest into local Ollama...
echo ===============================================================================
ollama pull llama3.2:latest
pause
goto end

:exit_script
exit /b 0

:end
endlocal
