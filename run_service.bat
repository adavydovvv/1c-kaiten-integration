@echo off
cd /d %~dp0
call .venv\Scripts\activate
uvicorn app:app --host 127.0.0.1 --port 8088
