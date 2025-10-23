#!/bin/bash

echo "========================================"
echo "  Ứng Dụng Học Ngôn Ngữ Ký Hiệu"
echo "========================================"
echo ""

# Kiểm tra Python
echo "Đang kiểm tra Python..."
if ! command -v python3 &> /dev/null; then
    echo ""
    echo "[LỖI] Chưa cài Python!"
    echo "macOS: brew install python3"
    echo "Linux: sudo apt install python3 python3-pip python3-tk"
    exit 1
fi

python3 --version

# Kiểm tra thư viện
echo ""
echo "Đang kiểm tra thư viện..."
if ! python3 -c "import cv2" 2>/dev/null; then
    echo ""
    echo "[CẢNH BÁO] Chưa cài thư viện!"
    echo "Đang tự động cài đặt..."
    pip3 install -r requirements.txt
fi

# Chạy ứng dụng
echo ""
echo "Đang khởi động ứng dụng..."
echo ""
python3 sign_language_app.py

echo ""
echo "Ứng dụng đã đóng."
