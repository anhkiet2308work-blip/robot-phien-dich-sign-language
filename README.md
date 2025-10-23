# 🤖 Ứng Dụng Desktop - Học Ngôn Ngữ Ký Hiệu

Ứng dụng desktop với giao diện Tkinter để học và nhận diện ngôn ngữ ký hiệu bằng AI.

## 📋 Yêu cầu hệ thống

- **Python 3.8 trở lên**
- **Webcam** (camera máy tính hoặc USB)
- **Windows / macOS / Linux**

## 🚀 Cài đặt

### Bước 1: Cài Python

**Windows:**
- Tải từ: https://www.python.org/downloads/
- Tick "Add Python to PATH" khi cài

**macOS:**
```bash
brew install python3
```

**Linux:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-tk
```

### Bước 2: Cài thư viện

Mở Terminal (macOS/Linux) hoặc Command Prompt (Windows):

```bash
# Vào thư mục chứa file
cd /đường/dẫn/đến/thư/mục

# Cài đặt các thư viện
pip install -r requirements.txt
```

**Lưu ý:** Quá trình cài TensorFlow có thể mất 5-10 phút.

### Bước 3: Chạy ứng dụng

```bash
python sign_language_app.py
```

## 📖 Hướng dẫn sử dụng

### 1️⃣ Thu thập mẫu

1. Click **"▶ Bật Camera"**
2. Chuyển sang tab **"📚 Thu thập mẫu"**
3. Nhập tên nhãn (VD: "Xin chào", "Cảm ơn")
4. Click **"🎬 Bắt đầu học"**
5. **Thực hiện ký hiệu** trước camera
6. Khi đủ 30-50 mẫu → Click **"⏸ Dừng"**
7. Lặp lại cho các ký hiệu khác (ít nhất 2 nhãn)

**Mẹo:**
- ✅ Thực hiện ở nhiều góc độ
- ✅ Thay đổi tốc độ (chậm/nhanh)
- ✅ 30-50 mẫu mỗi nhãn là tốt nhất

### 2️⃣ Huấn luyện mô hình

1. Chuyển sang tab **"🧠 Huấn luyện"**
2. Kiểm tra số lớp và mẫu
3. Click **"🚀 Huấn luyện mô hình"**
4. Chờ 10-30 giây
5. Xem độ chính xác (Accuracy)

**Độ chính xác:**
- > 90%: Tốt ✅
- 80-90%: Khá ⚠️
- < 80%: Cần thêm mẫu ❌

### 3️⃣ Nhận diện

1. Chuyển sang tab **"🎯 Nhận diện"**
2. **Thực hiện ký hiệu** đã học
3. Xem kết quả real-time
4. Độ tin cậy > 70% sẽ hiển thị nhãn

## 🎨 Giao diện

```
┌────────────────────────────────────────────────────┐
│        🤖 Hệ Thống Học Ngôn Ngữ Ký Hiệu           │
│   AI tự học từ bạn! Thu thập → Huấn luyện → Nhận diện│
├─────────────────────┬──────────────────────────────┤
│                     │ [📚][🧠][🎯] TABS            │
│   📹 Camera         │                              │
│  ┌────────────┐     │  TAB 1: Thu thập mẫu         │
│  │            │     │  - Input nhãn                │
│  │   Video    │     │  - Buttons: Bắt đầu/Dừng     │
│  │  640x480   │     │  - Stats: Mẫu/Nhãn/Tổng      │
│  │            │     │  - Log                       │
│  └────────────┘     │                              │
│  [▶ Bật] [⏹ Tắt]   │  TAB 2: Huấn luyện           │
│  🟢 Camera hoạt động│  - Stats model               │
│                     │  - Button huấn luyện         │
│                     │  - Dataset list              │
│                     │                              │
│                     │  TAB 3: Nhận diện            │
│                     │  - Prediction display        │
│                     │  - Confidence                │
└─────────────────────┴──────────────────────────────┘
```

## 🎯 Tính năng chính

### ✨ Thu thập thông minh
- ✅ Tự động đếm mẫu
- ✅ Phát hiện 2 tay đồng thời
- ✅ Hiển thị landmarks real-time
- ✅ Màu khác nhau cho mỗi tay (xanh/xanh lá)

### 🧠 Huấn luyện AI
- ✅ Neural Network (TensorFlow/Keras)
- ✅ Architecture: 126 → 64 → 32 → N
- ✅ Dropout tránh overfitting
- ✅ Validation 20%
- ✅ 50 epochs training

### 🎯 Nhận diện real-time
- ✅ Dự đoán liên tục
- ✅ Hiển thị confidence
- ✅ Threshold 70%

### 💾 Lưu trữ
- ✅ Dataset lưu file `dataset.pkl`
- ✅ Tự động load khi khởi động
- ✅ Có thể backup/restore

## 📊 Cấu trúc dữ liệu

### Dataset structure:
```python
{
  "Xin chào": [
    [0.5, 0.6, 0.1, ...],  # Mẫu 1 (126 features)
    [0.51, 0.59, 0.11, ...],  # Mẫu 2
    # ... 40 mẫu
  ],
  "Cảm ơn": [
    # ... 35 mẫu
  ]
}
```

### Features (126 dimensions):
```
2 tay × 21 điểm × 3 tọa độ (x,y,z) = 126 features

Tay 1: [x0,y0,z0, x1,y1,z1, ..., x20,y20,z20]  # 63 features
Tay 2: [x0,y0,z0, x1,y1,z1, ..., x20,y20,z20]  # 63 features
```

## 🔧 Khắc phục sự cố

### Camera không bật
```bash
# Kiểm tra quyền camera
# Windows: Settings → Privacy → Camera
# macOS: System Preferences → Security → Camera
# Linux: ls /dev/video*
```

### Lỗi cài đặt TensorFlow
```bash
# Nếu lỗi, thử:
pip install tensorflow-cpu==2.15.0  # CPU only (nhẹ hơn)
```

### Lỗi "No module named 'tkinter'"
```bash
# Linux:
sudo apt install python3-tk

# macOS:
brew install python-tk
```

### Model accuracy thấp
- ✅ Thu thêm mẫu (50-100 mỗi nhãn)
- ✅ Đảm bảo ánh sáng tốt
- ✅ Thực hiện ký hiệu rõ ràng
- ✅ Tránh các nhãn quá giống nhau

## 📁 Cấu trúc files

```
project/
├── sign_language_app.py    # Code chính
├── requirements.txt         # Dependencies
├── README.md               # Hướng dẫn (file này)
└── dataset.pkl             # Dataset (tự động tạo)
```

## 🎓 Workflow hoàn chỉnh

```
1. Cài đặt Python + thư viện
   ↓
2. Chạy ứng dụng
   ↓
3. Bật camera
   ↓
4. Thu thập "Xin chào" (40 mẫu)
   ↓
5. Thu thập "Cảm ơn" (35 mẫu)
   ↓
6. Thu thập "Tạm biệt" (45 mẫu)
   ↓
7. Huấn luyện → Accuracy 95%
   ↓
8. Nhận diện real-time
   ↓
9. Học thêm nhãn mới bất cứ lúc nào!
```

## 💡 Tips nâng cao

### Backup dataset
```bash
# Copy file dataset.pkl sang nơi an toàn
cp dataset.pkl dataset_backup.pkl
```

### Thêm nhãn mới
- Không cần xóa dataset cũ
- Chỉ cần thu thập nhãn mới
- Train lại → Model tự động cập nhật

### Chia sẻ dataset
- Gửi file `dataset.pkl` cho người khác
- Họ copy vào thư mục
- Chạy ứng dụng → Tự động load

## 🐛 Báo lỗi

Nếu gặp lỗi, hãy kiểm tra:
1. ✅ Python version (3.8+)
2. ✅ Đã cài đủ thư viện
3. ✅ Camera hoạt động
4. ✅ Quyền truy cập camera
5. ✅ Log trong ứng dụng

## 📝 License

MIT License - Tự do sử dụng và chỉnh sửa

## 👨‍💻 Phát triển bởi

Claude AI Assistant 🤖

---

**Chúc bạn học tập vui vẻ!** 🎉
