@echo off
setlocal

cd /d %~dp0

set SERVICE_NAME=1C-Kaiten-Integration
set NSSM_PATH=C:\nssm\win64\nssm.exe
set PYTHON_EXE=%CD%\.venv\Scripts\python.exe
set APP_DIR=%CD%
set APP_ARGS=-m uvicorn app:app --host 127.0.0.1 --port 8088
set LOG_DIR=%CD%\logs
set LOG_OUT=%LOG_DIR%\service.out.log
set LOG_ERR=%LOG_DIR%\service.err.log

if not exist "%NSSM_PATH%" (
    echo NSSM not found: %NSSM_PATH%
    pause
    exit /b 1
)

if not exist "%PYTHON_EXE%" (
    echo Python not found: %PYTHON_EXE%
    pause
    exit /b 1
)

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
if not exist "%CD%\state" mkdir "%CD%\state"
if not exist "%CD%\config" mkdir "%CD%\config"

echo Stopping old service if exists...
"%NSSM_PATH%" stop "%SERVICE_NAME%" >nul 2>nul
"%NSSM_PATH%" remove "%SERVICE_NAME%" confirm >nul 2>nul

echo Installing service...
"%NSSM_PATH%" install "%SERVICE_NAME%" "%PYTHON_EXE%" %APP_ARGS%
if errorlevel 1 (
    echo Service install failed.
    pause
    exit /b 1
)

echo Configuring service...
"%NSSM_PATH%" set "%SERVICE_NAME%" AppDirectory "%APP_DIR%"
"%NSSM_PATH%" set "%SERVICE_NAME%" DisplayName "%SERVICE_NAME%"
"%NSSM_PATH%" set "%SERVICE_NAME%" Description "Local FastAPI service for 1C-Kaiten integration"
"%NSSM_PATH%" set "%SERVICE_NAME%" Start SERVICE_AUTO_START
"%NSSM_PATH%" set "%SERVICE_NAME%" AppStdout "%LOG_OUT%"
"%NSSM_PATH%" set "%SERVICE_NAME%" AppStderr "%LOG_ERR%"
"%NSSM_PATH%" set "%SERVICE_NAME%" AppRotateFiles 1
"%NSSM_PATH%" set "%SERVICE_NAME%" AppRotateOnline 1

echo Starting service...
"%NSSM_PATH%" start "%SERVICE_NAME%"

echo.
echo Service installed and started.
echo Health check: http://127.0.0.1:8088/health
echo Stdout log: %LOG_OUT%
echo Stderr log: %LOG_ERR%
pause
