@echo off
chcp 65001 >nul
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
    echo [ОШИБКА] NSSM не найден по пути: %NSSM_PATH%
    pause
    exit /b 1
)

if not exist "%PYTHON_EXE%" (
    echo [ОШИБКА] Python не найден по пути: %PYTHON_EXE%. Сначала запустите install.bat.
    pause
    exit /b 1
)

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
if not exist "%CD%\state" mkdir "%CD%\state"
if not exist "%CD%\config" mkdir "%CD%\config"

echo Останавливаем старую службу, если она существует...
"%NSSM_PATH%" stop "%SERVICE_NAME%" >nul 2>nul
"%NSSM_PATH%" remove "%SERVICE_NAME%" confirm >nul 2>nul

echo Устанавливаем службу...
"%NSSM_PATH%" install "%SERVICE_NAME%" "%PYTHON_EXE%" %APP_ARGS%
if errorlevel 1 (
    echo [ОШИБКА] Установка службы не удалась. Убедитесь, что этот скрипт запущен от имени Администратора!
    pause
    exit /b 1
)

echo Настраиваем параметры службы...
"%NSSM_PATH%" set "%SERVICE_NAME%" AppDirectory "%APP_DIR%"
"%NSSM_PATH%" set "%SERVICE_NAME%" DisplayName "%SERVICE_NAME%"
"%NSSM_PATH%" set "%SERVICE_NAME%" Description "Локальный сервис интеграции 1С и Kaiten"
"%NSSM_PATH%" set "%SERVICE_NAME%" Start SERVICE_AUTO_START
"%NSSM_PATH%" set "%SERVICE_NAME%" AppStdout "%LOG_OUT%"
"%NSSM_PATH%" set "%SERVICE_NAME%" AppStderr "%LOG_ERR%"
"%NSSM_PATH%" set "%SERVICE_NAME%" AppRotateFiles 1
"%NSSM_PATH%" set "%SERVICE_NAME%" AppRotateOnline 1

echo Запускаем службу...
"%NSSM_PATH%" start "%SERVICE_NAME%"

echo.
echo [OK] Служба установлена и запущена!
echo Адрес сервиса: http://127.0.0.1:8088/health
echo Лог событий (Stdout): %LOG_OUT%
echo Лог ошибок (Stderr): %LOG_ERR%
pause