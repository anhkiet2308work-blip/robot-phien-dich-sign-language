# 🎬 Ví dụ thực tế - Dynamic Gestures

## 🎯 5 động tác dễ để BẮT ĐẦU

### 1️⃣ **"Vẫy tay chào"** (Dễ nhất)

**Mô tả:**
```
Giơ tay lên → Vẫy trái phải liên tục
```

**Timeline 30 frames:**
```
Frames 1-5:   Giơ tay lên 🖐️
Frames 6-10:  Vẫy sang trái ←
Frames 11-15: Vẫy sang phải →
Frames 16-20: Vẫy sang trái ←
Frames 21-25: Vẫy sang phải →
Frames 26-30: Về giữa 🖐️
```

**Checklist thu thập:**
- [ ] Làm 15-20 lần
- [ ] Tốc độ đều (~1 giây)
- [ ] Luôn trong vùng xanh
- [ ] Vẫy rộng và rõ ràng

**Expected Accuracy:** 85-90%

---

### 2️⃣ **"Lắc tay không"**

**Mô tả:**
```
Giơ tay lên → Lắc ngang trái phải (như từ chối)
```

**Timeline 30 frames:**
```
Frames 1-5:   Giơ tay lên ✋
Frames 6-12:  Lắc sang trái ←←
Frames 13-19: Lắc sang phải →→
Frames 20-26: Lắc sang trái ←←
Frames 27-30: Dừng ✋
```

**Tips:**
- ✅ Lắc nhanh hơn vẫy (2-3 lần/giây)
- ✅ Biên độ nhỏ hơn vẫy
- ✅ Động tác "từ chối"

**Expected Accuracy:** 82-88%

---

### 3️⃣ **"Gật đầu đồng ý"** (Dùng TAY thay đầu)

**Mô tả:**
```
Giơ tay lên → Lắc dọc lên xuống (gật đầu)
```

**Timeline 30 frames:**
```
Frames 1-5:   Tay ở giữa 🖐️
Frames 6-10:  Xuống dưới ↓
Frames 11-15: Lên trên ↑
Frames 16-20: Xuống dưới ↓
Frames 21-25: Lên trên ↑
Frames 26-30: Về giữa 🖐️
```

**Tips:**
- ✅ Di chuyển THEO CHIỀU DỌC (lên/xuống)
- ✅ Khác với "Lắc" (ngang trái/phải)
- ✅ 3-4 lần gật

**Expected Accuracy:** 80-85%

---

### 4️⃣ **"Tạm biệt"**

**Mô tả:**
```
Giơ tay cao → Vẫy liên tục → Hạ tay
```

**Timeline 30 frames:**
```
Frames 1-3:   Giơ tay cao 🙋
Frames 4-7:   Vẫy trái ←
Frames 8-11:  Vẫy phải →
Frames 12-15: Vẫy trái ←
Frames 16-19: Vẫy phải →
Frames 20-23: Vẫy trái ←
Frames 24-27: Vẫy phải →
Frames 28-30: Hạ tay xuống 👋
```

**Khác với "Xin chào":**
```
Xin chào: Vẫy vừa, ở giữa
Tạm biệt: Vẫy nhiều lần, từ cao xuống thấp
```

**Expected Accuracy:** 78-84%

---

### 5️⃣ **"Đến đây"**

**Mô tả:**
```
Giơ tay ra → Vẫy VỀ PHÍA MÌNH nhiều lần
```

**Timeline 30 frames:**
```
Frames 1-5:   Giơ tay ra xa 🤚
Frames 6-10:  Kéo về gần 👉
Frames 11-15: Đẩy ra xa 🤚
Frames 16-20: Kéo về gần 👉
Frames 21-25: Đẩy ra xa 🤚
Frames 26-30: Kéo về gần 👉
```

**Tips:**
- ✅ Chuyển động RA-VÀO (forward-backward)
- ✅ Khác với trái-phải và lên-xuống
- ✅ Như "vẫy gọi người"

**Expected Accuracy:** 75-82%

---

## 🎓 Workflow hoàn chỉnh

### **Bước 1: Setup**

```powershell
# Cài đặt
pip install opencv-python tensorflow numpy pillow

# Chạy
python sign_language_dynamic.py
```

### **Bước 2: Thu thập động tác đầu tiên**

```
1. Bật camera
2. Nhập: "Vẫy tay chào"
3. Click "Bắt đầu ghi"
4. ĐỢI: Buffer 0/30 → ... → 30/30 ✓
5. Thực hiện động tác VẪY TAY (~1 giây)
6. Thấy log: "✅ Sequence #1"
7. Buffer tự reset: 0/30
8. Lặp lại bước 5-7 (15 lần)
9. Click "Dừng"
```

### **Bước 3: Thu thập các động tác còn lại**

```
Lặp lại Bước 2 cho:
- "Lắc tay không" (15 sequences)
- "Gật đầu" (15 sequences)
- "Tạm biệt" (15 sequences)
- "Đến đây" (15 sequences)
```

### **Bước 4: Huấn luyện**

```
1. Tab "Huấn luyện"
2. Kiểm tra: 5 lớp, 75 sequences
3. Click "Huấn luyện LSTM"
4. Chờ 30-60 giây
5. Accuracy: ~80-85%
```

### **Bước 5: Test nhận diện**

```
1. Tab "Nhận diện"
2. ĐỢI buffer đầy (30/30)
3. Làm động tác "Vẫy tay"
4. Xem: "Vẫy tay chào - 87%"
```

---

## ⚠️ Lỗi thường gặp

### **Lỗi 1: "Model nhận diện sai liên tục"**

**Nguyên nhân:**
```
Thu thập: Vẫy chậm (2 giây)
Nhận diện: Vẫy nhanh (0.5 giây)
→ Pattern khác nhau!
```

**Giải pháp:**
```
✅ Luôn thực hiện ĐỒNG NHẤT
✅ Tốc độ ~1 giây
✅ Biên độ giống nhau
```

---

### **Lỗi 2: "Accuracy thấp (<70%)"**

**Nguyên nhân:**
```
- Quá ít sequences (5-7)
- Động tác quá giống nhau
```

**Giải pháp:**
```
✅ Thu ít nhất 15 sequences/nhãn
✅ Chọn động tác KHÁC BIỆT rõ:
   - Vẫy (ngang)
   - Gật (dọc)
   - Đến đây (ra-vào)
```

---

### **Lỗi 3: "Buffer không đầy"**

**Nguyên nhân:**
```
Camera FPS thấp
```

**Giải pháp:**
```
✅ Tăng ánh sáng
✅ Đóng app khác
✅ Dùng camera tốt hơn
```

---

## 🎯 Động tác NÂNG CAO (sau khi thuần thục)

### 6️⃣ **"Vòng tròn thuận chiều"**

```
Timeline:
Frames 1-10:  Di chuyển theo vòng tròn
Frames 11-20: Tiếp tục vòng tròn
Frames 21-30: Hoàn thành 1 vòng
```

---

### 7️⃣ **"Chữ C"**

```
Timeline:
Frames 1-15:  Vẽ nửa trên chữ C
Frames 16-30: Vẽ nửa dưới chữ C
```

---

### 8️⃣ **"Đếm 1-2-3"**

```
Timeline:
Frames 1-10:  Giơ 1 ngón
Frames 11-20: Giơ 2 ngón
Frames 21-30: Giơ 3 ngón
```

---

### 9️⃣ **"Xoay tay"**

```
Timeline:
Frames 1-15:  Xoay tay 180° về trái
Frames 16-30: Xoay tay 180° về phải
```

---

### 🔟 **"Vẫy nhanh-chậm"**

```
Timeline:
Frames 1-10:  Vẫy nhanh (4 lần)
Frames 11-30: Vẫy chậm (2 lần)
```

---

## 📊 Kết quả mong đợi

### **Dataset tốt:**

```
5 động tác cơ bản:
├─ Vẫy tay: 15 sequences
├─ Lắc tay: 15 sequences
├─ Gật đầu: 15 sequences
├─ Tạm biệt: 15 sequences
└─ Đến đây: 15 sequences

TOTAL: 5 lớp, 75 sequences, 2,250 frames

Training: 50 epochs, ~45 seconds
Accuracy: 82-88%
```

---

## 💾 Save & Load

### **Dataset tự động lưu:**

```
File: dataset_dynamic.pkl

Có thể:
- Backup: copy sang nơi khác
- Restore: copy lại
- Share: gửi cho người khác
```

### **Continue training:**

```
1. Mở lại app
2. Dataset tự động load
3. Thu thập thêm sequences
4. Train lại → Model cập nhật
```

---

## 🎯 Challenge

**Thử thu thập và train 5 động tác cơ bản:**

```
□ Vẫy tay (15 seq) 
□ Lắc tay (15 seq)
□ Gật đầu (15 seq)
□ Tạm biệt (15 seq)
□ Đến đây (15 seq)

Target: Accuracy > 80%
Time: ~10-15 phút
```

---

## 📖 Tóm tắt nhanh

**Thu thập 1 động tác:**
```
1. Nhập nhãn
2. Bắt đầu ghi
3. Đợi 30/30
4. Làm động tác (~1s)
5. Lặp 15 lần
6. Dừng
```

**Huấn luyện:**
```
1. Tab "Huấn luyện"
2. Click "Huấn luyện LSTM"
3. Đợi ~45s
4. Check accuracy
```

**Nhận diện:**
```
1. Tab "Nhận diện"
2. Đợi 30/30
3. Làm động tác
4. Xem kết quả
```

---

**Good luck!** 🎉 File `sign_language_dynamic.py` đã sẵn sàng!
