@echo off
setlocal

cd /d %~dp0

set PYTHON_CMD=py -3
set VENV_PY=%CD%\.venv\Scripts\python.exe

echo Step 1: create virtual environment...
if not exist ".venv" (
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
)

echo Step 2: upgrade pip...
"%VENV_PY%" -m pip install --upgrade pip
if errorlevel 1 (
    echo Failed to upgrade pip.
    pause
    exit /b 1
)

echo Step 3: install requirements...
"%VENV_PY%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install requirements.
    pause
    exit /b 1
)

echo Step 4: create folders...
if not exist "logs" mkdir "logs"
if not exist "state" mkdir "state"
if not exist "config" mkdir "config"

echo Step 5: create local config if missing...
if not exist "config\local_config.json" (
    if exist "config\local_config.example.json" (
        copy /Y "config\local_config.example.json" "config\local_config.json" >nul
    )
)

echo Step 6: local health test...
"%VENV_PY%" -c "import uvicorn, fastapi, requests; print('Python environment OK')"
if errorlevel 1 (
    echo Python environment check failed.
    pause
    exit /b 1
)

echo.
echo Base installation completed.
echo Next step: run install_service.bat as Administrator.
pause
