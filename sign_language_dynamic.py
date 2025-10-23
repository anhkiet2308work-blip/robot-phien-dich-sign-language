"""
Ứng dụng Nhận diện Ký hiệu ĐỘNG (Dynamic Gestures)
Hỗ trợ: Chuỗi động tác, không chỉ tư thế tĩnh
Model: LSTM (Long Short-Term Memory)
Yêu cầu: Python 3.8+, OpenCV, TensorFlow
Chạy: python sign_language_dynamic.py
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import cv2
import numpy as np
import pickle
import os
from datetime import datetime
from PIL import Image, ImageTk
import threading
from collections import deque
import tensorflow as tf
from tensorflow import keras

class DynamicSignLanguageApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🎬 Học Ký Hiệu ĐỘNG (Dynamic Gestures)")
        self.root.geometry("1200x750")
        self.root.configure(bg='#0a0e1a')
        
        # Tham số sequences
        self.SEQUENCE_LENGTH = 30  # 30 frames = ~1 giây
        self.frame_buffer = deque(maxlen=self.SEQUENCE_LENGTH)
        
        # Biến toàn cục
        self.cap = None
        self.is_running = False
        self.is_collecting = False
        self.current_label = ""
        self.dataset = {}  # {label: [sequence1, sequence2, ...]}
        self.model = None
        self.label_encoder = {}
        
        # Skin detection
        self.lower_skin = np.array([0, 20, 70], dtype=np.uint8)
        self.upper_skin = np.array([20, 255, 255], dtype=np.uint8)
        
        # Tải dataset
        self.load_dataset()
        
        # Tạo UI
        self.create_widgets()
        
    def create_widgets(self):
        # Style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TNotebook', background='#0a0e1a', borderwidth=0)
        style.configure('TNotebook.Tab', background='#1f2937', foreground='white', 
                       padding=[20, 10], font=('Arial', 11, 'bold'))
        style.map('TNotebook.Tab', background=[('selected', '#3b82f6')])
        
        # Main
        main_frame = tk.Frame(self.root, bg='#0a0e1a')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Header
        header = tk.Frame(main_frame, bg='#0a0e1a')
        header.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(header, text="🎬 Nhận Diện Ký Hiệu ĐỘNG", 
                font=('Arial', 20, 'bold'), bg='#0a0e1a', fg='white').pack()
        tk.Label(header, text="Hỗ trợ chuỗi động tác - Model: LSTM",
                font=('Arial', 10), bg='#0a0e1a', fg='#9ca3af').pack()
        
        # Left panel
        left_panel = tk.Frame(main_frame, bg='#111827', relief=tk.RAISED, bd=1)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        tk.Label(left_panel, text="📹 Camera", font=('Arial', 14, 'bold'),
                bg='#111827', fg='white').pack(pady=10)
        
        self.canvas = tk.Canvas(left_panel, width=640, height=480, bg='black',
                               highlightthickness=0)
        self.canvas.pack(padx=10, pady=5)
        
        # Controls
        cam_controls = tk.Frame(left_panel, bg='#111827')
        cam_controls.pack(pady=10)
        
        self.btn_start_cam = tk.Button(cam_controls, text="▶ Bật Camera",
                                       command=self.start_camera, bg='#3b82f6',
                                       fg='white', font=('Arial', 11, 'bold'),
                                       padx=15, pady=8, relief=tk.FLAT, cursor='hand2')
        self.btn_start_cam.pack(side=tk.LEFT, padx=5)
        
        self.btn_stop_cam = tk.Button(cam_controls, text="⏹ Tắt Camera",
                                      command=self.stop_camera, bg='#ef4444',
                                      fg='white', font=('Arial', 11, 'bold'),
                                      padx=15, pady=8, relief=tk.FLAT,
                                      state=tk.DISABLED, cursor='hand2')
        self.btn_stop_cam.pack(side=tk.LEFT, padx=5)
        
        self.status_label = tk.Label(left_panel, text="⚪ Chưa bật camera",
                                    font=('Arial', 10), bg='#111827', fg='#9ca3af')
        self.status_label.pack(pady=5)
        
        # Buffer indicator
        self.buffer_label = tk.Label(left_panel, text="Buffer: 0/30 frames",
                                     font=('Arial', 9), bg='#111827', fg='#f59e0b')
        self.buffer_label.pack(pady=2)
        
        info = tk.Label(left_panel, 
                       text="💡 Thực hiện TOÀN BỘ động tác trong vùng xanh",
                       font=('Arial', 9), bg='#111827', fg='#10b981')
        info.pack(pady=5)
        
        # Right panel
        right_panel = tk.Frame(main_frame, bg='#111827', relief=tk.RAISED, bd=1)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        self.notebook = ttk.Notebook(right_panel)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.create_collect_tab()
        self.create_train_tab()
        self.create_recognize_tab()
        
    def create_collect_tab(self):
        tab = tk.Frame(self.notebook, bg='#1f2937')
        self.notebook.add(tab, text='📚 Thu thập')
        
        # Input
        input_frame = tk.Frame(tab, bg='#1f2937')
        input_frame.pack(fill=tk.X, padx=20, pady=15)
        
        tk.Label(input_frame, text="Nhập nhãn:", font=('Arial', 11, 'bold'),
                bg='#1f2937', fg='white').pack(side=tk.LEFT, padx=(0, 10))
        
        self.entry_label = tk.Entry(input_frame, font=('Arial', 11),
                                    bg='#374151', fg='white', relief=tk.FLAT,
                                    insertbackground='white', width=25)
        self.entry_label.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)
        
        # Buttons
        btn_frame = tk.Frame(tab, bg='#1f2937')
        btn_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.btn_start_collect = tk.Button(btn_frame, text="🎬 Bắt đầu ghi",
                                          command=self.start_collecting,
                                          bg='#10b981', fg='white',
                                          font=('Arial', 11, 'bold'),
                                          padx=15, pady=8, relief=tk.FLAT, cursor='hand2')
        self.btn_start_collect.pack(side=tk.LEFT, padx=5)
        
        self.btn_stop_collect = tk.Button(btn_frame, text="⏸ Dừng",
                                         command=self.stop_collecting,
                                         bg='#f59e0b', fg='white',
                                         font=('Arial', 11, 'bold'),
                                         padx=15, pady=8, relief=tk.FLAT,
                                         state=tk.DISABLED, cursor='hand2')
        self.btn_stop_collect.pack(side=tk.LEFT, padx=5)
        
        # Stats
        stats_frame = tk.Frame(tab, bg='#1e293b', relief=tk.RAISED, bd=1)
        stats_frame.pack(fill=tk.X, padx=20, pady=10)
        
        stat_row = tk.Frame(stats_frame, bg='#1e293b')
        stat_row.pack(fill=tk.X, pady=10)
        
        self.stat_current = self.create_stat_box(stat_row, "Sequences", "0")
        self.stat_labels = self.create_stat_box(stat_row, "Tổng nhãn", "0")
        self.stat_total = self.create_stat_box(stat_row, "Tổng seq", "0")
        
        # Instructions
        instructions = tk.Label(tab, 
                               text="📖 Cách thu thập ĐỘNG TÁC:\n\n"
                                    "1. Nhập tên động tác (VD: 'Vẫy tay', 'Gật đầu')\n"
                                    "2. Click 'Bắt đầu ghi'\n"
                                    "3. ĐỢI buffer đầy (30 frames)\n"
                                    "4. Thực hiện TOÀN BỘ động tác (~1 giây)\n"
                                    "5. Lặp lại 10-20 lần\n"
                                    "6. Click 'Dừng'\n\n"
                                    "⚠️ Mỗi lần ghi = 1 sequence đầy đủ!",
                               font=('Arial', 9), bg='#1f2937', fg='#9ca3af',
                               justify=tk.LEFT)
        instructions.pack(pady=10, padx=20)
        
        # Log
        tk.Label(tab, text="📋 Log:", font=('Arial', 10, 'bold'),
                bg='#1f2937', fg='white', anchor='w').pack(fill=tk.X, padx=20, pady=(5, 5))
        
        self.log_collect = scrolledtext.ScrolledText(tab, height=6,
                                                     bg='#0f172a', fg='#9ca3af',
                                                     font=('Courier', 9), relief=tk.FLAT)
        self.log_collect.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))
        
        self.update_stats()
        
    def create_train_tab(self):
        tab = tk.Frame(self.notebook, bg='#1f2937')
        self.notebook.add(tab, text='🧠 Huấn luyện')
        
        # Stats
        stats_frame = tk.Frame(tab, bg='#1e293b', relief=tk.RAISED, bd=1)
        stats_frame.pack(fill=tk.X, padx=20, pady=15)
        
        stat_row = tk.Frame(stats_frame, bg='#1e293b')
        stat_row.pack(fill=tk.X, pady=10)
        
        self.stat_model_labels = self.create_stat_box(stat_row, "Số lớp", "0")
        self.stat_model_samples = self.create_stat_box(stat_row, "Tổng seq", "0")
        self.stat_model_acc = self.create_stat_box(stat_row, "Accuracy", "—")
        
        # Buttons
        btn_frame = tk.Frame(tab, bg='#1f2937')
        btn_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Button(btn_frame, text="🚀 Huấn luyện LSTM",
                 command=self.train_model, bg='#3b82f6', fg='white',
                 font=('Arial', 12, 'bold'), padx=20, pady=10,
                 relief=tk.FLAT, cursor='hand2').pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="🗑️ Xóa dataset",
                 command=self.clear_dataset, bg='#ef4444', fg='white',
                 font=('Arial', 12, 'bold'), padx=20, pady=10,
                 relief=tk.FLAT, cursor='hand2').pack(side=tk.LEFT, padx=5)
        
        # Info
        info = tk.Label(tab,
                       text="ℹ️ Model LSTM học chuỗi 30 frames\n"
                            "Mỗi sequence = 1 động tác hoàn chỉnh\n"
                            "Cần ít nhất 10 sequences mỗi nhãn",
                       font=('Arial', 9), bg='#1f2937', fg='#9ca3af',
                       justify=tk.LEFT)
        info.pack(pady=10)
        
        # Log
        tk.Label(tab, text="📋 Log:", font=('Arial', 10, 'bold'),
                bg='#1f2937', fg='white', anchor='w').pack(fill=tk.X, padx=20, pady=(5, 5))
        
        self.log_train = scrolledtext.ScrolledText(tab, height=12,
                                                   bg='#0f172a', fg='#9ca3af',
                                                   font=('Courier', 9), relief=tk.FLAT)
        self.log_train.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))
        
        # Dataset list
        tk.Label(tab, text="💾 Dataset:", font=('Arial', 10, 'bold'),
                bg='#1f2937', fg='white', anchor='w').pack(fill=tk.X, padx=20, pady=(5, 5))
        
        self.dataset_list = tk.Listbox(tab, height=6, bg='#0f172a', fg='white',
                                       font=('Arial', 10), relief=tk.FLAT,
                                       selectbackground='#3b82f6')
        self.dataset_list.pack(fill=tk.BOTH, padx=20, pady=(0, 15))
        
        self.update_dataset_list()
        
    def create_recognize_tab(self):
        tab = tk.Frame(self.notebook, bg='#1f2937')
        self.notebook.add(tab, text='🎯 Nhận diện')
        
        # Prediction
        pred_frame = tk.Frame(tab, bg='#1e293b', relief=tk.RAISED, bd=2)
        pred_frame.pack(fill=tk.X, padx=20, pady=20)
        
        self.pred_label = tk.Label(pred_frame, text="—",
                                   font=('Arial', 32, 'bold'),
                                   bg='#1e293b', fg='#3b82f6', pady=15)
        self.pred_label.pack()
        
        self.pred_conf = tk.Label(pred_frame, text="Thực hiện động tác...",
                                 font=('Arial', 12), bg='#1e293b',
                                 fg='#9ca3af', pady=5)
        self.pred_conf.pack()
        
        # Instructions
        instructions = tk.Frame(tab, bg='#1f2937')
        instructions.pack(fill=tk.X, padx=20, pady=15)
        
        tk.Label(instructions, text="📖 Cách nhận diện:",
                font=('Arial', 11, 'bold'), bg='#1f2937',
                fg='white', anchor='w').pack(fill=tk.X)
        
        tips = [
            "1. Đảm bảo đã huấn luyện LSTM",
            "2. Bật camera",
            "3. ĐỢI buffer đầy (30 frames)",
            "4. Thực hiện TOÀN BỘ động tác",
            "5. Model sẽ dự đoán liên tục"
        ]
        
        for tip in tips:
            tk.Label(instructions, text=tip, font=('Arial', 10),
                    bg='#1f2937', fg='#9ca3af', anchor='w').pack(fill=tk.X, pady=2)
        
        # Log
        tk.Label(tab, text="📋 Log:", font=('Arial', 10, 'bold'),
                bg='#1f2937', fg='white', anchor='w').pack(fill=tk.X, padx=20, pady=(10, 5))
        
        self.log_recognize = scrolledtext.ScrolledText(tab, height=8,
                                                       bg='#0f172a', fg='#9ca3af',
                                                       font=('Courier', 9), relief=tk.FLAT)
        self.log_recognize.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))
        
    def create_stat_box(self, parent, label, value):
        frame = tk.Frame(parent, bg='#1e293b')
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        val_label = tk.Label(frame, text=value, font=('Arial', 24, 'bold'),
                            bg='#1e293b', fg='#3b82f6')
        val_label.pack()
        
        tk.Label(frame, text=label, font=('Arial', 9),
                bg='#1e293b', fg='#9ca3af').pack()
        
        return val_label
    
    # ============= CAMERA =============
    def start_camera(self):
        if not self.is_running:
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
        if self.is_running:
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.flip(frame, 1)
                
                # ROI
                cv2.rectangle(frame, (100, 100), (540, 380), (0, 255, 0), 2)
                cv2.putText(frame, "Thuc hien dong tac o day", (110, 90),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                roi = frame[100:380, 100:540]
                
                # Skin detection
                hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                mask = cv2.inRange(hsv, self.lower_skin, self.upper_skin)
                
                kernel = np.ones((3,3), np.uint8)
                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
                mask = cv2.GaussianBlur(mask, (5, 5), 100)
                
                # Features
                features = self.image_to_features(mask)
                
                if features is not None:
                    self.frame_buffer.append(features)
                
                # Update buffer indicator
                buffer_size = len(self.frame_buffer)
                self.buffer_label.config(text=f"Buffer: {buffer_size}/30 frames")
                
                # Thu thập hoặc nhận diện
                if self.is_collecting and self.current_label and buffer_size == self.SEQUENCE_LENGTH:
                    self.collect_sequence()
                elif self.notebook.index('current') == 2 and self.model and buffer_size == self.SEQUENCE_LENGTH:
                    self.recognize()
                
                # Hiển thị
                mask_3channel = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
                frame[100:380, 100:540] = cv2.addWeighted(roi, 0.7, mask_3channel, 0.3, 0)
                
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_rgb = cv2.resize(frame_rgb, (640, 480))
                img = Image.fromarray(frame_rgb)
                imgtk = ImageTk.PhotoImage(image=img)
                self.canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)
                self.canvas.imgtk = imgtk
            
            self.root.after(10, self.update_frame)
    
    def image_to_features(self, mask):
        try:
            resized = cv2.resize(mask, (28, 28))
            features = resized.flatten() / 255.0
            return features
        except:
            return None
    
    # ============= COLLECTION =============
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
        """Lưu 1 sequence đầy đủ (30 frames)"""
        sequence = np.array(list(self.frame_buffer))
        self.dataset[self.current_label].append(sequence)
        count = len(self.dataset[self.current_label])
        self.stat_current.config(text=str(count))
        
        if count == 1:
            self.log("✅ Buffer đầy! Đã ghi sequence đầu tiên", 'collect')
        elif count == 10:
            self.log("✅ Đủ 10 sequences! Tiếp tục hoặc dừng", 'collect')
        elif count == 20:
            self.log("🎉 20 sequences! Rất tốt!", 'collect')
        else:
            self.log(f"  → Sequence #{count}", 'collect')
        
        # Clear buffer để ghi sequence mới
        self.frame_buffer.clear()
    
    # ============= TRAINING =============
    def train_model(self):
        labels = list(self.dataset.keys())
        if len(labels) < 2:
            messagebox.showwarning("Cảnh báo", "Cần ít nhất 2 nhãn!")
            return
        
        self.log("🚀 Bắt đầu huấn luyện LSTM...", 'train')
        
        thread = threading.Thread(target=self._train_model_thread)
        thread.daemon = True
        thread.start()
    
    def _train_model_thread(self):
        try:
            labels = list(self.dataset.keys())
            xs, ys = [], []
            self.label_encoder = {label: idx for idx, label in enumerate(labels)}
            
            for label, idx in self.label_encoder.items():
                for sequence in self.dataset[label]:
                    xs.append(sequence)
                    one_hot = np.zeros(len(labels))
                    one_hot[idx] = 1
                    ys.append(one_hot)
            
            xs = np.array(xs)  # Shape: (num_sequences, 30, 784)
            ys = np.array(ys)  # Shape: (num_sequences, num_classes)
            
            self.log(f"📊 Dữ liệu: {xs.shape[0]} sequences, {len(labels)} lớp", 'train')
            self.log(f"📊 Shape: {xs.shape}", 'train')
            
            # LSTM Model
            self.model = keras.Sequential([
                keras.layers.LSTM(64, return_sequences=True, input_shape=(self.SEQUENCE_LENGTH, 784)),
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
            
            self.log("🧠 Đang huấn luyện LSTM...", 'train')
            
            history = self.model.fit(
                xs, ys,
                epochs=50,
                batch_size=16,
                validation_split=0.2,
                verbose=0
            )
            
            accuracy = history.history['val_accuracy'][-1]
            
            self.root.after(0, lambda: self.stat_model_labels.config(text=str(len(labels))))
            self.root.after(0, lambda: self.stat_model_samples.config(text=str(len(xs))))
            self.root.after(0, lambda: self.stat_model_acc.config(text=f"{accuracy*100:.1f}%"))
            
            self.log(f"✅ Hoàn thành! Accuracy: {accuracy*100:.1f}%", 'train')
            self.root.after(0, lambda: messagebox.showinfo(
                "Thành công",
                f"Model LSTM đã sẵn sàng!\nĐộ chính xác: {accuracy*100:.1f}%"
            ))
            
        except Exception as e:
            self.log(f"❌ Lỗi: {str(e)}", 'train')
            self.root.after(0, lambda: messagebox.showerror("Lỗi", str(e)))
    
    # ============= RECOGNITION =============
    def recognize(self):
        if not self.model:
            return
        
        sequence = np.array(list(self.frame_buffer))
        sequence = sequence.reshape(1, self.SEQUENCE_LENGTH, 784)
        
        prediction = self.model.predict(sequence, verbose=0)
        
        max_idx = np.argmax(prediction[0])
        confidence = prediction[0][max_idx]
        
        labels = list(self.label_encoder.keys())
        predicted_label = labels[max_idx]
        
        if confidence > 0.6:
            self.pred_label.config(text=predicted_label)
            self.pred_conf.config(text=f"Độ tin cậy: {confidence*100:.1f}%")
        else:
            self.pred_label.config(text="❓")
            self.pred_conf.config(text="Không chắc chắn")
    
    # ============= UTILITIES =============
    def update_stats(self):
        labels = list(self.dataset.keys())
        total = sum(len(sequences) for sequences in self.dataset.values())
        current = len(self.dataset.get(self.current_label, []))
        
        self.stat_current.config(text=str(current))
        self.stat_labels.config(text=str(len(labels)))
        self.stat_total.config(text=str(total))
    
    def update_dataset_list(self):
        self.dataset_list.delete(0, tk.END)
        for label, sequences in self.dataset.items():
            self.dataset_list.insert(tk.END, f"{label} ({len(sequences)} sequences)")
    
    def log(self, message, tab='collect'):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}\n"
        
        if tab == 'collect':
            self.log_collect.insert(tk.END, log_msg)
            self.log_collect.see(tk.END)
        elif tab == 'train':
            self.log_train.insert(tk.END, log_msg)
            self.log_train.see(tk.END)
        elif tab == 'recognize':
            self.log_recognize.insert(tk.END, log_msg)
            self.log_recognize.see(tk.END)
    
    def save_dataset(self):
        with open('dataset_dynamic.pkl', 'wb') as f:
            pickle.dump(self.dataset, f)
    
    def load_dataset(self):
        if os.path.exists('dataset_dynamic.pkl'):
            with open('dataset_dynamic.pkl', 'rb') as f:
                self.dataset = pickle.load(f)
    
    def clear_dataset(self):
        if messagebox.askyesno("Xác nhận", "Xóa toàn bộ dataset?"):
            self.dataset = {}
            self.model = None
            self.save_dataset()
            self.update_stats()
            self.update_dataset_list()
            self.log("🗑️ Đã xóa dataset", 'train')
    
    def on_closing(self):
        self.stop_camera()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = DynamicSignLanguageApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
