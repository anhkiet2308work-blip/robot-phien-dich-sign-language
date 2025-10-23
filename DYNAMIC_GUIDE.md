# 🎬 Hướng dẫn: Nhận diện Ký hiệu ĐỘNG

## 🆚 So sánh 2 loại ký hiệu

### **Static Gestures (Tĩnh)** - App cũ
```
✅ Dùng cho: Tư thế 1 lần
✅ Ví dụ:
   - "OK" → Chạm ngón cái + ngón trỏ
   - "Số 5" → Giơ 5 ngón
   - "Peace" → Ngón trỏ + giữa
   
✅ Model: Dense Neural Network
✅ Input: 1 frame = 784 features
```

### **Dynamic Gestures (Động)** - App mới ⭐
```
✅ Dùng cho: Chuỗi động tác
✅ Ví dụ:
   - "Xin chào" → Giơ tay + vẫy trái phải
   - "Tạm biệt" → Vẫy tay liên tục
   - "Không" → Lắc tay trái phải
   - "Đồng ý" → Gật tay lên xuống
   - "Đến đây" → Vẫy tay về phía mình
   
✅ Model: LSTM (Long Short-Term Memory)
✅ Input: 30 frames = sequence (30, 784)
```

---

## 🎯 Khi nào dùng Dynamic version?

### ✅ **Dùng khi:**
- Ký hiệu có DI CHUYỂN
- Ký hiệu có HƯỚNG (trái/phải, lên/xuống)
- Ký hiệu có TỐC ĐỘ (nhanh/chậm)
- Ký hiệu có LẶP LẠI (vẫy nhiều lần)

### ❌ **Không cần dùng khi:**
- Chỉ là tư thế tĩnh
- Không có chuyển động
- → Dùng Static version (nhanh hơn, đơn giản hơn)

---

## 📊 Cách hoạt động

### **Architecture:**

```
Input: Sequence của 30 frames
    ↓
LSTM Layer 1 (64 units) - Học pattern theo thời gian
    ↓
Dropout 30% - Tránh overfitting
    ↓
LSTM Layer 2 (32 units) - Tinh chỉnh
    ↓
Dropout 20%
    ↓
Dense (32 units, ReLU)
    ↓
Dense (N classes, Softmax)
    ↓
Output: Xác suất mỗi nhãn
```

### **Sequence:**

```
1 sequence = 30 frames liên tiếp

Frame 1  → [784 features]
Frame 2  → [784 features]
Frame 3  → [784 features]
...
Frame 30 → [784 features]

→ Shape: (30, 784)
```

### **Timeline:**

```
Thời gian thực: ~1 giây
FPS: ~30 frames/giây
→ 30 frames = toàn bộ động tác
```

---

## 🚀 Cách sử dụng

### **1. Cài đặt:**

```powershell
pip install opencv-python tensorflow numpy pillow
python sign_language_dynamic.py
```

### **2. Thu thập động tác:**

**Bước 1:** Nhập tên động tác
```
VD: "Vẫy tay chào"
    "Lắc đầu không"
    "Gật đầu đồng ý"
```

**Bước 2:** Click "Bắt đầu ghi"

**Bước 3:** ĐỢI buffer đầy (30 frames)
```
Buffer: 0/30 frames
Buffer: 15/30 frames
Buffer: 30/30 frames ✓  ← Bây giờ mới bắt đầu!
```

**Bước 4:** Thực hiện TOÀN BỘ động tác (~1 giây)
```
Ví dụ "Vẫy tay":
1. Giơ tay lên
2. Vẫy trái
3. Vẫy phải
4. Vẫy trái
5. Hạ tay

→ Toàn bộ trong 1 giây!
```

**Bước 5:** App tự động lưu sequence
```
Log: ✅ Buffer đầy! Đã ghi sequence đầu tiên
```

**Bước 6:** Buffer tự động reset
```
Buffer: 0/30 frames  ← Bắt đầu lại
```

**Bước 7:** Lặp lại bước 4-6 (10-20 lần)
```
Sequence #1 ✓
Sequence #2 ✓
...
Sequence #15 ✓
```

**Bước 8:** Click "Dừng"

### **3. Huấn luyện:**

```
1. Chuyển tab "Huấn luyện"
2. Click "Huấn luyện LSTM"
3. Chờ ~30-60 giây
4. Xem accuracy
```

### **4. Nhận diện:**

```
1. Chuyển tab "Nhận diện"
2. ĐỢI buffer đầy (30/30)
3. Thực hiện động tác
4. Xem kết quả real-time
```

---

## 💡 Tips quan trọng

### **Thu thập tốt:**

✅ **Luôn thực hiện TOÀN BỘ động tác**
```
❌ SAI: Chỉ vẫy 1 lần
✅ ĐÚNG: Vẫy 3-4 lần trong 1 giây
```

✅ **Giữ tốc độ ổn định**
```
❌ SAI: Lần 1 nhanh, lần 2 chậm
✅ ĐÚNG: Mọi lần đều ~1 giây
```

✅ **Thực hiện trong vùng xanh**
```
❌ SAI: Tay ra ngoài vùng
✅ ĐÚNG: Luôn trong khung xanh
```

✅ **Nhiều variation**
```
- Tốc độ: Nhanh, trung bình, chậm
- Biên độ: Rộng, hẹp
- Góc: Thẳng, hơi nghiêng
```

### **Số lượng sequences:**

```
10-15 sequences: Tối thiểu
20-30 sequences: Tốt
50+ sequences: Rất tốt
```

---

## 🎓 Ví dụ cụ thể

### **Ví dụ 1: "Vẫy tay chào"**

**Mô tả:**
```
1. Giơ tay lên cao (frame 1-5)
2. Vẫy trái (frame 6-10)
3. Vẫy phải (frame 11-15)
4. Vẫy trái (frame 16-20)
5. Vẫy phải (frame 21-25)
6. Hạ tay (frame 26-30)
```

**Thu thập:**
```
Sequence 1: Vẫy nhanh
Sequence 2: Vẫy chậm
Sequence 3: Vẫy rộng
...
Sequence 15: Variation khác
```

### **Ví dụ 2: "Lắc tay không"**

**Mô tả:**
```
1. Giơ tay lên (frame 1-5)
2. Lắc trái (frame 6-12)
3. Lắc phải (frame 13-19)
4. Lắc trái (frame 20-26)
5. Dừng (frame 27-30)
```

### **Ví dụ 3: "Gọi đến đây"**

**Mô tả:**
```
1. Giơ tay ra (frame 1-8)
2. Vẫy về phía mình 3 lần (frame 9-27)
3. Hạ tay (frame 28-30)
```

---

## 📊 So sánh Performance

| Tiêu chí | Static | Dynamic (LSTM) |
|----------|--------|----------------|
| **Input size** | 784 | 30 × 784 = 23,520 |
| **Model size** | Nhỏ (~100KB) | Lớn (~2MB) |
| **Training time** | 10-20s | 30-60s |
| **Inference time** | Nhanh (~10ms) | Chậm hơn (~50ms) |
| **Accuracy** | 90-95% | 80-90% |
| **Use case** | Tư thế tĩnh | Động tác |

---

## 🔬 Kiến trúc LSTM

### **Tại sao dùng LSTM?**

```
RNN thường → Không nhớ lâu (vanishing gradient)
LSTM → Nhớ được pattern dài
→ Phù hợp cho sequences
```

### **LSTM Cell:**

```
Input: Frame t
    ↓
[Forget Gate]  → Quên thông tin cũ không cần
[Input Gate]   → Nhận thông tin mới
[Cell State]   → Trạng thái nhớ
[Output Gate]  → Output cho frame này
    ↓
Output: Hidden state
```

### **Sequence Learning:**

```
Frame 1 → LSTM → h1
Frame 2 → LSTM → h2  (nhớ h1)
Frame 3 → LSTM → h3  (nhớ h1, h2)
...
Frame 30 → LSTM → h30 (nhớ tất cả)
    ↓
h30 → Dense → Prediction
```

---

## 🐛 Troubleshooting

### **"Buffer không đầy"**

```
Nguyên nhân: Camera FPS thấp
Giải pháp: 
- Tăng ánh sáng
- Đóng app khác
- Giảm chất lượng camera
```

### **"Accuracy thấp (<70%)"**

```
Nguyên nhân: 
- Quá ít sequences
- Động tác không nhất quán
- Động tác quá giống nhau

Giải pháp:
- Thu thêm sequences (30+)
- Thực hiện đồng nhất hơn
- Chọn động tác khác biệt rõ
```

### **"Nhận diện sai"**

```
Nguyên nhân:
- Thực hiện khác lúc train
- Tốc độ khác
- Quên đợi buffer đầy

Giải pháp:
- Thực hiện giống lúc train
- Giữ tốc độ ~1 giây
- Đợi "Buffer: 30/30"
```

---

## 🎯 Best Practices

### **Khi định nghĩa động tác:**

✅ **Rõ ràng, khác biệt**
```
✅ "Vẫy tay trái phải"
✅ "Gật tay lên xuống"
✅ "Vòng tròn thuận chiều"

❌ "Vẫy tay" (mơ hồ)
❌ "Di chuyển" (không cụ thể)
```

✅ **Có điểm bắt đầu/kết thúc rõ**
```
✅ Giơ tay → Động tác → Hạ tay
❌ Động tác liên tục không dừng
```

✅ **Thời gian phù hợp (~1 giây)**
```
✅ 3-5 lần vẫy trong 1 giây
❌ 1 lần vẫy chậm 3 giây
❌ 20 lần vẫy nhanh trong 1 giây
```

### **Khi huấn luyện:**

✅ Thu ít nhất 15 sequences/nhãn
✅ Thực hiện nhất quán
✅ Nhiều variation nhỏ
✅ Kiểm tra accuracy validation

---

## 📝 Tóm tắt

**3 files Python:**

1. **sign_language_app.py** - Static với MediaPipe
   - ✅ Tư thế tĩnh
   - ✅ Chính xác cao
   - ❌ Cần Python 3.9-3.11

2. **sign_language_simple.py** - Static với OpenCV
   - ✅ Tư thế tĩnh
   - ✅ Dễ cài đặt
   - ✅ Mọi Python version

3. **sign_language_dynamic.py** - Dynamic với LSTM ⭐
   - ✅ Động tác có chuyển động
   - ✅ Sequence learning
   - ✅ Mọi Python version
   - ⚠️ Cần nhiều data hơn

---

**Chọn file nào?**

```
Ký hiệu tĩnh (OK, Peace, Số) → Simple/App
Ký hiệu động (Vẫy, Lắc, Gật) → Dynamic ⭐
```

---

Bạn còn thắc mắc gì không? 😊
