@echo off
chcp 65001 >nul
echo ========================================
echo   Ứng dụng Học Ngôn Ngữ Ký Hiệu
echo   (Phiên bản đơn giản - Không MediaPipe)
echo ========================================
echo.

echo [1/3] Kiểm tra Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Chưa cài Python!
    echo.
    echo Hãy tải tại: https://www.python.org/downloads/
    echo.
    pause
    exit
)
python --version
echo ✅ Python OK!
echo.

echo [2/3] Kiểm tra thư viện...
python -c "import cv2" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Chưa cài thư viện!
    echo.
    echo Đang tự động cài đặt...
    pip install -r requirements_simple.txt
    if errorlevel 1 (
        echo.
        echo ❌ Lỗi cài đặt! Thử thủ công:
        echo pip install opencv-python tensorflow numpy pillow
        echo.
        pause
        exit
    )
)
echo ✅ Thư viện OK!
echo.

echo [3/3] Khởi động ứng dụng...
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

python sign_language_simple.py

echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo Ứng dụng đã đóng.
echo.
pause
