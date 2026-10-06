@echo off
cd /d "%~dp0"
if not exist ".venv" (
    echo [!] Virtual environment not found. Running setup_dev_env.bat first...
    call setup_dev_env.bat
)
call .venv\Scripts\activate.bat
python -m src.main
pause
