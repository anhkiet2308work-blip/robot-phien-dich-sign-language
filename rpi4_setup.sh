#!/bin/bash
################################################################################
# 🤖 ROBOT PHIÊN DỊCH - RASPBERRY PI 4 AUTO SETUP
# Script tự động cài đặt toàn bộ dependencies cho RPi 4
################################################################################

echo "========================================================================"
echo "🤖 ROBOT PHIÊN DỊCH NGÔN NGỮ KÝ HIỆU - RASPBERRY PI 4 SETUP"
echo "========================================================================"
echo ""

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo; then
    echo "⚠️  Warning: This doesn't appear to be a Raspberry Pi!"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check RAM (recommend 4GB+)
TOTAL_RAM=$(free -g | awk '/^Mem:/{print $2}')
echo "💾 Detected RAM: ${TOTAL_RAM}GB"
if [ "$TOTAL_RAM" -lt 3 ]; then
    echo "⚠️  Warning: Less than 4GB RAM detected. App may run slowly."
fi

echo ""
echo "📦 Step 1/6: Updating system..."
echo "========================================================================"
sudo apt-get update
sudo apt-get upgrade -y

echo ""
echo "📦 Step 2/6: Installing system dependencies..."
echo "========================================================================"
sudo apt-get install -y \
    python3-pip \
    python3-dev \
    python3-opencv \
    libopencv-dev \
    libatlas-base-dev \
    libjasper-dev \
    libqtgui4 \
    libqt4-test \
    libhdf5-dev \
    libhdf5-serial-dev \
    portaudio19-dev \
    python3-pyaudio \
    espeak \
    libportaudio2 \
    libportaudiocpp0 \
    ffmpeg \
    git

echo ""
echo "📦 Step 3/6: Installing Python packages (this may take 10-20 minutes)..."
echo "========================================================================"

# Upgrade pip
pip3 install --upgrade pip setuptools wheel

# Install NumPy first (required by others)
echo "  → Installing NumPy..."
pip3 install numpy==1.23.5

# Install TensorFlow for ARM
echo "  → Installing TensorFlow (ARM optimized)..."
pip3 install tensorflow==2.13.0

# Install OpenCV
echo "  → Installing OpenCV..."
pip3 install opencv-python==4.8.0.74
pip3 install opencv-contrib-python==4.8.0.74

# Install Pillow
echo "  → Installing Pillow..."
pip3 install Pillow==10.0.0

# Install Audio packages
echo "  → Installing audio packages..."
pip3 install SpeechRecognition==3.10.0
pip3 install PyAudio==0.2.13
pip3 install gTTS==2.3.2
pip3 install pygame==2.5.0

# Install Excel support
echo "  → Installing openpyxl..."
pip3 install openpyxl==3.1.2

echo ""
echo "📦 Step 4/6: Configuring system settings..."
echo "========================================================================"

# Increase swap size for training
CURRENT_SWAP=$(free -m | awk '/^Swap:/{print $2}')
echo "Current swap: ${CURRENT_SWAP}MB"
if [ "$CURRENT_SWAP" -lt 2048 ]; then
    echo "  → Increasing swap to 2GB..."
    sudo dphys-swapfile swapoff
    sudo sed -i 's/CONF_SWAPSIZE=.*/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile
    sudo dphys-swapfile setup
    sudo dphys-swapfile swapon
    echo "  ✅ Swap increased to 2GB"
else
    echo "  ✅ Swap size is adequate"
fi

# Enable camera if using Pi Camera
if [ -e /dev/video0 ]; then
    echo "  ✅ Camera detected at /dev/video0"
else
    echo "  ⚠️  No camera detected. Make sure camera is enabled:"
    echo "     sudo raspi-config → Interface Options → Camera → Enable"
fi

echo ""
echo "📦 Step 5/6: Setting up performance optimizations..."
echo "========================================================================"

# Add performance tweaks to /boot/config.txt
if ! grep -q "# Robot Phien Dich Optimizations" /boot/config.txt; then
    echo "  → Adding performance tweaks..."
    sudo bash -c 'cat >> /boot/config.txt << EOF

# Robot Phien Dich Optimizations
# Overclock (safe settings for RPi 4)
over_voltage=2
arm_freq=1750

# GPU memory (reduce for more RAM for TensorFlow)
gpu_mem=128

# Enable hardware video codec
start_x=1
EOF'
    echo "  ✅ Performance tweaks added"
    echo "  ⚠️  Reboot required for changes to take effect"
else
    echo "  ✅ Performance tweaks already configured"
fi

echo ""
echo "📦 Step 6/6: Creating application directory..."
echo "========================================================================"

# Create app directory
APP_DIR="$HOME/robot-phien-dich"
mkdir -p "$APP_DIR"
cd "$APP_DIR"

# Create temperature monitoring script
cat > check_temp.sh << 'EOF'
#!/bin/bash
# Check CPU temperature
TEMP=$(vcgencmd measure_temp | grep -o '[0-9.]*')
echo "🌡️  CPU Temperature: ${TEMP}°C"
if (( $(echo "$TEMP > 70" | bc -l) )); then
    echo "⚠️  WARNING: CPU is hot! Consider adding cooling."
elif (( $(echo "$TEMP > 60" | bc -l) )); then
    echo "⚠️  CPU temperature is elevated. Monitor during training."
else
    echo "✅ Temperature is normal."
fi
EOF
chmod +x check_temp.sh

echo ""
echo "========================================================================"
echo "✅ INSTALLATION COMPLETE!"
echo "========================================================================"
echo ""
echo "📊 System Information:"
echo "  • OS: $(lsb_release -d | cut -f2)"
echo "  • Python: $(python3 --version)"
echo "  • TensorFlow: $(python3 -c 'import tensorflow as tf; print(tf.__version__)')"
echo "  • OpenCV: $(python3 -c 'import cv2; print(cv2.__version__)')"
echo "  • RAM: ${TOTAL_RAM}GB"
echo "  • Swap: $(free -m | awk '/^Swap:/{print $2}')MB"
echo ""
echo "🔥 Performance Tips:"
echo "  1. Monitor temperature: ./check_temp.sh"
echo "  2. Add heatsink + fan for best performance"
echo "  3. Use high-quality power supply (5V 3A)"
echo "  4. Use fast MicroSD card (UHS-I or better)"
echo ""
echo "📝 Next Steps:"
echo "  1. Copy your Python application to: $APP_DIR"
echo "  2. Run: python3 sign_language_dynamic_v7.py"
echo "  3. If camera not working: sudo raspi-config → Enable Camera"
echo ""
echo "⚠️  IMPORTANT: Reboot recommended to apply all changes"
read -p "Reboot now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔄 Rebooting..."
    sudo reboot
else
    echo "✅ Setup complete! Remember to reboot later."
fi
