@echo off
REM Sync fork with upstream - launcher script
REM Usage:
REM   scripts\sync-fork.bat              # Normal sync
REM   scripts\sync-fork.bat --claude     # Use Claude Code for conflicts
REM   scripts\sync-fork.bat --copilot    # Use GitHub Copilot CLI for conflicts
REM   scripts\sync-fork.bat --vscode     # Open VS Code for conflicts

cd /d "%~dp0\.."

if "%1"=="--claude" (
    powershell -ExecutionPolicy Bypass -File "scripts\sync-fork.ps1" -UseClaudeCode
) else if "%1"=="--copilot" (
    powershell -ExecutionPolicy Bypass -File "scripts\sync-fork.ps1" -UseCopilot
) else if "%1"=="--vscode" (
    powershell -ExecutionPolicy Bypass -File "scripts\sync-fork.ps1" -UseVSCode
) else (
    powershell -ExecutionPolicy Bypass -File "scripts\sync-fork.ps1"
)
