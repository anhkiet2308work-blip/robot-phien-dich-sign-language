
"""
Ứng dụng Nhận diện Ký hiệu ĐỘNG (Dynamic Gestures) — v2
Chế độ:
  1) 🎙️ Dịch GIỌNG NÓI → CỬ CHỈ (VN)
  2) ✋ Dịch CỬ CHỈ → GIỌNG NÓI (VN)

Điểm mới:
- Tab "Chế độ" để chọn 2 mode ở trên.
- Tab "Huấn luyện" khóa bằng mật khẩu (mặc định: 1234). Có nút mở khóa.
- GIỌNG NÓI → VĂN BẢN: thu âm → nhận dạng → so khớp nhãn đã dạy (fuzzy) → vẽ ảnh động minh hoạ.
- CỬ CHỈ → GIỌNG NÓI: giữ tính năng nhận diện như trước, thêm phát âm tiếng Việt; nhãn đã nói 1 lần thì không nói lại (tránh lặp).
- Chống lặp nói nhãn bằng "lịch sử đã nói" và nút xoá lịch sử.

Yêu cầu:
- Python 3.8+
- OpenCV, TensorFlow / Keras, Pillow
- speech_recognition (STT), pyaudio (hoặc sounddevice + sr.Microphone), pyttsx3 (TTS offline)
  Cài đặt nhanh (Windows):
    pip install opencv-python tensorflow pillow speechrecognition pyaudio pyttsx3
  (Nếu gặp lỗi PyAudio trên Windows, có thể dùng wheel sẵn hoặc thay bằng sounddevice + sr.Recognizer(record) thủ công.)

Chạy:
  python sign_language_dynamic_v2.py
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext
import cv2
import numpy as np
import pickle
import os
from datetime import datetime, timedelta
from PIL import Image, ImageTk, ImageDraw
import threading
from collections import deque
import difflib

# Deep learning
import tensorflow as tf
from tensorflow import keras

# STT & TTS
try:
    import speech_recognition as sr
except Exception:
    sr = None

try:
    import pyttsx3
except Exception:
    pyttsx3 = None


class DynamicSignLanguageApp:
    def __init__(self, root):
        self.root = root
        self.root.title("✨ Ký Hiệu ĐỘNG v2 — GIỌNG NÓI ↔ CỬ CHỈ (VN)")
        self.root.geometry("1280x820")
        self.root.configure(bg='#0a0e1a')

        # ====== Parameters & State ======
        self.SEQUENCE_LENGTH = 30  # frames / ~1s
        self.frame_buffer = deque(maxlen=self.SEQUENCE_LENGTH)

        self.cap = None
        self.is_running = False
        self.is_collecting = False
        self.current_label = ""
        self.dataset = {}              # {label: [sequence ...]}
        self.model = None
        self.label_encoder = {}        # {label: idx}

        # Skin detection HSV ranges
        self.lower_skin = np.array([0, 20, 70], dtype=np.uint8)
        self.upper_skin = np.array([20, 255, 255], dtype=np.uint8)

        # Modes
        self.mode = tk.StringVar(value="gesture_to_speech")  # default
        self.train_locked = True
        self.TRAIN_PASSWORD = "1234"

        # Gesture → Speech: avoid repeats
        self.spoken_labels = set()
        self.last_spoken = {"label": None, "time": datetime.min}
        self.speak_cooldown = timedelta(seconds=4)

        # STT recognizer
        self.recognizer = sr.Recognizer() if sr else None
        self.stt_is_listening = False

        # TTS engine
        self.tts = None
        if pyttsx3:
            try:
                self.tts = pyttsx3.init()
                # Tinh chỉnh TTS VN (nếu OS có voice Vietnamese sẽ tự chọn; nếu không vẫn đọc được chữ VN theo giọng mặc định)
                self.tts.setProperty('rate', 175)
                self.tts.setProperty('volume', 1.0)
            except Exception:
                self.tts = None

        # Animation for Speech→Gesture
        self.anim_running = False
        self.anim_phase = 0
        self.anim_label_target = None  # label được map từ text
        self.anim_after_id = None

        # Load dataset
        self.load_dataset()

        # Build UI
        self.create_widgets()

    # ---------- UI ----------
    def create_widgets(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TNotebook', background='#0a0e1a', borderwidth=0)
        style.configure('TNotebook.Tab', background='#1f2937', foreground='white',
                        padding=[18, 10], font=('Arial', 11, 'bold'))
        style.map('TNotebook.Tab', background=[('selected', '#3b82f6')])

        main = tk.Frame(self.root, bg='#0a0e1a')
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Header
        header = tk.Frame(main, bg='#0a0e1a')
        header.pack(fill=tk.X, pady=(0, 8))
        tk.Label(header, text="✨ GIỌNG NÓI ↔ CỬ CHỈ (Vietnamese)",
                 font=('Arial', 20, 'bold'), bg='#0a0e1a', fg='white').pack()
        tk.Label(header, text="LSTM 30 frames • Dataset động tác tay • STT & TTS offline",
                 font=('Arial', 10), bg='#0a0e1a', fg='#9ca3af').pack()

        # Left: Camera / Animation
        left = tk.Frame(main, bg='#111827', relief=tk.RIDGE, bd=1)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left, text="📺 Khung hiển thị", font=('Arial', 14, 'bold'),
                 bg='#111827', fg='white').pack(pady=10)

        self.canvas = tk.Canvas(left, width=720, height=480, bg='black', highlightthickness=0)
        self.canvas.pack(padx=12, pady=6)

        # Camera controls
        cam_row = tk.Frame(left, bg='#111827')
        cam_row.pack(pady=10)
        self.btn_start_cam = tk.Button(cam_row, text="▶ Bật Camera", command=self.start_camera,
                                       bg='#3b82f6', fg='white', font=('Arial', 11, 'bold'),
                                       padx=16, pady=8, relief=tk.FLAT, cursor='hand2')
        self.btn_start_cam.pack(side=tk.LEFT, padx=6)
        self.btn_stop_cam = tk.Button(cam_row, text="⏹ Tắt Camera", command=self.stop_camera,
                                      bg='#ef4444', fg='white', font=('Arial', 11, 'bold'),
                                      padx=16, pady=8, relief=tk.FLAT, cursor='hand2', state=tk.DISABLED)
        self.btn_stop_cam.pack(side=tk.LEFT, padx=6)

        self.status_label = tk.Label(left, text="⚪ Chưa bật camera", font=('Arial', 10),
                                     bg='#111827', fg='#9ca3af')
        self.status_label.pack()

        self.buffer_label = tk.Label(left, text="Buffer: 0/30 frames", font=('Arial', 9),
                                     bg='#111827', fg='#f59e0b')
        self.buffer_label.pack(pady=2)

        # Right: Tabs
        right = tk.Frame(main, bg='#111827', relief=tk.RIDGE, bd=1)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))

        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self.create_mode_tab()
        self.create_collect_tab()
        self.create_train_tab()
        self.create_recognize_tab()

    def create_mode_tab(self):
        tab = tk.Frame(self.notebook, bg='#1f2937')
        self.notebook.add(tab, text='🧭 Chế độ')

        # Mode buttons
        row = tk.Frame(tab, bg='#1f2937')
        row.pack(pady=18, padx=20, fill=tk.X)

        b1 = tk.Button(row, text="🎙️ GIỌNG NÓI → CỬ CHỈ", font=('Arial', 13, 'bold'),
                       bg='#10b981', fg='white', padx=18, pady=14, relief=tk.FLAT,
                       command=lambda: self.set_mode("speech_to_gesture"))
        b1.pack(side=tk.LEFT, padx=6)

        b2 = tk.Button(row, text="✋ CỬ CHỈ → GIỌNG NÓI", font=('Arial', 13, 'bold'),
                       bg='#3b82f6', fg='white', padx=18, pady=14, relief=tk.FLAT,
                       command=lambda: self.set_mode("gesture_to_speech"))
        b2.pack(side=tk.LEFT, padx=6)

        # Speech → Gesture controls
        box = tk.LabelFrame(tab, text="🎙️ GIỌNG NÓI → CỬ CHỈ", bg='#1f2937', fg='white',
                            font=('Arial', 12, 'bold'), padx=12, pady=8)
        box.pack(fill=tk.X, padx=20, pady=(10, 8))

        self.lbl_stt_status = tk.Label(box, text="Mic: sẵn sàng", bg='#1f2937', fg='#9ca3af')
        self.lbl_stt_status.pack(anchor='w')

        ctrl = tk.Frame(box, bg='#1f2937')
        ctrl.pack(pady=6, fill=tk.X)
        self.btn_stt_start = tk.Button(ctrl, text="🎧 Bắt đầu nghe", bg='#10b981', fg='white',
                                       font=('Arial', 11, 'bold'), padx=14, pady=8, relief=tk.FLAT,
                                       command=self.start_listening)
        self.btn_stt_start.pack(side=tk.LEFT, padx=4)
        self.btn_stt_stop = tk.Button(ctrl, text="🛑 Dừng nghe", bg='#ef4444', fg='white',
                                      font=('Arial', 11, 'bold'), padx=14, pady=8, relief=tk.FLAT,
                                      command=self.stop_listening, state=tk.DISABLED)
        self.btn_stt_stop.pack(side=tk.LEFT, padx=4)

        tk.Label(box, text="Văn bản nhận được:", bg='#1f2937', fg='white', font=('Arial', 10, 'bold')).pack(anchor='w', pady=(6,0))
        self.txt_stt_text = tk.Text(box, height=3, bg='#0f172a', fg='#9ca3af', relief=tk.FLAT, font=('Courier', 10))
        self.txt_stt_text.pack(fill=tk.X)

        tk.Label(box, text="Nhãn khớp nhất:", bg='#1f2937', fg='white', font=('Arial', 10, 'bold')).pack(anchor='w', pady=(6,0))
        self.lbl_best_label = tk.Label(box, text="—", bg='#1f2937', fg='#3b82f6', font=('Arial', 16, 'bold'))
        self.lbl_best_label.pack(anchor='w', pady=(2,6))

        hint = "⚡ Mẹo: Nhãn học được ở tab Thu thập/Huấn luyện (VD: 'xin chào', 'cảm ơn'...). Hệ thống sẽ khớp gần đúng."
        tk.Label(box, text=hint, bg='#1f2937', fg='#9ca3af', font=('Arial', 9)).pack(anchor='w', pady=(0,6))

        # Anim info
        self.lbl_anim_info = tk.Label(tab, text="Ảnh động minh hoạ sẽ hiển thị trong khung bên trái.", bg='#1f2937', fg='#9ca3af')
        self.lbl_anim_info.pack(anchor='w', padx=22, pady=(0,8))

    def create_collect_tab(self):
        tab = tk.Frame(self.notebook, bg='#1f2937')
        self.notebook.add(tab, text='📚 Thu thập')

        # Input
        row = tk.Frame(tab, bg='#1f2937')
        row.pack(fill=tk.X, padx=20, pady=12)

        tk.Label(row, text="Nhập nhãn:", font=('Arial', 11, 'bold'),
                 bg='#1f2937', fg='white').pack(side=tk.LEFT, padx=(0, 8))

        self.entry_label = tk.Entry(row, font=('Arial', 11), bg='#374151', fg='white',
                                    relief=tk.FLAT, insertbackground='white', width=28)
        self.entry_label.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)

        # Buttons
        btn_row = tk.Frame(tab, bg='#1f2937')
        btn_row.pack(fill=tk.X, padx=20, pady=(0, 8))

        self.btn_start_collect = tk.Button(btn_row, text="🎬 Bắt đầu ghi", command=self.start_collecting,
                                           bg='#10b981', fg='white', font=('Arial', 11, 'bold'),
                                           padx=14, pady=8, relief=tk.FLAT, cursor='hand2')
        self.btn_start_collect.pack(side=tk.LEFT, padx=5)

        self.btn_stop_collect = tk.Button(btn_row, text="⏸ Dừng", command=self.stop_collecting,
                                          bg='#f59e0b', fg='white', font=('Arial', 11, 'bold'),
                                          padx=14, pady=8, relief=tk.FLAT, cursor='hand2', state=tk.DISABLED)
        self.btn_stop_collect.pack(side=tk.LEFT, padx=5)

        # Stats
        stats = tk.Frame(tab, bg='#1e293b', relief=tk.RAISED, bd=1)
        stats.pack(fill=tk.X, padx=20, pady=10)

        r = tk.Frame(stats, bg='#1e293b')
        r.pack(fill=tk.X, pady=10)

        self.stat_current = self.create_stat_box(r, "Sequences (label hiện tại)", "0")
        self.stat_labels = self.create_stat_box(r, "Tổng nhãn", "0")
        self.stat_total = self.create_stat_box(r, "Tổng sequences", "0")

        # Instructions
        instructions = tk.Label(tab,
            text=(
                "📖 Hướng dẫn thu thập động tác (30 frames):\n"
                "1) Nhập tên nhãn (VD: 'xin chào', 'cảm ơn'...)\n"
                "2) Bật Camera → 'Bắt đầu ghi'\n"
                "3) ĐỢI buffer đầy (30/30) rồi thực hiện động tác (~1 giây)\n"
                "4) Lặp 10–20 lần/nhãn để đủ dữ liệu • Bấm 'Dừng'\n"
            ),
            font=('Arial', 9), bg='#1f2937', fg='#9ca3af', justify=tk.LEFT
        )
        instructions.pack(pady=6, padx=20, anchor='w')

        # Log
        tk.Label(tab, text="📋 Log:", font=('Arial', 10, 'bold'),
                 bg='#1f2937', fg='white', anchor='w').pack(fill=tk.X, padx=20, pady=(6, 4))

        self.log_collect = scrolledtext.ScrolledText(tab, height=7, bg='#0f172a', fg='#9ca3af',
                                                     font=('Courier', 9), relief=tk.FLAT)
        self.log_collect.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 14))

        self.update_stats()

    def create_train_tab(self):
        tab = tk.Frame(self.notebook, bg='#1f2937')
        self.notebook.add(tab, text='🧠 Huấn luyện (🔒)')

        # Lock controls
        lock_row = tk.Frame(tab, bg='#1f2937')
        lock_row.pack(fill=tk.X, padx=20, pady=(14, 4))

        self.btn_unlock = tk.Button(lock_row, text="🔓 Mở khóa", bg='#10b981', fg='white',
                                    font=('Arial', 11, 'bold'), padx=12, pady=8, relief=tk.FLAT,
                                    command=self.unlock_train)
        self.btn_unlock.pack(side=tk.LEFT, padx=(0,6))

        self.lbl_lock = tk.Label(lock_row, text="Đã khoá — nhập mật khẩu để dùng chức năng huấn luyện.",
                                 bg='#1f2937', fg='#f59e0b')
        self.lbl_lock.pack(side=tk.LEFT)

        # Stats
        stats = tk.Frame(tab, bg='#1e293b', relief=tk.RAISED, bd=1)
        stats.pack(fill=tk.X, padx=20, pady=12)

        r = tk.Frame(stats, bg='#1e293b')
        r.pack(fill=tk.X, pady=10)

        self.stat_model_labels = self.create_stat_box(r, "Số lớp (nhãn)", "0")
        self.stat_model_samples = self.create_stat_box(r, "Tổng sequences", "0")
        self.stat_model_acc = self.create_stat_box(r, "Accuracy", "—")

        # Buttons
        btns = tk.Frame(tab, bg='#1f2937')
        btns.pack(fill=tk.X, padx=20, pady=6)

        self.btn_train = tk.Button(btns, text="🚀 Huấn luyện LSTM", command=self.train_model,
                                   bg='#3b82f6', fg='white', font=('Arial', 12, 'bold'),
                                   padx=18, pady=10, relief=tk.FLAT, state=tk.DISABLED)
        self.btn_train.pack(side=tk.LEFT, padx=5)

        self.btn_clear = tk.Button(btns, text="🗑️ Xoá dataset", command=self.clear_dataset,
                                   bg='#ef4444', fg='white', font=('Arial', 12, 'bold'),
                                   padx=18, pady=10, relief=tk.FLAT, state=tk.DISABLED)
        self.btn_clear.pack(side=tk.LEFT, padx=5)

        info = tk.Label(tab,
            text=(
                "ℹ️ LSTM học chuỗi 30 frames • Cần >= 2 nhãn, mỗi nhãn >= 10 sequences để có kết quả ổn.\n"
                "Sau khi huấn luyện xong, chuyển sang tab Nhận diện để dùng CỬ CHỈ → GIỌNG NÓI."
            ),
            font=('Arial', 9), bg='#1f2937', fg='#9ca3af', justify=tk.LEFT
        )
        info.pack(pady=8, padx=20, anchor='w')

        # Log
        tk.Label(tab, text="📋 Log:", font=('Arial', 10, 'bold'),
                 bg='#1f2937', fg='white', anchor='w').pack(fill=tk.X, padx=20, pady=(6, 4))

        self.log_train = scrolledtext.ScrolledText(tab, height=12, bg='#0f172a', fg='#9ca3af',
                                                   font=('Courier', 9), relief=tk.FLAT)
        self.log_train.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 14))

        # Dataset list
        tk.Label(tab, text="💾 Dataset:", font=('Arial', 10, 'bold'),
                 bg='#1f2937', fg='white', anchor='w').pack(fill=tk.X, padx=20, pady=(6, 4))
        self.dataset_list = tk.Listbox(tab, height=6, bg='#0f172a', fg='white',
                                       font=('Arial', 10), relief=tk.FLAT,
                                       selectbackground='#3b82f6')
        self.dataset_list.pack(fill=tk.BOTH, padx=20, pady=(0, 14))
        self.update_dataset_list()

    def create_recognize_tab(self):
        tab = tk.Frame(self.notebook, bg='#1f2937')
        self.notebook.add(tab, text='🎯 Nhận diện')

        # Prediction box
        pred_box = tk.Frame(tab, bg='#1e293b', relief=tk.RAISED, bd=2)
        pred_box.pack(fill=tk.X, padx=20, pady=16)

        self.pred_label = tk.Label(pred_box, text="—", font=('Arial', 36, 'bold'),
                                   bg='#1e293b', fg='#3b82f6', pady=14)
        self.pred_label.pack()
        self.pred_conf = tk.Label(pred_box, text="Thực hiện động tác trong khung...", font=('Arial', 12),
                                  bg='#1e293b', fg='#9ca3af', pady=4)
        self.pred_conf.pack()

        # TTS controls
        tts_box = tk.LabelFrame(tab, text="🔊 Giọng nói", bg='#1f2937', fg='white',
                                font=('Arial', 12, 'bold'), padx=12, pady=8)
        tts_box.pack(fill=tk.X, padx=20, pady=8)

        if self.tts:
            tk.Label(tts_box, text="Nhãn đã nói sẽ không lặp lại (tránh ồn).", bg='#1f2937', fg='#9ca3af').pack(anchor='w')
        else:
            tk.Label(tts_box, text="pyttsx3 chưa khả dụng — sẽ không phát âm.", bg='#1f2937', fg='#f59e0b').pack(anchor='w')

        ttk_sep = tk.Frame(tts_box, height=2, bg='#374151')
        ttk_sep.pack(fill=tk.X, pady=6)

        btn_row = tk.Frame(tts_box, bg='#1f2937')
        btn_row.pack(fill=tk.X)

        self.btn_clear_spoken = tk.Button(btn_row, text="🧹 Xoá lịch sử đã nói", bg='#374151', fg='white',
                                          font=('Arial', 10, 'bold'), padx=10, pady=6,
                                          relief=tk.FLAT, command=self.clear_spoken_history)
        self.btn_clear_spoken.pack(side=tk.LEFT, padx=4)

        tk.Label(tab, text="📋 Log:", font=('Arial', 10, 'bold'),
                 bg='#1f2937', fg='white', anchor='w').pack(fill=tk.X, padx=20, pady=(8, 4))

        self.log_recognize = scrolledtext.ScrolledText(tab, height=9, bg='#0f172a', fg='#9ca3af',
                                                       font=('Courier', 9), relief=tk.FLAT)
        self.log_recognize.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 14))

    def create_stat_box(self, parent, label, value):
        frame = tk.Frame(parent, bg='#1e293b')
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        val = tk.Label(frame, text=value, font=('Arial', 22, 'bold'), bg='#1e293b', fg='#3b82f6')
        val.pack()
        tk.Label(frame, text=label, font=('Arial', 9), bg='#1e293b', fg='#9ca3af').pack()
        return val

    # ---------- Camera ----------
    def start_camera(self):
        if self.is_running:
            return
        self.cap = cv2.VideoCapture(0)
        if self.cap.isOpened():
            self.is_running = True
            self.btn_start_cam.config(state=tk.DISABLED)
            self.btn_stop_cam.config(state=tk.NORMAL)
            self.status_label.config(text="🟢 Camera hoạt động", fg='#10b981')
            self.frame_buffer.clear()
            self.update_frame()
            self.log("✅ Camera đã bật", 'collect')
        else:
            messagebox.showerror("Lỗi", "Không thể mở camera!")

    def stop_camera(self):
        self.is_running = False
        if self.cap:
            self.cap.release()
        self.btn_start_cam.config(state=tk.NORMAL)
        self.btn_stop_cam.config(state=tk.DISABLED)
        self.status_label.config(text="⚪ Camera đã tắt", fg='#9ca3af')
        self.canvas.delete("all")
        self.frame_buffer.clear()
        self.log("⏹️ Camera đã tắt", 'collect')

    def update_frame(self):
        """Render camera frame OR animation frames (depending on mode)."""
        if not self.is_running:
            return

        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)

            # ROI rectangle
            cv2.rectangle(frame, (100, 100), (620, 420), (0, 255, 0), 2)
            cv2.putText(frame, "Thuc hien dong tac o day", (110, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)

            roi = frame[100:420, 100:620]

            # Skin mask
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, self.lower_skin, self.upper_skin)
            kernel = np.ones((3,3), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
            mask = cv2.GaussianBlur(mask, (5,5), 100)

            features = self.image_to_features(mask)
            if features is not None:
                self.frame_buffer.append(features)

            # Update buffer label
            self.buffer_label.config(text=f"Buffer: {len(self.frame_buffer)}/{self.SEQUENCE_LENGTH} frames")

            # Either recognize (gesture→speech) or just render
            if self.notebook.index('current') == 3 and self.model and len(self.frame_buffer) == self.SEQUENCE_LENGTH:
                if self.mode.get() == "gesture_to_speech":
                    self.recognize()

            # Compose mask preview overlay
            mask_3 = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
            frame[100:420, 100:620] = cv2.addWeighted(roi, 0.7, mask_3, 0.3, 0)

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_rgb = cv2.resize(frame_rgb, (720, 480))
            img = Image.fromarray(frame_rgb)

            # If we are in speech→gesture mode and have a target label => draw animation on top
            if self.mode.get() == "speech_to_gesture" and self.anim_running:
                img = self.draw_animation(img)

            imgtk = ImageTk.PhotoImage(image=img)
            self.canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)
            self.canvas.imgtk = imgtk

        self.root.after(10, self.update_frame)

    def image_to_features(self, mask):
        try:
            resized = cv2.resize(mask, (28,28))
            return resized.flatten() / 255.0
        except Exception:
            return None

    # ---------- Collect ----------
    def start_collecting(self):
        label = self.entry_label.get().strip()
        if not label:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập nhãn!")
            return
        if not self.is_running:
            messagebox.showwarning("Cảnh báo", "Hãy bật camera trước!")
            return
        self.current_label = label
        self.is_collecting = True
        if label not in self.dataset:
            self.dataset[label] = []
        self.frame_buffer.clear()
        self.btn_start_collect.config(state=tk.DISABLED)
        self.btn_stop_collect.config(state=tk.NORMAL)
        self.status_label.config(text=f"🔴 Đang ghi: {label}", fg='#ef4444')
        self.log(f"📚 Bắt đầu ghi: {label}", 'collect')
        self.log("⏳ Đợi buffer đầy (30 frames)...", 'collect')

    def stop_collecting(self):
        self.is_collecting = False
        self.current_label = ""
        self.btn_start_collect.config(state=tk.NORMAL)
        self.btn_stop_collect.config(state=tk.DISABLED)
        self.status_label.config(text="🟢 Camera hoạt động", fg='#10b981')
        self.save_dataset()
        self.update_stats()
        self.update_dataset_list()
        self.log("⏸️ Đã dừng ghi", 'collect')

    def collect_sequence(self):
        seq = np.array(list(self.frame_buffer))
        self.dataset[self.current_label].append(seq)
        count = len(self.dataset[self.current_label])
        self.stat_current.config(text=str(count))
        if count == 1:
            self.log("✅ Buffer đầy! Đã ghi sequence đầu tiên.", 'collect')
        elif count in (10, 20, 30):
            self.log(f"🎉 Đã có {count} sequences cho nhãn này.", 'collect')
        else:
            self.log(f"  → Sequence #{count}", 'collect')
        self.frame_buffer.clear()

    # ---------- Train (locked) ----------
    def unlock_train(self):
        pwd = simpledialog.askstring("Mật khẩu", "Nhập mật khẩu để mở khoá:", show='*')
        if pwd is None:
            return
        if pwd == self.TRAIN_PASSWORD:
            self.train_locked = False
            self.btn_train.config(state=tk.NORMAL)
            self.btn_clear.config(state=tk.NORMAL)
            self.lbl_lock.config(text="ĐÃ MỞ KHOÁ — bạn có thể huấn luyện hoặc xoá dataset.", fg='#10b981')
            self.notebook.tab(2, text='🧠 Huấn luyện')
        else:
            messagebox.showerror("Sai mật khẩu", "Mật khẩu không đúng!")

    def train_model(self):
        if self.train_locked:
            messagebox.showwarning("Khoá", "Bạn cần mở khoá để huấn luyện.")
            return
        labels = list(self.dataset.keys())
        if len(labels) < 2:
            messagebox.showwarning("Cảnh báo", "Cần ít nhất 2 nhãn!")
            return
        self.log("🚀 Bắt đầu huấn luyện LSTM...", 'train')
        th = threading.Thread(target=self._train_thread, daemon=True)
        th.start()

    def _train_thread(self):
        try:
            labels = list(self.dataset.keys())
            xs, ys = [], []
            self.label_encoder = {label: idx for idx, label in enumerate(labels)}

            for label, idx in self.label_encoder.items():
                for seq in self.dataset[label]:
                    xs.append(seq)
                    one_hot = np.zeros(len(labels))
                    one_hot[idx] = 1
                    ys.append(one_hot)

            xs = np.array(xs)  # (N, 30, 784)
            ys = np.array(ys)  # (N, C)

            self.root.after(0, lambda: self.log(f"📊 Dữ liệu: {xs.shape[0]} sequences, {len(labels)} lớp", 'train'))
            self.root.after(0, lambda: self.log(f"📊 Shape: {xs.shape}", 'train'))

            self.model = keras.Sequential([
                keras.layers.LSTM(64, return_sequences=True, input_shape=(self.SEQUENCE_LENGTH, 784)),
                keras.layers.Dropout(0.3),
                keras.layers.LSTM(32),
                keras.layers.Dropout(0.2),
                keras.layers.Dense(32, activation='relu'),
                keras.layers.Dense(len(labels), activation='softmax')
            ])
            self.model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

            self.root.after(0, lambda: self.log("🧠 Đang huấn luyện LSTM...", 'train'))

            history = self.model.fit(xs, ys, epochs=50, batch_size=16, validation_split=0.2, verbose=0)
            acc = float(history.history['val_accuracy'][-1])

            self.root.after(0, lambda: self.stat_model_labels.config(text=str(len(labels))))
            self.root.after(0, lambda: self.stat_model_samples.config(text=str(len(xs))))
            self.root.after(0, lambda: self.stat_model_acc.config(text=f"{acc*100:.1f}%"))
            self.root.after(0, lambda: self.log(f"✅ Hoàn thành! Accuracy: {acc*100:.1f}%", 'train'))
            self.root.after(0, lambda: messagebox.showinfo("Thành công", f"Model đã sẵn sàng! Acc: {acc*100:.1f}%"))
        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ Lỗi: {e}", 'train'))
            self.root.after(0, lambda: messagebox.showerror("Lỗi", str(e)))

    # ---------- Recognition (gesture → speech) ----------
    def recognize(self):
        if not self.model:
            return
        seq = np.array(list(self.frame_buffer)).reshape(1, self.SEQUENCE_LENGTH, 784)
        pred = self.model.predict(seq, verbose=0)[0]
        idx = int(np.argmax(pred))
        conf = float(pred[idx])

        labels = list(self.label_encoder.keys())
        label = labels[idx] if labels else "—"

        if conf > 0.6:
            self.pred_label.config(text=label)
            self.pred_conf.config(text=f"Độ tin cậy: {conf*100:.1f}%")
            self.log(f"✔ {label} ({conf*100:.1f}%)", 'recognize')
            # speak if not spoken recently
            self.speak_once(label)
        else:
            self.pred_label.config(text="❓")
            self.pred_conf.config(text="Không chắc chắn")

    def speak_once(self, text):
        now = datetime.now()
        if text in self.spoken_labels:
            return
        if self.last_spoken["label"] == text and now - self.last_spoken["time"] < self.speak_cooldown:
            return
        if not self.tts:
            return
        try:
            self.spoken_labels.add(text)
            self.last_spoken = {"label": text, "time": now}
            # Nói tiếng Việt (engine sẽ dùng giọng khả dụng)
            self.tts.say(text)
            self.tts.runAndWait()
        except Exception as e:
            self.log(f"TTS lỗi: {e}", 'recognize')

    def clear_spoken_history(self):
        self.spoken_labels.clear()
        self.last_spoken = {"label": None, "time": datetime.min}
        self.log("🧹 Đã xoá lịch sử 'đã nói'", 'recognize')

    # ---------- STT & Speech → Gesture ----------
    def start_listening(self):
        if not sr or not self.recognizer:
            messagebox.showerror("Thiếu thư viện", "Chưa cài 'speech_recognition'.")
            return
        if self.stt_is_listening:
            return
        try:
            self.mic = sr.Microphone()
        except Exception as e:
            messagebox.showerror("Mic lỗi", str(e))
            return

        self.stt_is_listening = True
        self.btn_stt_start.config(state=tk.DISABLED)
        self.btn_stt_stop.config(state=tk.NORMAL)
        self.lbl_stt_status.config(text="🎙️ Đang nghe...", fg='#10b981')

        th = threading.Thread(target=self._listen_loop, daemon=True)
        th.start()

    def stop_listening(self):
        self.stt_is_listening = False
        self.btn_stt_start.config(state=tk.NORMAL)
        self.btn_stt_stop.config(state=tk.DISABLED)
        self.lbl_stt_status.config(text="Mic: sẵn sàng", fg='#9ca3af')

    def _listen_loop(self):
        with self.mic as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.6)
        while self.stt_is_listening:
            try:
                with self.mic as source:
                    audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=5)
                # Thử Google Web (cần internet); nếu offline, người dùng có thể thay bằng VOSK/Whisper cục bộ
                try:
                    text = self.recognizer.recognize_google(audio, language='vi-VN')
                except Exception:
                    text = ""  # im lặng nếu không nhận
                if text:
                    self.root.after(0, lambda t=text: self.on_text_captured(t))
            except sr.WaitTimeoutError:
                continue
            except Exception:
                continue

    def on_text_captured(self, text):
        self.txt_stt_text.delete('1.0', tk.END)
        self.txt_stt_text.insert(tk.END, text)

        best_label, score = self.best_match_label(text)
        if best_label:
            self.lbl_best_label.config(text=f"{best_label}  (match {int(score*100)}%)")
            # Trigger animation drawing in left canvas
            self.anim_label_target = best_label
            self.start_animation()
        else:
            self.lbl_best_label.config(text="—")
            self.stop_animation()

    def best_match_label(self, text):
        """Fuzzy match: so sánh văn bản với danh sách nhãn đã dạy."""
        labels = list(self.dataset.keys())
        if not labels:
            return None, 0.0
        text_norm = text.strip().lower()
        labels_norm = [s.strip().lower() for s in labels]
        match = difflib.get_close_matches(text_norm, labels_norm, n=1, cutoff=0.4)
        if not match:
            # thử điểm tương đồng
            scores = [(lab, difflib.SequenceMatcher(None, text_norm, lab).ratio()) for lab in labels_norm]
            best = max(scores, key=lambda x: x[1])
            idx = labels_norm.index(best[0])
            return labels[idx], float(best[1])
        else:
            idx = labels_norm.index(match[0])
            return labels[idx], 1.0

    # ---------- Animation (for Speech → Gesture) ----------
    def start_animation(self):
        if self.anim_running:
            return
        self.anim_running = True
        self.anim_phase = 0

    def stop_animation(self):
        self.anim_running = False
        if self.anim_after_id:
            try:
                self.root.after_cancel(self.anim_after_id)
            except Exception:
                pass
            self.anim_after_id = None

    def draw_animation(self, base_img: Image.Image):
        """Vẽ ảnh động đơn giản mô phỏng động tác cho 'anim_label_target'."""
        im = base_img.copy()
        draw = ImageDraw.Draw(im)

        # khu vực ROI tương ứng camera (100:620, 100:420) đã scale về 720x480
        # ước lượng tương đối để vẽ hiệu ứng trong vùng đó:
        left, top = int(720*(100/720)), int(480*(100/480))
        right, bottom = int(720*(620/720)), int(480*(420/480))

        # 4 pha chuyển động một 'bàn tay' (hình tròn) qua lại
        cx = np.interp(self.anim_phase % 40, [0, 20, 39], [left+40, right-40, left+40])
        cy = (top + bottom) // 2
        r = 28

        # màu cyan cho nổi
        draw.ellipse((cx-r, cy-r, cx+r, cy+r), outline=(72, 216, 255), width=4)
        # caption label
        label_text = f"Minh hoạ: {self.anim_label_target}"
        draw.rectangle((left, top-36, left+360, top-6), fill=(0,0,0,160))
        # PIL default font
        draw.text((left+10, top-30), label_text, fill=(200, 230, 255))

        self.anim_phase += 2
        if self.anim_phase > 1e9:
            self.anim_phase = 0

        # schedule next frame
        self.anim_after_id = self.root.after(60, lambda: None)  # placeholder to keep cadence
        return im

    # ---------- Utilities ----------
    def save_dataset(self):
        with open('dataset_dynamic.pkl', 'wb') as f:
            pickle.dump(self.dataset, f)

    def load_dataset(self):
        if os.path.exists('dataset_dynamic.pkl'):
            with open('dataset_dynamic.pkl', 'rb') as f:
                self.dataset = pickle.load(f)

    def clear_dataset(self):
        if messagebox.askyesno("Xác nhận", "Xoá toàn bộ dataset?"):
            self.dataset = {}
            self.model = None
            self.save_dataset()
            self.update_stats()
            self.update_dataset_list()
            self.log("🗑️ Đã xoá dataset", 'train')

    def update_stats(self):
        labels = list(self.dataset.keys())
        total = sum(len(v) for v in self.dataset.values())
        current = len(self.dataset.get(self.current_label, []))
        self.stat_current.config(text=str(current))
        self.stat_labels.config(text=str(len(labels)))
        self.stat_total.config(text=str(total))

    def update_dataset_list(self):
        self.dataset_list.delete(0, tk.END)
        for label, seqs in self.dataset.items():
            self.dataset_list.insert(tk.END, f"{label} ({len(seqs)} sequences)")

    def log(self, message, tab='collect'):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {message}\n"
        if tab == 'collect':
            if hasattr(self, 'log_collect'):
                self.log_collect.insert(tk.END, line)
                self.log_collect.see(tk.END)
        elif tab == 'train':
            if hasattr(self, 'log_train'):
                self.log_train.insert(tk.END, line)
                self.log_train.see(tk.END)
        elif tab == 'recognize':
            if hasattr(self, 'log_recognize'):
                self.log_recognize.insert(tk.END, line)
                self.log_recognize.see(tk.END)

    def set_mode(self, m):
        self.mode.set(m)
        if m == "speech_to_gesture":
            self.log("🧭 Chế độ: GIỌNG NÓI → CỬ CHỈ", 'collect')
            self.start_animation()  # để có nền animation khi có kết quả
        else:
            self.log("🧭 Chế độ: CỬ CHỈ → GIỌNG NÓI", 'collect')
            self.stop_animation()

    def on_closing(self):
        self.stop_listening()
        self.stop_camera()
        try:
            if self.tts:
                self.tts.stop()
        except Exception:
            pass
        self.root.destroy()

    # ---------- Periodic checks in update_frame ----------
    def _maybe_collect_or_recognize(self):
        """Called inside update_frame if needed; kept for compatibility."""
        if self.is_collecting and self.current_label and len(self.frame_buffer) == self.SEQUENCE_LENGTH:
            self.collect_sequence()
        elif self.notebook.index('current') == 3 and self.model and len(self.frame_buffer) == self.SEQUENCE_LENGTH:
            if self.mode.get() == "gesture_to_speech":
                self.recognize()


if __name__ == "__main__":
    root = tk.Tk()
    app = DynamicSignLanguageApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
