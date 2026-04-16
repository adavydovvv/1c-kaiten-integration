@echo off
chcp 65001 >nul
setlocal

cd /d %~dp0

set PYTHON_CMD=py -3
set VENV_PY=%CD%\.venv\Scripts\python.exe

echo Шаг 1: Создание виртуального окружения...
if not exist ".venv" (
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo [ОШИБКА] Не удалось создать виртуальное окружение. Убедитесь, что Python установлен.
        pause
        exit /b 1
    )
)

echo Шаг 2: Обновление pip...
"%VENV_PY%" -m pip install --upgrade pip >nul
if errorlevel 1 (
    echo [ОШИБКА] Не удалось обновить pip.
    pause
    exit /b 1
)

echo Шаг 3: Установка зависимостей...
"%VENV_PY%" -m pip install -r requirements.txt >nul
if errorlevel 1 (
    echo [ОШИБКА] Не удалось установить зависимости из requirements.txt.
    pause
    exit /b 1
)

echo Шаг 4: Создание рабочих папок...
if not exist "logs" mkdir "logs"
if not exist "state" mkdir "state"
if not exist "config" mkdir "config"

echo.
echo Шаг 5: Запуск мастера настройки (setup_wizard.py)...
echo ----------------------------------------------------
"%VENV_PY%" setup_wizard.py
if errorlevel 1 (
    echo.
    echo [ОШИБКА] Мастер настройки прерван или завершился с ошибкой.
    pause
    exit /b 1
)
echo ----------------------------------------------------

echo Шаг 6: Проверка работоспособности окружения...
"%VENV_PY%" -c "import uvicorn, fastapi, requests; print('Python окружение настроено корректно!')"
if errorlevel 1 (
    echo [ОШИБКА] Проверка Python окружения провалилась.
    pause
    exit /b 1
)

echo.
echo [OK] Базовая установка и настройка завершены!
echo Следующий шаг: запустите install_service.bat от имени Администратора.
pause