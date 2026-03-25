@echo off
chcp 65001 > nul
setlocal

cd /d %~dp0

set SERVICE_NAME=1C-Kaiten-Integration
set NSSM_PATH=C:\nssm\win64\nssm.exe
set PYTHON_EXE=%CD%\.venv\Scripts\python.exe
set APP_DIR=%CD%
set APP_ARGS=-m uvicorn app:app --host 127.0.0.1 --port 8088
set LOG_OUT=%CD%\logs\service.out.log
set LOG_ERR=%CD%\logs\service.err.log

if not exist "%NSSM_PATH%" (
    echo NSSM не найден: %NSSM_PATH%
    pause
    exit /b 1
)

if not exist "%PYTHON_EXE%" (
    echo Не найден python.exe: %PYTHON_EXE%
    pause
    exit /b 1
)

if not exist "%CD%\logs" mkdir "%CD%\logs"
if not exist "%CD%\state" mkdir "%CD%\state"
if not exist "%CD%\config" mkdir "%CD%\config"

echo Удаляем старый сервис, если он уже был...
"%NSSM_PATH%" stop "%SERVICE_NAME%" >nul 2>nul
"%NSSM_PATH%" remove "%SERVICE_NAME%" confirm >nul 2>nul

echo Устанавливаем сервис...
"%NSSM_PATH%" install "%SERVICE_NAME%" "%PYTHON_EXE%" %APP_ARGS%
if errorlevel 1 (
    echo Ошибка установки сервиса.
    pause
    exit /b 1
)

echo Настраиваем параметры...
"%NSSM_PATH%" set "%SERVICE_NAME%" AppDirectory "%APP_DIR%"
"%NSSM_PATH%" set "%SERVICE_NAME%" DisplayName "%SERVICE_NAME%"
"%NSSM_PATH%" set "%SERVICE_NAME%" Description "Local FastAPI service for 1C-Kaiten integration"
"%NSSM_PATH%" set "%SERVICE_NAME%" Start SERVICE_AUTO_START
"%NSSM_PATH%" set "%SERVICE_NAME%" AppStdout "%LOG_OUT%"
"%NSSM_PATH%" set "%SERVICE_NAME%" AppStderr "%LOG_ERR%"

reg add "HKLM\SYSTEM\CurrentControlSet\Services\%SERVICE_NAME%\Parameters" /v AppNoConsole /t REG_DWORD /d 1 /f >nul

echo Запускаем сервис...
"%NSSM_PATH%" start "%SERVICE_NAME%"

echo.
echo Сервис установлен и запущен.
echo Проверка: http://127.0.0.1:8088/health
echo Логи:
echo   %LOG_OUT%
echo   %LOG_ERR%
pause
