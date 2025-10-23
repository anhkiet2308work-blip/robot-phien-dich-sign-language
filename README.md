## 🚀 Cài đặt trên Raspberry Pi 4

### Bước 1: Clone repository
```bash
git clone https://github.com/anhkiet2308work-blip/robot-phien-dich-sign-language.git
cd robot-phien-dich-sign-language
```

### Bước 2: Chạy setup (tự động tạo venv)
```bash
chmod +x setup_rpi4.sh
./setup_rpi4.sh
```

### Bước 3: Download model & dataset
```bash
chmod +x download_models.sh
./download_models.sh
```

### Bước 4: Chạy app
```bash
chmod +x run.sh
./run.sh
```

**Hoặc chạy thủ công:**
```bash
source venv/bin/activate
python3 sign_language_dynamic_v7.py
```