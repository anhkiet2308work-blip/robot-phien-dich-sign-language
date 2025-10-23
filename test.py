"""
COMPLETE WORKING VERSION
Tất cả tính năng hoạt động đầy đủ:
- Thu thập ✓
- Huấn luyện ✓
- Nhận diện → Giọng nói (TTS) ✓
- Giọng nói → Play animation ✓
"""

import tkinter as tk
from tkinter import messagebox, scrolledtext
import cv2
import numpy as np
import pickle, json, os, time
from datetime import datetime
from PIL import Image, ImageTk, ImageDraw
import threading
from collections import deque
import difflib
from pathlib import Path

os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL','2')
import tensorflow as tf
from tensorflow import keras

try:
    import speech_recognition as sr
except:
    sr = None

try:
    import pyttsx3
except:
    pyttsx3 = None


class CompleteApp:
    SEQ_LEN = 30
    
    def __init__(self, root):
        self.root = root
        self.root.title("Ký hiệu ĐỘNG - COMPLETE VERSION")
        self.root.geometry("1200x800")
        self.root.configure(bg='lightgray')
        
        # Data
        self.cap = None
        self.is_running = False
        self.frame_buffer = deque(maxlen=self.SEQ_LEN)
        self.raw_roi_buffer = deque(maxlen=self.SEQ_LEN)
        self.is_collecting = False
        self.current_label = ""
        
        self.dataset = {}
        self.labels_order = []
        self.model = None
        
        self.dataset_pkl = Path("dataset_dynamic.pkl")
        self.frames_root = Path("frames")
        self.frames_root.mkdir(exist_ok=True)
        self.frames_index_path = Path("frames_index.json")
        self.frames_index = {}
        
        self.lower_skin = np.array([0, 20, 70], dtype=np.uint8)
        self.upper_skin = np.array([20, 255, 255], dtype=np.uint8)
        
        # Speech recognition
        self.recognizer = sr.Recognizer() if sr else None
        self.stt_is_listening = False
        
        # Text to speech
        self.tts = None
        if pyttsx3:
            try:
                self.tts = pyttsx3.init()
                self.tts.setProperty('rate', 175)
                self.tts.setProperty('volume', 1.0)
                print("✓ TTS initialized")
            except Exception as e:
                print(f"✗ TTS error: {e}")
                self.tts = None
        else:
            print("✗ pyttsx3 not available")
        
        self.spoken_once = set()
        
        # Playback
        self.playback_frames = []
        self.playback_idx = 0
        self.playback_running = False
        self.playback_label = None
        
        self.load_dataset()
        self.load_frames_index()
        
        self.build_ui()
        
        print("\n✅ APP READY - All features enabled!\n")
    
    def build_ui(self):
        # Title
        title = tk.Label(
            self.root,
            text="🤖 KÝ HIỆU ĐỘNG - COMPLETE",
            font=('Arial', 24, 'bold'),
            bg='lightgray',
            fg='black'
        )
        title.pack(pady=15)
        
        # Mode buttons
        btn_frame = tk.Frame(self.root, bg='lightgray')
        btn_frame.pack(pady=10)
        
        tk.Button(
            btn_frame,
            text="✋ THU THẬP",
            font=('Arial', 13, 'bold'),
            bg='green',
            fg='white',
            padx=18,
            pady=10,
            command=lambda: self.show_mode("collect")
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            btn_frame,
            text="🧠 HUẤN LUYỆN",
            font=('Arial', 13, 'bold'),
            bg='purple',
            fg='white',
            padx=18,
            pady=10,
            command=lambda: self.show_mode("train")
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            btn_frame,
            text="🎯 NHẬN DIỆN",
            font=('Arial', 13, 'bold'),
            bg='blue',
            fg='white',
            padx=18,
            pady=10,
            command=lambda: self.show_mode("recognize")
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            btn_frame,
            text="🎙️ GIỌNG NÓI",
            font=('Arial', 13, 'bold'),
            bg='orange',
            fg='white',
            padx=18,
            pady=10,
            command=lambda: self.show_mode("speech")
        ).pack(side=tk.LEFT, padx=5)
        
        # Canvas
        self.canvas = tk.Canvas(self.root, width=800, height=400, bg='black')
        self.canvas.pack(pady=10)
        
        # Camera controls
        cam_frame = tk.Frame(self.root, bg='lightgray')
        cam_frame.pack(pady=8)
        
        self.btn_cam_on = tk.Button(
            cam_frame,
            text="📷 BẬT CAMERA",
            font=('Arial', 12, 'bold'),
            bg='blue',
            fg='white',
            padx=20,
            pady=8,
            command=self.start_camera
        )
        self.btn_cam_on.pack(side=tk.LEFT, padx=5)
        
        self.btn_cam_off = tk.Button(
            cam_frame,
            text="⏹ TẮT",
            font=('Arial', 12, 'bold'),
            bg='red',
            fg='white',
            padx=20,
            pady=8,
            command=self.stop_camera,
            state=tk.DISABLED
        )
        self.btn_cam_off.pack(side=tk.LEFT, padx=5)
        
        self.lbl_buffer = tk.Label(
            cam_frame,
            text="Buffer: 0/30",
            font=('Arial', 12, 'bold'),
            bg='lightgray',
            fg='black'
        )
        self.lbl_buffer.pack(side=tk.LEFT, padx=15)
        
        # Control panel
        self.control_frame = tk.Frame(self.root, bg='white', width=1100, height=220)
        self.control_frame.pack(pady=10, padx=20, fill=tk.BOTH)
        
        self.mode_label = tk.Label(
            self.control_frame,
            text="👆 Chọn chế độ bên trên",
            font=('Arial', 14, 'bold'),
            bg='white',
            fg='blue'
        )
        self.mode_label.pack(pady=20)
        
        # Build all panels
        self.build_collect_panel()
        self.build_train_panel()
        self.build_recognize_panel()
        self.build_speech_panel()
        
        # Hide all initially
        self.collect_panel.pack_forget()
        self.train_panel.pack_forget()
        self.recognize_panel.pack_forget()
        self.speech_panel.pack_forget()
    
    def build_collect_panel(self):
        self.collect_panel = tk.Frame(self.control_frame, bg='white')
        
        tk.Label(
            self.collect_panel,
            text="Nhập tên động tác:",
            font=('Arial', 12, 'bold'),
            bg='white'
        ).pack()
        
        self.entry_label = tk.Entry(self.collect_panel, font=('Arial', 13), width=30)
        self.entry_label.pack(pady=5)
        
        btn_frame = tk.Frame(self.collect_panel, bg='white')
        btn_frame.pack(pady=10)
        
        self.btn_start_collect = tk.Button(
            btn_frame,
            text="🎬 GHI",
            font=('Arial', 12, 'bold'),
            bg='green',
            fg='white',
            padx=20,
            pady=8,
            command=self.start_collecting
        )
        self.btn_start_collect.pack(side=tk.LEFT, padx=5)
        
        self.btn_stop_collect = tk.Button(
            btn_frame,
            text="⏸ DỪNG",
            font=('Arial', 12, 'bold'),
            bg='orange',
            fg='white',
            padx=20,
            pady=8,
            command=self.stop_collecting,
            state=tk.DISABLED
        )
        self.btn_stop_collect.pack(side=tk.LEFT, padx=5)
        
        self.lbl_collect_stats = tk.Label(
            self.collect_panel,
            text="Sequences: 0 | Tổng: 0",
            font=('Arial', 11, 'bold'),
            bg='white'
        )
        self.lbl_collect_stats.pack(pady=10)
        
        tk.Label(
            self.collect_panel,
            text="💡 Tip: Ghi 15-20 sequences cho mỗi động tác",
            font=('Arial', 10),
            bg='white',
            fg='gray'
        ).pack()
    
    def build_train_panel(self):
        self.train_panel = tk.Frame(self.control_frame, bg='white')
        
        self.lbl_train_stats = tk.Label(
            self.train_panel,
            text="Dataset: 0 nhãn, 0 sequences\nChưa có mô hình",
            font=('Arial', 12, 'bold'),
            bg='white'
        )
        self.lbl_train_stats.pack(pady=15)
        
        btn_frame = tk.Frame(self.train_panel, bg='white')
        btn_frame.pack(pady=10)
        
        tk.Button(
            btn_frame,
            text="🚀 HUẤN LUYỆN",
            font=('Arial', 13, 'bold'),
            bg='purple',
            fg='white',
            padx=30,
            pady=12,
            command=self.train_model
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            btn_frame,
            text="🗑️ XÓA",
            font=('Arial', 13, 'bold'),
            bg='red',
            fg='white',
            padx=30,
            pady=12,
            command=self.clear_dataset
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Label(
            self.train_panel,
            text="⚠️ Cần ít nhất 2 nhãn để train",
            font=('Arial', 10),
            bg='white',
            fg='gray'
        ).pack(pady=5)
    
    def build_recognize_panel(self):
        self.recognize_panel = tk.Frame(self.control_frame, bg='white')
        
        tk.Label(
            self.recognize_panel,
            text="Kết quả nhận diện:",
            font=('Arial', 12, 'bold'),
            bg='white'
        ).pack(pady=5)
        
        self.lbl_pred = tk.Label(
            self.recognize_panel,
            text="—",
            font=('Arial', 36, 'bold'),
            bg='white',
            fg='blue'
        )
        self.lbl_pred.pack(pady=10)
        
        self.lbl_conf = tk.Label(
            self.recognize_panel,
            text="Chờ buffer đầy...",
            font=('Arial', 13),
            bg='white'
        )
        self.lbl_conf.pack()
        
        tk.Label(
            self.recognize_panel,
            text="🔊 Hệ thống sẽ tự động đọc tên động tác",
            font=('Arial', 10),
            bg='white',
            fg='gray'
        ).pack(pady=10)
    
    def build_speech_panel(self):
        self.speech_panel = tk.Frame(self.control_frame, bg='white')
        
        self.lbl_mic = tk.Label(
            self.speech_panel,
            text="🎤 Mic: Sẵn sàng",
            font=('Arial', 12, 'bold'),
            bg='white'
        )
        self.lbl_mic.pack(pady=10)
        
        btn_frame = tk.Frame(self.speech_panel, bg='white')
        btn_frame.pack(pady=8)
        
        self.btn_listen = tk.Button(
            btn_frame,
            text="🎧 NGHE",
            font=('Arial', 12, 'bold'),
            bg='green',
            fg='white',
            padx=20,
            pady=8,
            command=self.start_listening
        )
        self.btn_listen.pack(side=tk.LEFT, padx=5)
        
        self.btn_stop_listen = tk.Button(
            btn_frame,
            text="🛑 DỪNG",
            font=('Arial', 12, 'bold'),
            bg='red',
            fg='white',
            padx=20,
            pady=8,
            command=self.stop_listening,
            state=tk.DISABLED
        )
        self.btn_stop_listen.pack(side=tk.LEFT, padx=5)
        
        tk.Label(
            self.speech_panel,
            text="Văn bản:",
            font=('Arial', 11, 'bold'),
            bg='white'
        ).pack(pady=3)
        
        self.txt_speech = tk.Text(self.speech_panel, height=2, width=40, font=('Arial', 12))
        self.txt_speech.pack(pady=5)
        
        self.lbl_match = tk.Label(
            self.speech_panel,
            text="Khớp: —",
            font=('Arial', 13, 'bold'),
            bg='white',
            fg='blue'
        )
        self.lbl_match.pack(pady=8)
        
        tk.Label(
            self.speech_panel,
            text="📹 Animation sẽ tự động phát khi tìm thấy",
            font=('Arial', 10),
            bg='white',
            fg='gray'
        ).pack()
    
    def show_mode(self, mode):
        # Hide all
        self.collect_panel.pack_forget()
        self.train_panel.pack_forget()
        self.recognize_panel.pack_forget()
        self.speech_panel.pack_forget()
        
        # Stop playback if running
        self.playback_running = False
        
        # Show selected
        if mode == "collect":
            self.mode_label.config(text="✋ CHẾ ĐỘ: THU THẬP MẪU")
            self.collect_panel.pack(fill=tk.BOTH, expand=True, pady=10)
            self.update_stats()
            
        elif mode == "train":
            self.mode_label.config(text="🧠 CHẾ ĐỘ: HUẤN LUYỆN MÔ HÌNH")
            self.train_panel.pack(fill=tk.BOTH, expand=True, pady=10)
            self.update_stats()
            
        elif mode == "recognize":
            self.mode_label.config(text="🎯 CHẾ ĐỘ: NHẬN DIỆN ĐỘNG TÁC")
            self.recognize_panel.pack(fill=tk.BOTH, expand=True, pady=10)
            
        elif mode == "speech":
            self.mode_label.config(text="🎙️ CHẾ ĐỘ: GIỌNG NÓI → CỬ CHỈ")
            self.speech_panel.pack(fill=tk.BOTH, expand=True, pady=10)
            self.stop_camera()  # Tắt camera cho mode này
    
    # ===== CAMERA =====
    
    def start_camera(self):
        if self.is_running:
            return
        
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            messagebox.showerror("Lỗi", "Không mở được camera!")
            return
        
        self.is_running = True
        self.btn_cam_on.config(state=tk.DISABLED)
        self.btn_cam_off.config(state=tk.NORMAL)
        self.frame_buffer.clear()
        
        # Stop playback when camera starts
        self.playback_running = False
        
        self.update_frame()
        print("✓ Camera started")
    
    def stop_camera(self):
        if not self.is_running:
            return
        
        self.is_running = False
        if self.cap:
            self.cap.release()
        
        self.btn_cam_on.config(state=tk.NORMAL)
        self.btn_cam_off.config(state=tk.DISABLED)
        self.canvas.delete("all")
        self.frame_buffer.clear()
        print("✓ Camera stopped")
    
    def update_frame(self):
        if not self.is_running:
            return
        
        ret, frame = self.cap.read()
        if not ret:
            self.root.after(10, self.update_frame)
            return
        
        frame = cv2.flip(frame, 1)
        cv2.rectangle(frame, (100, 100), (540, 380), (0, 255, 0), 2)
        cv2.putText(frame, "Dong tac o day", (110, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        roi = frame[100:380, 100:540]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower_skin, self.upper_skin)
        
        kernel = np.ones((3,3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
        mask = cv2.GaussianBlur(mask, (5, 5), 100)
        
        features = self.image_to_features(mask)
        if features is not None:
            self.frame_buffer.append(features)
            self.raw_roi_buffer.append(roi.copy())
        
        buffer_size = len(self.frame_buffer)
        self.lbl_buffer.config(text=f"Buffer: {buffer_size}/30")
        
        if buffer_size == self.SEQ_LEN:
            if self.is_collecting and self.current_label:
                self.collect_sequence()
            elif self.model:
                self.recognize_current()
        
        mask_3ch = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        frame[100:380, 100:540] = cv2.addWeighted(roi, 0.7, mask_3ch, 0.3, 0)
        
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        img = img.resize((800, 400), Image.LANCZOS)
        
        photo = ImageTk.PhotoImage(img)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=photo)
        self.canvas.image = photo
        
        self.root.after(10, self.update_frame)
    
    def image_to_features(self, mask):
        try:
            resized = cv2.resize(mask, (28, 28))
            return resized.flatten() / 255.0
        except:
            return None
    
    # ===== COLLECTION =====
    
    def start_collecting(self):
        label = self.entry_label.get().strip()
        if not label:
            messagebox.showwarning("Cảnh báo", "Nhập nhãn!")
            return
        
        if not self.is_running:
            messagebox.showwarning("Cảnh báo", "Bật camera trước!")
            return
        
        self.current_label = label
        self.is_collecting = True
        
        if label not in self.dataset:
            self.dataset[label] = []
            if label not in self.labels_order:
                self.labels_order.append(label)
        
        self.frame_buffer.clear()
        self.raw_roi_buffer.clear()
        
        self.btn_start_collect.config(state=tk.DISABLED)
        self.btn_stop_collect.config(state=tk.NORMAL)
        print(f"✓ Started collecting: {label}")
    
    def stop_collecting(self):
        self.is_collecting = False
        self.current_label = ""
        
        self.btn_start_collect.config(state=tk.NORMAL)
        self.btn_stop_collect.config(state=tk.DISABLED)
        
        self.save_dataset()
        self.save_frames_index()
        self.update_stats()
        print("✓ Stopped collecting")
    
    def collect_sequence(self):
        sequence = np.array(list(self.frame_buffer))
        self.dataset[self.current_label].append(sequence)
        
        count = len(self.dataset[self.current_label])
        self.update_stats()
        print(f"✓ Collected seq #{count} for '{self.current_label}'")
        
        self.save_frames_for_sequence(self.current_label, count - 1)
        self.frame_buffer.clear()
        self.raw_roi_buffer.clear()
    
    def save_frames_for_sequence(self, label, seq_idx):
        try:
            label_dir = self.frames_root / label
            label_dir.mkdir(exist_ok=True)
            
            seq_dir = label_dir / f"seq_{seq_idx:04d}"
            seq_dir.mkdir(exist_ok=True)
            
            for i, roi in enumerate(self.raw_roi_buffer):
                frame_path = seq_dir / f"frame_{i:03d}.jpg"
                cv2.imwrite(str(frame_path), roi)
            
            if label not in self.frames_index:
                self.frames_index[label] = []
            
            rel_path = f"{label}/seq_{seq_idx:04d}"
            self.frames_index[label].append(rel_path)
        except Exception as e:
            print(f"✗ Error saving frames: {e}")
    
    # ===== TRAINING =====
    
    def train_model(self):
        labels = [lb for lb in self.labels_order if lb in self.dataset and len(self.dataset[lb]) > 0]
        if len(labels) < 2:
            messagebox.showwarning("Cảnh báo", "Cần ít nhất 2 nhãn!")
            return
        
        print("✓ Starting training...")
        threading.Thread(target=self._train_thread, daemon=True).start()
    
    def _train_thread(self):
        try:
            labels = [lb for lb in self.labels_order if lb in self.dataset and len(self.dataset[lb]) > 0]
            xs, ys = [], []
            
            for idx, label in enumerate(labels):
                for seq in self.dataset[label]:
                    xs.append(seq)
                    one_hot = np.zeros(len(labels))
                    one_hot[idx] = 1
                    ys.append(one_hot)
            
            xs = np.array(xs)
            ys = np.array(ys)
            
            print(f"✓ Training data: {len(xs)} sequences, {len(labels)} classes")
            
            self.model = keras.Sequential([
                keras.layers.LSTM(64, return_sequences=True, input_shape=(self.SEQ_LEN, 784)),
                keras.layers.Dropout(0.3),
                keras.layers.LSTM(32),
                keras.layers.Dropout(0.2),
                keras.layers.Dense(32, activation='relu'),
                keras.layers.Dense(len(labels), activation='softmax')
            ])
            
            self.model.compile(
                optimizer='adam',
                loss='categorical_crossentropy',
                metrics=['accuracy']
            )
            
            print("✓ Training model (50 epochs)...")
            
            history = self.model.fit(
                xs, ys,
                epochs=50,
                batch_size=16,
                validation_split=0.2,
                verbose=0
            )
            
            acc = history.history['val_accuracy'][-1]
            
            print(f"✓ Training complete! Accuracy: {acc*100:.1f}%")
            
            self.root.after(0, lambda: self.lbl_train_stats.config(
                text=f"Dataset: {len(labels)} nhãn, {len(xs)} seq\n✅ Mô hình: {acc*100:.1f}% accuracy"
            ))
            self.root.after(0, lambda: messagebox.showinfo(
                "Thành công!", f"Model đã sẵn sàng!\nAccuracy: {acc*100:.1f}%"
            ))
            
        except Exception as e:
            print(f"✗ Training error: {e}")
            self.root.after(0, lambda: messagebox.showerror("Lỗi", f"Training thất bại: {e}"))
    
    def clear_dataset(self):
        if not messagebox.askyesno("Xác nhận", "Xóa toàn bộ dataset?"):
            return
        
        self.dataset = {}
        self.labels_order = []
        self.model = None
        self.frames_index = {}
        
        try:
            if self.frames_root.exists():
                for p in self.frames_root.rglob("*"):
                    if p.is_file():
                        p.unlink()
                for p in sorted(self.frames_root.glob("*"), reverse=True):
                    if p.is_dir():
                        try:
                            p.rmdir()
                        except:
                            pass
        except:
            pass
        
        self.save_dataset()
        self.save_frames_index()
        self.update_stats()
        print("✓ Dataset cleared")
    
    # ===== RECOGNITION (Gesture → Speech) =====
    
    def recognize_current(self):
        if not self.model:
            return
        
        seq = np.array(list(self.frame_buffer)).reshape(1, self.SEQ_LEN, 784)
        probs = self.model.predict(seq, verbose=0)[0]
        
        idx = int(np.argmax(probs))
        conf = float(probs[idx])
        
        labels = [lb for lb in self.labels_order if lb in self.dataset and len(self.dataset[lb]) > 0]
        label = labels[idx] if idx < len(labels) else "—"
        
        if conf > 0.6:
            self.lbl_pred.config(text=label)
            self.lbl_conf.config(text=f"Độ tin cậy: {conf*100:.1f}%")
            
            print(f"✓ Recognized: {label} ({conf*100:.1f}%)")
            
            # TTS - Đọc tên động tác
            if self.tts and label not in self.spoken_once:
                self.spoken_once.add(label)
                print(f"🔊 Speaking: {label}")
                try:
                    # Run TTS in thread to not block UI
                    threading.Thread(target=lambda: self._speak(label), daemon=True).start()
                except Exception as e:
                    print(f"✗ TTS error: {e}")
        else:
            self.lbl_pred.config(text="❓")
            self.lbl_conf.config(text="Không chắc chắn")
    
    def _speak(self, text):
        """Speak text using TTS"""
        try:
            self.tts.say(text)
            self.tts.runAndWait()
        except Exception as e:
            print(f"✗ Speak error: {e}")
    
    # ===== SPEECH RECOGNITION (Speech → Gesture) =====
    
    def start_listening(self):
        if not sr or not self.recognizer:
            messagebox.showerror("Thiếu thư viện", "speech_recognition chưa được cài đặt!")
            return
        
        try:
            self.mic = sr.Microphone()
        except Exception as e:
            messagebox.showerror("Lỗi Mic", str(e))
            return
        
        self.stt_is_listening = True
        self.btn_listen.config(state=tk.DISABLED)
        self.btn_stop_listen.config(state=tk.NORMAL)
        self.lbl_mic.config(text="🎙️ Đang nghe...", fg='green')
        
        threading.Thread(target=self._listen_loop, daemon=True).start()
        print("✓ Listening started")
    
    def stop_listening(self):
        self.stt_is_listening = False
        self.btn_listen.config(state=tk.NORMAL)
        self.btn_stop_listen.config(state=tk.DISABLED)
        self.lbl_mic.config(text="🎤 Mic: Sẵn sàng", fg='black')
        print("✓ Listening stopped")
    
    def _listen_loop(self):
        with self.mic as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.6)
        
        while self.stt_is_listening:
            try:
                with self.mic as source:
                    audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=5)
                
                try:
                    text = self.recognizer.recognize_google(audio, language='vi-VN')
                except:
                    text = ""
                
                if text:
                    self.root.after(0, lambda t=text: self.on_speech_text(t))
            except:
                continue
    
    def on_speech_text(self, text):
        """Handle recognized speech"""
        print(f"✓ Heard: {text}")
        
        self.txt_speech.delete('1.0', tk.END)
        self.txt_speech.insert(tk.END, text)
        
        best, score = self.best_label(text)
        self.lbl_match.config(text=f"Khớp: {best or '—'} ({int(score*100)}%)")
        
        if best and score > 0.5:
            print(f"✓ Matched label: {best} ({score*100:.0f}%)")
            # Play animation
            self.play_label(best)
        else:
            print(f"✗ No good match (best: {best}, score: {score*100:.0f}%)")
    
    def best_label(self, text):
        """Find best matching label for text"""
        labels = [lb for lb in self.labels_order if lb in self.dataset and len(self.dataset[lb]) > 0]
        if not labels:
            return None, 0.0
        
        t = text.strip().lower()
        lst = [s.lower() for s in labels]
        
        # Try exact match first
        m = difflib.get_close_matches(t, lst, n=1, cutoff=0.4)
        if m:
            idx = lst.index(m[0])
            return labels[idx], 1.0
        
        # Try fuzzy match
        scores = [(lab, difflib.SequenceMatcher(None, t, lab.lower()).ratio()) for lab in labels]
        best = max(scores, key=lambda x: x[1])
        return best[0], float(best[1])
    
    def play_label(self, label):
        """Play animation for label"""
        seq_dirs = self.frames_index.get(label, [])
        if not seq_dirs:
            print(f"✗ No frames for label: {label}")
            messagebox.showinfo("Thiếu dữ liệu", f"Chưa có frames cho nhãn '{label}'")
            return
        
        # Get last sequence
        seq_rel = seq_dirs[-1]
        seq_dir = self.frames_root / seq_rel
        frames = sorted(seq_dir.glob("*.jpg"))
        
        if not frames:
            print(f"✗ Empty sequence: {seq_rel}")
            messagebox.showinfo("Thiếu dữ liệu", f"Sequence rỗng")
            return
        
        print(f"✓ Playing animation: {label} ({len(frames)} frames)")
        
        # Load frames
        self.playback_frames = [Image.open(p) for p in frames]
        self.playback_idx = 0
        self.playback_label = label
        self.playback_running = True
        
        # Stop camera if running
        if self.is_running:
            self.stop_camera()
        
        # Start playback
        self.render_playback()
    
    def render_playback(self):
        """Render playback animation"""
        if not self.playback_running or not self.playback_frames:
            return
        
        # Get canvas size
        canvas_w = 800
        canvas_h = 400
        
        # Create base image
        base = Image.new("RGB", (canvas_w, canvas_h), (30, 30, 30))
        
        # Calculate frame size (70% of canvas)
        w, h = int(canvas_w * 0.7), int(canvas_h * 0.7)
        x, y = (canvas_w - w) // 2, (canvas_h - h) // 2
        
        # Get current frame
        frame_img = self.playback_frames[self.playback_idx % len(self.playback_frames)]
        frame_img = frame_img.resize((w, h), Image.LANCZOS)
        base.paste(frame_img, (x, y))
        
        # Draw label overlay
        draw = ImageDraw.Draw(base)
        draw.rectangle((x, y - 40, x + 280, y - 10), fill=(50, 50, 50))
        draw.text((x + 15, y - 32), f"📹 {self.playback_label}", fill=(255, 255, 255))
        
        # Display
        photo = ImageTk.PhotoImage(base)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=photo)
        self.canvas.image = photo
        
        # Next frame
        self.playback_idx = (self.playback_idx + 1) % len(self.playback_frames)
        
        # Schedule next frame (60ms = ~17fps)
        self.root.after(60, self.render_playback)
    
    # ===== UTILS =====
    
    def update_stats(self):
        tot_labels = len([lb for lb in self.dataset if len(self.dataset[lb]) > 0])
        tot_seq = sum(len(v) for v in self.dataset.values())
        cur = len(self.dataset.get(self.current_label, [])) if self.current_label else 0
        
        self.lbl_collect_stats.config(text=f"Sequences: {cur} | Tổng nhãn: {tot_labels} | Tổng: {tot_seq}")
        self.lbl_train_stats.config(
            text=f"Dataset: {tot_labels} nhãn, {tot_seq} sequences\n"
                 f"{'✅ Mô hình sẵn sàng' if self.model else 'Chưa có mô hình'}"
        )
    
    def save_dataset(self):
        with open(self.dataset_pkl, 'wb') as f:
            pickle.dump({
                'dataset': self.dataset,
                'labels_order': self.labels_order
            }, f)
    
    def load_dataset(self):
        if self.dataset_pkl.exists():
            try:
                obj = pickle.load(open(self.dataset_pkl, 'rb'))
                if isinstance(obj, dict) and 'dataset' in obj:
                    self.dataset = obj.get('dataset', {})
                    self.labels_order = obj.get('labels_order', list(self.dataset.keys()))
                else:
                    self.dataset = obj
                    self.labels_order = list(self.dataset.keys())
                print(f"✓ Loaded dataset: {len(self.dataset)} labels")
            except:
                self.dataset = {}
                self.labels_order = []
    
    def save_frames_index(self):
        with open(self.frames_index_path, 'w', encoding='utf-8') as f:
            json.dump(self.frames_index, f, ensure_ascii=False, indent=2)
    
    def load_frames_index(self):
        if self.frames_index_path.exists():
            try:
                self.frames_index = json.load(
                    open(self.frames_index_path, 'r', encoding='utf-8')
                )
                print(f"✓ Loaded frames index")
            except:
                self.frames_index = {}


if __name__ == "__main__":
    print("\n" + "="*60)
    print("KÝ HIỆU ĐỘNG - COMPLETE VERSION")
    print("Tất cả tính năng hoạt động:")
    print("  ✓ Thu thập mẫu")
    print("  ✓ Huấn luyện LSTM")
    print("  ✓ Nhận diện → TTS (text-to-speech)")
    print("  ✓ Giọng nói → Play animation")
    print("="*60 + "\n")
    
    root = tk.Tk()
    app = CompleteApp(root)
    root.mainloop()