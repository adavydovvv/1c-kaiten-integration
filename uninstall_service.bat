@echo off
chcp 65001 > nul
setlocal

cd /d %~dp0

set SERVICE_NAME=1C-Kaiten-Integration
set NSSM_PATH=C:\nssm\win64\nssm.exe

if not exist "%NSSM_PATH%" (
    echo NSSM не найден: %NSSM_PATH%
    pause
    exit /b 1
)

echo Останавливаем сервис...
"%NSSM_PATH%" stop "%SERVICE_NAME%" >nul 2>nul

echo Удаляем сервис...
"%NSSM_PATH%" remove "%SERVICE_NAME%" confirm
if errorlevel 1 (
    echo Не удалось удалить сервис %SERVICE_NAME%
    pause
    exit /b 1
)

echo.
echo Сервис %SERVICE_NAME% удален.
pause
