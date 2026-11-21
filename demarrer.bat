@echo off
rem Jessna Event - demarre Django sur toutes les interfaces reseau (0.0.0.0:8000).
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
  echo Environnement Python introuvable. Lance d'abord :
  echo   python -m venv .venv
  echo   .venv\Scripts\activate
  echo   pip install -r requirements.txt
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
pause
