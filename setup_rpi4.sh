#!/bin/bash
echo "🤖 Setting up Robot Phiên Dịch on Raspberry Pi 4..."

# Update system
sudo apt-get update

# Install dependencies
sudo apt-get install -y python3-pip python3-opencv libatlas-base-dev portaudio19-dev python3-pyaudio ffmpeg

# Install Python packages
pip3 install -r requirements.txt

echo "✅ Setup complete!"
echo "Next: ./download_models.sh"