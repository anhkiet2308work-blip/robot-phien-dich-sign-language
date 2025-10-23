#!/bin/bash
echo "🤖 Setting up Robot Phiên Dịch on Raspberry Pi 4..."

# Update system
echo "📦 Step 1/4: Updating system..."
sudo apt-get update

# Install system dependencies
echo "📦 Step 2/4: Installing system dependencies..."
sudo apt-get install -y \
    python3-pip \
    python3-venv \
    python3-opencv \
    libatlas-base-dev \
    portaudio19-dev \
    python3-pyaudio \
    ffmpeg

# Create virtual environment
echo "📦 Step 3/4: Creating virtual environment..."
python3 -m venv venv

# Activate and install packages
echo "📦 Step 4/4: Installing Python packages..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✅ SETUP COMPLETE!"
echo ""
echo "⚠️  To run the app:"
echo "   source venv/bin/activate"
echo "   python3 sign_language_dynamic_v7.py"
echo ""
echo "Or use the shortcut:"
echo "   ./run.sh"