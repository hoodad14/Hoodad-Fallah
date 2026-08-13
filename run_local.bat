@echo off
setlocal
if not exist .env copy .env.example .env
if not exist .venv py -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python preflight.py
if errorlevel 1 exit /b %errorlevel%
python manage.py runserver 127.0.0.1:8000
endlocal
