@echo off
chcp 65001 >nul
setlocal

cd /d %~dp0

set SERVICE_NAME=1C-Kaiten-Integration
set NSSM_PATH=C:\nssm\win64\nssm.exe

if not exist "%NSSM_PATH%" (
    echo [ОШИБКА] Утилита NSSM не найдена по пути: %NSSM_PATH%
    pause
    exit /b 1
)

echo Останавливаем службу %SERVICE_NAME%...
"%NSSM_PATH%" stop "%SERVICE_NAME%" >nul 2>nul

echo Удаляем службу из Windows...
"%NSSM_PATH%" remove "%SERVICE_NAME%" confirm
if errorlevel 1 (
    echo [ОШИБКА] Не удалось удалить службу %SERVICE_NAME%
    pause
    exit /b 1
)

echo.
echo [OK] Служба успешно удалена!
echo.
echo Зачистка локальных конфигурационных файлов...

if exist "config\local_config.json" (
    del /q /f "config\local_config.json"
    echo [OK] Файл config\local_config.json успешно удален.
) else (
    echo [-] Файл config\local_config.json не найден.
)

:: На всякий случай удаляем .env
if exist ".env" (
    del /q /f ".env"
    echo [OK] Файл .env успешно удален.
)

echo.
echo Деинсталляция полностью завершена! Можно безопасно удалять папку.
pause