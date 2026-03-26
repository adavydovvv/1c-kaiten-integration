@echo off
setlocal

cd /d %~dp0

set SERVICE_NAME=1C-Kaiten-Integration
set NSSM_PATH=C:\nssm\win64\nssm.exe

if not exist "%NSSM_PATH%" (
    echo NSSM not found: %NSSM_PATH%
    pause
    exit /b 1
)

echo Stopping service...
"%NSSM_PATH%" stop "%SERVICE_NAME%" >nul 2>nul

echo Removing service...
"%NSSM_PATH%" remove "%SERVICE_NAME%" confirm
if errorlevel 1 (
    echo Failed to remove service %SERVICE_NAME%
    pause
    exit /b 1
)

echo.
echo Service removed.
pause
