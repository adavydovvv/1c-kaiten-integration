@echo off
cd /d %~dp0

if not exist .venv (
    py -3 -m venv .venv
)

call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

if not exist logs mkdir logs
if not exist state mkdir state
if not exist config mkdir config

python setup_wizard.py

echo.
echo Установка завершена.
echo Для ручного запуска используйте run_service.bat
pause
