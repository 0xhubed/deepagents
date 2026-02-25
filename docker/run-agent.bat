@echo off
REM DeepAgents CLI Launcher for Windows
REM Double-click this file to start the agent

SETLOCAL EnableDelayedExpansion

REM ============================================
REM CONFIGURATION - Edit these as needed
REM ============================================

REM Workspace folder on Windows (where your files are)
SET WORKSPACE=C:\agent-workspace

REM Ollama server configuration
SET OLLAMA_BASE_URL=http://10.8.137.71:11435
SET OLLAMA_MODEL=GLM-4.7-flash

REM ============================================
REM DO NOT EDIT BELOW THIS LINE
REM ============================================

echo.
echo  ====================================
echo   DeepAgents CLI Launcher
echo  ====================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERROR] Docker is not running!
    echo Please start Docker Desktop and try again.
    echo.
    pause
    exit /b 1
)

REM Check if workspace exists, create if not
IF NOT EXIST "%WORKSPACE%" (
    echo Creating workspace folder: %WORKSPACE%
    mkdir "%WORKSPACE%"
    mkdir "%WORKSPACE%\input"
    mkdir "%WORKSPACE%\output"
    mkdir "%WORKSPACE%\projects"
    echo Created workspace with input/, output/, projects/ subdirectories.
    echo.
)

REM Build image (uses cache if unchanged)
echo Building Docker image (cached if unchanged)...
echo.
cd /d "%~dp0"
docker build -t deepagents-cli:latest -f Dockerfile ..
IF ERRORLEVEL 1 (
    echo [ERROR] Failed to build Docker image!
    pause
    exit /b 1
)
echo.
echo Build complete!
echo.

REM Display configuration
echo Configuration:
echo   Workspace:  %WORKSPACE%
echo   Ollama URL: %OLLAMA_BASE_URL%
echo   Model:      %OLLAMA_MODEL%
echo.
echo Your files in %WORKSPACE% are accessible at /workspace inside the agent.
echo.
echo Starting DeepAgents CLI...
echo ----------------------------------------
echo.

REM Run the container (loads env vars from .env file + explicit overrides)
docker run -it --rm ^
    -v "%WORKSPACE%:/workspace" ^
    --env-file "%~dp0.env" ^
    -e OLLAMA_BASE_URL=%OLLAMA_BASE_URL% ^
    -e OLLAMA_MODEL=%OLLAMA_MODEL% ^
    -w /workspace ^
    deepagents-cli:latest

echo.
echo ----------------------------------------
echo DeepAgents CLI session ended.
echo.
pause
