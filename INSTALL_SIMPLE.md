# 🚀 Hướng dẫn cài đặt - Phiên bản đơn giản (Không MediaPipe)

## ✅ Ưu điểm version này:

- ❌ **KHÔNG CẦN MediaPipe** (tránh lỗi cài đặt)
- ✅ Chỉ dùng OpenCV + TensorFlow
- ✅ Nhẹ hơn, dễ cài hơn
- ✅ Hoạt động với mọi phiên bản Python 3.8+

## 📋 Cài đặt

### Bước 1: Kiểm tra Python

```powershell
python --version
```

**Yêu cầu:** Python 3.8 trở lên (bất kỳ phiên bản nào đều OK!)

### Bước 2: Cài thư viện

```powershell
pip install -r requirements_simple.txt
```

Hoặc cài từng cái:

```powershell
pip install opencv-python
pip install tensorflow
pip install numpy
pip install pillow
```

### Bước 3: Chạy ứng dụng

```powershell
python sign_language_simple.py
```

## 🎯 Cách dùng

### **Khác biệt với version MediaPipe:**

| Tính năng | MediaPipe | Simple (OpenCV) |
|-----------|-----------|-----------------|
| **Phát hiện** | 21 điểm/tay | Vùng da (ROI) |
| **Features** | 126 số (2x21x3) | 784 số (28x28) |
| **Cài đặt** | Khó (lỗi nhiều) | Dễ |
| **Độ chính xác** | Cao hơn | Vừa phải |
| **Tốc độ** | Nhanh | Nhanh |

### **1. Thu thập:**

1. Bật camera
2. **Đưa tay vào vùng hình chữ nhật XANH LÁ**
3. Làm ký hiệu và **giữ nguyên**
4. Thu 30-50 mẫu
5. Dừng

**Mẹo:**
- Đảm bảo tay nằm TRONG vùng xanh
- Ánh sáng tốt
- Nền đơn giản
- Không di chuyển quá nhanh

### **2. Huấn luyện:**

Tương tự version cũ - Click "Huấn luyện"

### **3. Nhận diện:**

Đưa tay vào vùng xanh → Làm ký hiệu → Xem kết quả

## 🔧 Khắc phục sự cố

### Vẫn lỗi cài TensorFlow?

```powershell
# Dùng TensorFlow CPU (nhẹ hơn)
pip uninstall tensorflow
pip install tensorflow-cpu
```

### Camera không hoạt động?

```powershell
# Kiểm tra quyền camera:
# Windows: Settings → Privacy → Camera
# Cho phép Python truy cập camera
```

### Không nhận diện được tay?

- ✅ Tăng ánh sáng
- ✅ Đảm bảo tay nằm trong vùng xanh
- ✅ Da tay phải khác màu nền
- ✅ Không đeo găng tay

## 📊 Cấu trúc Features

### Version này dùng:

```
Mask 28x28 pixels = 784 features

Thay vì:
21 điểm x 3 tọa độ x 2 tay = 126 features (MediaPipe)
```

### Workflow:

```
1. Capture frame
   ↓
2. Extract ROI (vùng xanh)
   ↓
3. Convert to HSV
   ↓
4. Skin detection (mask)
   ↓
5. Resize to 28x28
   ↓
6. Flatten → 784 features
   ↓
7. Train/Predict
```

## ⚡ So sánh hiệu năng

### MediaPipe version:
- ✅ Chính xác hơn (landmarks chuẩn)
- ❌ Khó cài đặt
- ❌ Phụ thuộc Python version

### OpenCV version (Simple):
- ✅ Dễ cài đặt
- ✅ Hoạt động mọi Python version
- ⚠️ Chính xác thấp hơn một chút
- ⚠️ Phụ thuộc ánh sáng

## 🎓 Khi nào dùng version nào?

### Dùng **Simple (OpenCV)**:
- ❌ MediaPipe không cài được
- ✅ Python 3.13 hoặc phiên bản mới
- ✅ Muốn cài đặt nhanh
- ✅ Demo/học tập

### Dùng **MediaPipe**:
- ✅ Python 3.9-3.11
- ✅ Cần độ chính xác cao
- ✅ Sản phẩm thực tế

## 📝 Tóm tắt lệnh

```powershell
# Cài đặt
pip install opencv-python tensorflow numpy pillow

# Chạy
python sign_language_simple.py

# Nếu lỗi TensorFlow
pip install tensorflow-cpu
```

---

**Version này đơn giản và hoạt động ngay!** 🎉
