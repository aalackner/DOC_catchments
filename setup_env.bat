@echo off
REM Create virtual environment in 'venv' folder
python3 -m venv venv

REM Activate the virtual environment
call venv\Scripts\activate

REM Upgrade pip
python3 -m pip install --upgrade pip

REM Install required packages from requirements.txt
python3 -m pip install -r requirements.txt

REM List installed packages
python3 -m pip list

echo.
echo Virtual environment setup complete.
echo To activate later, run: venv\Scripts\activate