#!/bin/bash
echo "📥 Downloading model and dataset from GitHub Releases..."

wget https://github.com/anhkiet2308work-blip/robot-phien-dich-sign-language/releases/download/v2.1.0/sign_language_model.h5

wget https://github.com/anhkiet2308work-blip/robot-phien-dich-sign-language/releases/download/v2.1.0/dataset_dynamic.pkl

echo "✅ Download complete!"