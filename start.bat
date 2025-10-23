@echo off
echo ========================================
echo   Ung Dung Hoc Ngu Ngu Ky Hieu
echo ========================================
echo.
echo Dang kiem tra Python...
python --version
if errorlevel 1 (
    echo.
    echo [LOI] Chua cai Python!
    echo Hay tai tai: https://www.python.org/downloads/
    pause
    exit
)

echo.
echo Dang kiem tra thu vien...
pip show opencv-python >nul 2>&1
if errorlevel 1 (
    echo.
    echo [CANH BAO] Chua cai thu vien!
    echo Dang tu dong cai dat...
    pip install -r requirements.txt
)

echo.
echo Dang khoi dong ung dung...
echo.
python sign_language_app.py

pause
