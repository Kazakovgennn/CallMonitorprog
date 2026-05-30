@echo off
chcp 65001 >nul
title CallMonitor Setup

echo ========================================
echo    CallMonitor Full Setup
echo ========================================
echo.

cd /d "%~dp0"

:: ========================================
:: 1. Check/Install Ollama
:: ========================================
echo [1/5] Checking Ollama...

where ollama >nul 2>nul
if %errorlevel% equ 0 goto :ollama_installed

reg query "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Ollama" >nul 2>nul
if %errorlevel% equ 0 goto :ollama_installed

echo Ollama not found. Downloading installer...
powershell -Command "Invoke-WebRequest -Uri 'https://ollama.com/download/OllamaSetup.exe' -OutFile '%TEMP%\OllamaSetup.exe'"

if %errorlevel% neq 0 (
    echo ERROR: Failed to download Ollama
    pause
    exit /b
)

echo Installing Ollama...
start /wait %TEMP%\OllamaSetup.exe /S

if %errorlevel% neq 0 (
    echo ERROR: Ollama installation failed
    pause
    exit /b
)

:ollama_installed

:: ========================================
:: 2. Download Qwen model
:: ========================================
echo.
echo [2/5] Checking Qwen model...

timeout /t 3 /nobreak >nul

ollama list | findstr "qwen2.5:7b" >nul 2>nul
if %errorlevel% equ 0 goto :model_installed

echo Downloading qwen2.5:7b (approx 4.5 GB)...
echo This may take 10-30 minutes.
ollama pull qwen2.5:7b

if %errorlevel% neq 0 (
    echo ERROR: Failed to download model
    pause
    exit /b
)

:model_installed

:: ========================================
:: 3. Install Python packages
:: ========================================
echo.
echo [3/5] Installing Python packages...

if not exist "core\requirements.txt" (
    echo ERROR: core\requirements.txt not found
    pause
    exit /b
)

pip install -r core\requirements.txt

if %errorlevel% neq 0 (
    echo WARNING: pip install failed, trying with python -m pip...
    python -m pip install -r core\requirements.txt
)

echo Python packages installed.

:: ========================================
:: 4. Setup Windows Scheduler
:: ========================================
echo.
echo [4/5] Configuring Windows Scheduler...

set MAIN_PATH=%~dp0whisper_stt.py

if not exist "%MAIN_PATH%" (
    echo ERROR: %MAIN_PATH% not found
    pause
    exit /b
)

schtasks /delete /tn "CallMonitor" /f >nul 2>nul

schtasks /create /tn "CallMonitor" ^
    /tr "python \"%MAIN_PATH%\"" ^
    /sc minute ^
    /mo 30 ^
    /f >nul 2>nul

if %errorlevel% neq 0 (
    echo WARNING: Failed to create scheduled task. Run as Administrator.
) else (
    echo Scheduled task created.
)

:: ========================================
:: 5. Done
:: ========================================
echo.
echo ========================================
echo    Setup Complete!
echo ========================================
echo.
echo Place audio files in: data\incoming\
echo The script will run every 30 minutes.
echo Reports will be sent to Telegram.
echo.
echo To run manually: whisper_stt.py
echo.
pause