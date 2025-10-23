
"""
Ký hiệu ĐỘNG v3 — GIỌNG NÓI ↔ CỬ CHỈ (VN)
- Sửa lỗi: train & nhận diện không chạy do thiếu trigger; UI chồng chéo
- Thêm: Ghi lại (xoá sequence cuối) nếu ghi sai
- Thêm: Khi thu thập, lưu toàn bộ frame ROI của mỗi sequence vào thư mục frames/<label>/<seq_id>/
- Chế độ 🎙️ Giọng nói → Cử chỉ: phát "animation thật" từ các frame đã ghi (không dùng vẽ minh hoạ)
"""


import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext
import cv2
import numpy as np
import pickle, json, os, time
from datetime import datetime, timedelta
from PIL import Image, ImageTk
import threading
from collections import deque
import difflib
from pathlib import Path

# DL
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


class DynamicSignV3:
    SEQ_LEN = 30

    def __init__(self, root):
        self.root = root
        self.root.title("Ký hiệu ĐỘNG v3 — GIỌNG NÓI ↔ CỬ CHỈ (VN)")
        self.root.geometry("1280x820")
        self.root.minsize(1100, 720)

        # State
        self.cap = None
        self.is_running = False
        self.frame_buffer = deque(maxlen=self.SEQ_LEN)      # features
        self.raw_roi_buffer = deque(maxlen=self.SEQ_LEN)    # raw PIL frames for saving
        self.is_collecting = False
        self.current_label = ""

        self.dataset = {}            # {label: [np.array(seq_features)]}
        self.labels_order = []       # stable order
        self.model = None

        # paths
        self.dataset_pkl = Path("dataset_dynamic.pkl")
        self.frames_root = Path("frames")
        self.frames_root.mkdir(exist_ok=True)
        self.frames_index_path = Path("frames_index.json")
        self.frames_index = {}       # {label: [seq_dir_rel,...]}

        # HSV skin
        import numpy as np
        self.lower_skin = np.array([0, 20, 70], dtype=np.uint8)
        self.upper_skin = np.array([20, 255, 255], dtype=np.uint8)

        # Modes
        self.mode = tk.StringVar(value="gesture_to_speech")
        self.train_locked = True
        self.TRAIN_PASSWORD = "1234"

        # Speech
        self.recognizer = sr.Recognizer() if sr else None
        self.stt_is_listening = False

        # TTS
        self.tts = None
        if pyttsx3:
            try:
                self.tts = pyttsx3.init()
                self.tts.setProperty('rate', 175)
                self.tts.setProperty('volume', 1.0)
            except Exception:
                self.tts = None
        self.spoken_once = set()

        # Playback for Speech→Gesture
        self.playback_frames = []    # list[PIL.Image]
        self.playback_idx = 0
        self.playback_running = False
        self.playback_label = None

        # Load
        self.load_dataset()
        self.load_frames_index()

        # UI
        self.build_ui()


    # ---------------- UI ----------------
    def build_ui(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TNotebook.Tab', padding=[12, 6])

        container = tk.Frame(self.root, bg='#0b1220')
        container.pack(fill=tk.BOTH, expand=True)

        left = tk.Frame(container, bg='#0b1220')
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10,5), pady=10)
        right = tk.Frame(container, bg='#0b1220')
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5,10), pady=10)

        # Left — camera canvas + controls
        tk.Label(left, text="Khung hiển thị", fg='white', bg='#0b1220', font=('Arial', 14, 'bold')).pack(anchor='w', pady=(0,6))
        self.canvas = tk.Canvas(left, width=800, height=500, bg='black', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        camrow = tk.Frame(left, bg='#0b1220')
        camrow.pack(fill=tk.X, pady=8)
        self.btn_start = tk.Button(camrow, text="▶ Bật Camera", command=self.start_camera, bg='#2563eb', fg='white')
        self.btn_start.pack(side=tk.LEFT, padx=4)
        self.btn_stop = tk.Button(camrow, text="⏹ Tắt", command=self.stop_camera, bg='#ef4444', fg='white', state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=4)

        self.lbl_status = tk.Label(camrow, text="⚪ Chưa bật camera", fg='#9ca3af', bg='#0b1220')
        self.lbl_status.pack(side=tk.LEFT, padx=10)
        self.lbl_buffer = tk.Label(camrow, text="Buffer 0/30", fg='#f59e0b', bg='#0b1220')
        self.lbl_buffer.pack(side=tk.LEFT, padx=10)

        # Right — notebook
        self.nb = ttk.Notebook(right)
        self.nb.pack(fill=tk.BOTH, expand=True)

        self.tab_mode = tk.Frame(self.nb, bg='#0f172a')
        self.nb.add(self.tab_mode, text="🧭 Chế độ")

        self.tab_collect = tk.Frame(self.nb, bg='#0f172a')
        self.nb.add(self.tab_collect, text="📚 Thu thập")

        self.tab_train = tk.Frame(self.nb, bg='#0f172a')
        self.nb.add(self.tab_train, text="🧠 Huấn luyện (🔒)")

        self.tab_recog = tk.Frame(self.nb, bg='#0f172a')
        self.nb.add(self.tab_recog, text="🎯 Nhận diện")

        self.build_mode_tab()
        self.build_collect_tab()
        self.build_train_tab()
        self.build_recog_tab()


    def build_mode_tab(self):
        row = tk.Frame(self.tab_mode, bg='#0f172a')
        row.pack(padx=14, pady=14, anchor='w')
        tk.Button(row, text="🎙️ Giọng nói → Cử chỉ", bg='#10b981', fg='white',
                  command=lambda: self.set_mode("speech_to_gesture")).pack(side=tk.LEFT, padx=6)
        tk.Button(row, text="✋ Cử chỉ → Giọng nói", bg='#2563eb', fg='white',
                  command=lambda: self.set_mode("gesture_to_speech")).pack(side=tk.LEFT, padx=6)

        box = tk.LabelFrame(self.tab_mode, text="🎙️ Giọng nói → Cử chỉ", bg='#0f172a', fg='white')
        box.pack(fill=tk.X, padx=14, pady=8)
        self.lbl_stt = tk.Label(box, text="Mic: sẵn sàng", fg='#9ca3af', bg='#0f172a')
        self.lbl_stt.pack(anchor='w', pady=(4,2))
        ctrl = tk.Frame(box, bg='#0f172a'); ctrl.pack(anchor='w', pady=4)
        self.btn_listen = tk.Button(ctrl, text="🎧 Bắt đầu nghe", bg='#10b981', fg='white', command=self.start_listening)
        self.btn_listen.pack(side=tk.LEFT, padx=4)
        self.btn_stop_listen = tk.Button(ctrl, text="🛑 Dừng", bg='#ef4444', fg='white', state=tk.DISABLED, command=self.stop_listening)
        self.btn_stop_listen.pack(side=tk.LEFT, padx=4)

        tk.Label(box, text="Văn bản:", fg='white', bg='#0f172a').pack(anchor='w')
        self.txt_text = tk.Text(box, height=3, bg='#0b1220', fg='#cbd5e1', relief=tk.FLAT)
        self.txt_text.pack(fill=tk.X, padx=2, pady=4)

        self.lbl_best = tk.Label(box, text="Nhãn khớp: —", fg='#93c5fd', bg='#0f172a', font=('Arial', 12, 'bold'))
        self.lbl_best.pack(anchor='w', pady=(2,6))

        tk.Label(self.tab_mode, text="Gợi ý: Thu thập đủ dữ liệu để có nhiều sequence thật. Khi nói, hệ thống sẽ phát lại sequence thật của nhãn tương ứng.",
                 fg='#9ca3af', bg='#0f172a', wraplength=520, justify=tk.LEFT).pack(anchor='w', padx=14, pady=4)


    def build_collect_tab(self):
        row = tk.Frame(self.tab_collect, bg='#0f172a')
        row.pack(fill=tk.X, padx=14, pady=(12,6))
        tk.Label(row, text="Nhãn:", fg='white', bg='#0f172a').pack(side=tk.LEFT, padx=(0,6))
        self.ent_label = tk.Entry(row, width=24, bg='#0b1220', fg='white', insertbackground='white', relief=tk.FLAT)
        self.ent_label.pack(side=tk.LEFT)
        self.btn_begin = tk.Button(row, text="🎬 Bắt đầu ghi", bg='#10b981', fg='white', command=self.start_collect)
        self.btn_begin.pack(side=tk.LEFT, padx=6)
        self.btn_end = tk.Button(row, text="⏸ Dừng", bg='#f59e0b', fg='white', command=self.stop_collect, state=tk.DISABLED)
        self.btn_end.pack(side=tk.LEFT, padx=6)
        self.btn_undo = tk.Button(row, text="↩️ Ghi lại (xoá sequence cuối)", bg='#374151', fg='white', command=self.undo_last_seq)
        self.btn_undo.pack(side=tk.LEFT, padx=6)

        stats = tk.Frame(self.tab_collect, bg='#0f172a')
        stats.pack(fill=tk.X, padx=14)
        self.lbl_stat_label = tk.Label(stats, text="Label hiện tại: —", fg='#9ca3af', bg='#0f172a')
        self.lbl_stat_label.pack(side=tk.LEFT, padx=(0,16))
        self.lbl_stat_counts = tk.Label(stats, text="Sequences: 0 | Tổng nhãn: 0 | Tổng seq: 0", fg='#9ca3af', bg='#0f172a')
        self.lbl_stat_counts.pack(side=tk.LEFT)

        tk.Label(self.tab_collect, text="Log:", fg='white', bg='#0f172a').pack(anchor='w', padx=14, pady=(8,4))
        self.log_collect = scrolledtext.ScrolledText(self.tab_collect, height=10, bg='#0b1220', fg='#cbd5e1', relief=tk.FLAT)
        self.log_collect.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0,12))


    def build_train_tab(self):
        lock = tk.Frame(self.tab_train, bg='#0f172a')
        lock.pack(fill=tk.X, padx=14, pady=(12,6))
        self.btn_unlock = tk.Button(lock, text="🔓 Mở khoá", bg='#10b981', fg='white', command=self.unlock)
        self.btn_unlock.pack(side=tk.LEFT, padx=(0,8))
        self.lbl_lock = tk.Label(lock, text="Đang khoá — nhập mật khẩu để dùng train.", fg='#fbbf24', bg='#0f172a')
        self.lbl_lock.pack(side=tk.LEFT)

        row = tk.Frame(self.tab_train, bg='#0f172a'); row.pack(fill=tk.X, padx=14, pady=6)
        self.btn_train = tk.Button(row, text="🚀 Huấn luyện LSTM", bg='#2563eb', fg='white', state=tk.DISABLED, command=self.train_model)
        self.btn_train.pack(side=tk.LEFT, padx=4)
        self.btn_clear = tk.Button(row, text="🗑 Xoá dataset", bg='#ef4444', fg='white', state=tk.DISABLED, command=self.clear_dataset)
        self.btn_clear.pack(side=tk.LEFT, padx=4)

        self.lbl_train_stat = tk.Label(self.tab_train, text="Dataset: —", fg='#9ca3af', bg='#0f172a')
        self.lbl_train_stat.pack(anchor='w', padx=14, pady=6)

        tk.Label(self.tab_train, text="Log:", fg='white', bg='#0f172a').pack(anchor='w', padx=14, pady=(6,4))
        self.log_train = scrolledtext.ScrolledText(self.tab_train, height=12, bg='#0b1220', fg='#cbd5e1', relief=tk.FLAT)
        self.log_train.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0,12))


    def build_recog_tab(self):
        box = tk.Frame(self.tab_recog, bg='#0f172a')
        box.pack(fill=tk.X, padx=14, pady=12)
        self.lbl_pred = tk.Label(box, text="—", font=('Arial', 32, 'bold'), fg='#93c5fd', bg='#0f172a')
        self.lbl_pred.pack(anchor='w')
        self.lbl_conf = tk.Label(box, text="Hãy thực hiện động tác trong khung.", fg='#9ca3af', bg='#0f172a')
        self.lbl_conf.pack(anchor='w', pady=(4,2))
        self.btn_clear_spoken = tk.Button(box, text="🧹 Xoá danh sách đã nói", bg='#374151', fg='white', command=lambda: self.spoken_once.clear())
        self.btn_clear_spoken.pack(anchor='w', pady=6)

        tk.Label(self.tab_recog, text="Log:", fg='white', bg='#0f172a').pack(anchor='w', padx=14, pady=(8,4))
        self.log_recog = scrolledtext.ScrolledText(self.tab_recog, height=10, bg='#0b1220', fg='#cbd5e1', relief=tk.FLAT)
        self.log_recog.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0,12))


    # --------------- Camera loop ---------------
    def start_camera(self):
        if self.is_running:
            return
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            messagebox.showerror("Lỗi", "Không mở được camera.")
            return
        self.is_running = True
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.lbl_status.config(text="🟢 Camera hoạt động", fg='#34d399')
        self.frame_buffer.clear()
        self.raw_roi_buffer.clear()
        self.loop()

    def stop_camera(self):
        self.is_running = False
        if self.cap:
            self.cap.release()
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.lbl_status.config(text="⚪ Camera tắt", fg='#9ca3af')
        self.canvas.delete("all")

    def loop(self):
        if not self.is_running:
            return
        ok, frame = self.cap.read()
        if ok:
            frame = cv2.flip(frame, 1)
            H, W = frame.shape[:2]
            x1, y1, x2, y2 = 100, 100, min(620, W-10), min(420, H-10)
            cv2.rectangle(frame, (x1,y1), (x2,y2), (0,255,0), 2)
            cv2.putText(frame, "ROI", (x1+4, y1-8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
            roi = frame[y1:y2, x1:x2]

            # skin
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, self.lower_skin, self.upper_skin)
            kernel = np.ones((3,3), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, 2)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, 2)
            mask = cv2.GaussianBlur(mask, (5,5), 100)

            # features + raw buffer
            features = cv2.resize(mask, (28,28)).flatten()/255.0
            self.frame_buffer.append(features)

            roi_rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
            pil = Image.fromarray(roi_rgb).resize((int((x2-x1)), int((y2-y1))), Image.BILINEAR)
            self.raw_roi_buffer.append(pil)

            # triggers
            if self.is_collecting and len(self.frame_buffer) == self.SEQ_LEN:
                self.collect_sequence()   # save features + frames
            elif self.nb.index('current') == 3 and self.model is not None and len(self.frame_buffer) == self.SEQ_LEN:
                if self.mode.get() == "gesture_to_speech":
                    self.recognize_current()

            # compose base image
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb).resize((800, 500), Image.BILINEAR)

            # Speech→Gesture playback
            if self.mode.get() == "speech_to_gesture" and self.playback_running and self.playback_frames:
                scale_x = 800 / W
                scale_y = 500 / H
                X1 = int(x1 * scale_x)
                Y1 = int(y1 * scale_y)
                X2 = int(x2 * scale_x)
                Y2 = int(y2 * scale_y)
                w = X2 - X1; h = Y2 - Y1
                frame_to_paste = self.playback_frames[self.playback_idx % len(self.playback_frames)].resize((w,h), Image.BILINEAR)
                img.paste(frame_to_paste, (X1, Y1))
                self.playback_idx = (self.playback_idx + 1) % max(1, len(self.playback_frames))

            imgtk = ImageTk.PhotoImage(img)
            self.canvas.create_image(0,0, anchor=tk.NW, image=imgtk)
            self.canvas.imgtk = imgtk

            self.lbl_buffer.config(text=f"Buffer {len(self.frame_buffer)}/{self.SEQ_LEN}")

        self.root.after(10, self.loop)


    # --------------- Collect ---------------
    def start_collect(self):
        label = self.ent_label.get().strip()
        if not label:
            messagebox.showwarning("Thiếu nhãn", "Nhập nhãn trước khi ghi.")
            return
        if not self.is_running:
            messagebox.showwarning("Camera", "Hãy bật camera trước.")
            return
        self.current_label = label
        self.is_collecting = True
        self.frame_buffer.clear()
        self.raw_roi_buffer.clear()
        if label not in self.dataset:
            self.dataset[label] = []
        if label not in self.labels_order:
            self.labels_order.append(label)
        if label not in self.frames_index:
            self.frames_index[label] = []

        self.btn_begin.config(state=tk.DISABLED)
        self.btn_end.config(state=tk.NORMAL)
        self.lbl_stat_label.config(text=f"Label hiện tại: {label}")
        self.log_collect.insert(tk.END, f"[{self.now()}] Bắt đầu ghi: {label}\n")
        self.log_collect.see(tk.END)

    def stop_collect(self):
        self.is_collecting = False
        self.btn_begin.config(state=tk.NORMAL)
        self.btn_end.config(state=tk.DISABLED)
        self.save_dataset()
        self.save_frames_index()
        self.update_stats()
        self.log_collect.insert(tk.END, f"[{self.now()}] Dừng ghi\n")
        self.log_collect.see(tk.END)

    def collect_sequence(self):
        # Save features
        seq = np.array(list(self.frame_buffer))
        self.dataset[self.current_label].append(seq)

        # Save frames to disk
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        seq_dir = self.frames_root / self.current_label / ts
        seq_dir.mkdir(parents=True, exist_ok=True)
        for i, pil in enumerate(list(self.raw_roi_buffer)):
            pil.save(seq_dir / f"{i:02d}.jpg", quality=85)

        self.frames_index[self.current_label].append(str(seq_dir.relative_to(self.frames_root)))

        n_label = len(self.dataset[self.current_label])
        self.log_collect.insert(tk.END, f"[{self.now()}] ✔ Ghi sequence #{n_label} ({self.current_label})\n")
        self.log_collect.see(tk.END)

        self.frame_buffer.clear()
        self.raw_roi_buffer.clear()
        self.update_stats()

    def undo_last_seq(self):
        label = self.current_label or self.ent_label.get().strip()
        if not label or label not in self.dataset or len(self.dataset[label]) == 0:
            messagebox.showinfo("Thông báo", "Không có sequence nào để xoá.")
            return
        # remove last features
        self.dataset[label].pop()
        # remove last frames on disk
        if label in self.frames_index and self.frames_index[label]:
            last_rel = self.frames_index[label].pop()
            seq_dir = self.frames_root / last_rel
            try:
                for p in sorted(seq_dir.glob("*")):
                    p.unlink()
                seq_dir.rmdir()
            except Exception:
                pass
        self.save_dataset()
        self.save_frames_index()
        self.update_stats()
        self.log_collect.insert(tk.END, f"[{self.now()}] ↩️ Đã xoá sequence cuối của '{label}'\n")
        self.log_collect.see(tk.END)


    # --------------- Train ---------------
    def unlock(self):
        pwd = simpledialog.askstring("Mật khẩu", "Nhập mật khẩu huấn luyện:", show='*')
        if pwd == self.TRAIN_PASSWORD:
            self.train_locked = False
            self.btn_train.config(state=tk.NORMAL)
            self.btn_clear.config(state=tk.NORMAL)
            self.lbl_lock.config(text="ĐÃ MỞ KHOÁ — có thể train/xoá dataset.", fg='#34d399')
            self.nb.tab(2, text="🧠 Huấn luyện")
        else:
            messagebox.showerror("Sai mật khẩu", "Không đúng.")

    def train_model(self):
        if self.train_locked:
            return
        labels = [lb for lb in self.labels_order if lb in self.dataset and len(self.dataset[lb])>0]
        if len(labels) < 2:
            messagebox.showwarning("Thiếu dữ liệu", "Cần >= 2 nhãn, mỗi nhãn >= 1 sequence.")
            return
        self.log_train.insert(tk.END, f"[{self.now()}] Bắt đầu train...\n")
        self.log_train.see(tk.END)
        threading.Thread(target=self._train_thread, daemon=True).start()

    def _train_thread(self):
        try:
            labels = [lb for lb in self.labels_order if lb in self.dataset and len(self.dataset[lb])>0]
            xs, ys = [], []
            for idx, lb in enumerate(labels):
                for seq in self.dataset[lb]:
                    xs.append(seq)
                    one = np.zeros(len(labels)); one[idx]=1
                    ys.append(one)
            xs = np.array(xs); ys = np.array(ys)

            self.model = keras.Sequential([
                keras.layers.LSTM(64, return_sequences=True, input_shape=(self.SEQ_LEN, 784)),
                keras.layers.Dropout(0.3),
                keras.layers.LSTM(32),
                keras.layers.Dropout(0.2),
                keras.layers.Dense(32, activation='relu'),
                keras.layers.Dense(len(labels), activation='softmax')
            ])
            self.model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

            hist = self.model.fit(xs, ys, epochs=40, batch_size=16, validation_split=0.2, verbose=0)
            acc = float(hist.history['val_accuracy'][-1])
            self.log_train.insert(tk.END, f"[{self.now()}] ✅ Train xong. Val acc: {acc*100:.1f}%  | Samples: {len(xs)}  | Classes: {len(labels)}\n")
            self.log_train.see(tk.END)
        except Exception as e:
            self.log_train.insert(tk.END, f"[{self.now()}] ❌ Lỗi train: {e}\n")
            self.log_train.see(tk.END)

    def clear_dataset(self):
        if not messagebox.askyesno("Xác nhận", "Xoá tất cả dữ liệu & khung hình đã lưu?"):
            return
        self.dataset = {}
        self.labels_order = []
        self.model = None
        try:
            if self.frames_root.exists():
                for p in self.frames_root.rglob("*"):
                    if p.is_file(): p.unlink()
                for p in sorted(self.frames_root.glob("*"), reverse=True):
                    if p.is_dir():
                        try: p.rmdir()
                        except Exception: pass
        except Exception:
            pass
        self.frames_index = {}
        self.save_dataset()
        self.save_frames_index()
        self.update_stats()
        self.log_train.insert(tk.END, f"[{self.now()}] Đã xoá sạch dataset.\n")


    # --------------- Recognition (gesture -> speech) ---------------
    def recognize_current(self):
        if self.model is None:
            return
        seq = np.array(list(self.frame_buffer)).reshape(1, self.SEQ_LEN, 784)
        probs = self.model.predict(seq, verbose=0)[0]
        idx = int(np.argmax(probs))
        conf = float(probs[idx])
        labels = [lb for lb in self.labels_order if lb in self.dataset and len(self.dataset[lb])>0]
        label = labels[idx] if idx < len(labels) else "—"

        if conf > 0.6:
            self.lbl_pred.config(text=label)
            self.lbl_conf.config(text=f"Độ tin cậy: {conf*100:.1f}%")
            self.log_recog.insert(tk.END, f"[{self.now()}] ✔ {label} ({conf*100:.1f}%)\n")
            self.log_recog.see(tk.END)
            if self.tts and label not in self.spoken_once:
                try:
                    self.spoken_once.add(label)
                    self.tts.say(label)
                    self.tts.runAndWait()
                except Exception:
                    pass
        else:
            self.lbl_pred.config(text="❓")
            self.lbl_conf.config(text="Không chắc chắn")


    # --------------- Speech -> Gesture (play recorded frames) ---------------
    def start_listening(self):
        if not sr or not self.recognizer:
            messagebox.showerror("Thiếu thư viện", "speech_recognition chưa sẵn sàng.")
            return
        try:
            self.mic = sr.Microphone()
        except Exception as e:
            messagebox.showerror("Mic", str(e)); return
        self.stt_is_listening = True
        self.btn_listen.config(state=tk.DISABLED)
        self.btn_stop_listen.config(state=tk.NORMAL)
        self.lbl_stt.config(text="🎙️ Đang nghe...", fg='#34d399')
        threading.Thread(target=self._listen_loop, daemon=True).start()

    def stop_listening(self):
        self.stt_is_listening = False
        self.btn_listen.config(state=tk.NORMAL)
        self.btn_stop_listen.config(state=tk.DISABLED)
        self.lbl_stt.config(text="Mic: sẵn sàng", fg='#9ca3af')

    def _listen_loop(self):
        with self.mic as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.6)
        while self.stt_is_listening:
            try:
                with self.mic as source:
                    audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=5)
                try:
                    text = self.recognizer.recognize_google(audio, language='vi-VN')
                except Exception:
                    text = ""
                if text:
                    self.root.after(0, lambda t=text: self.on_text(t))
            except Exception:
                continue

    def on_text(self, text):
        self.txt_text.delete('1.0', tk.END)
        self.txt_text.insert(tk.END, text)
        best, score = self.best_label(text)
        self.lbl_best.config(text=f"Nhãn khớp: {best or '—'} ({int(score*100)}%)")
        if best:
            self.play_label(best)

    def best_label(self, text):
        labels = [lb for lb in self.labels_order if lb in self.dataset and len(self.dataset[lb])>0]
        if not labels: return None, 0.0
        t = text.strip().lower()
        lst = [s.lower() for s in labels]
        m = difflib.get_close_matches(t, lst, n=1, cutoff=0.4)
        if not m:
            scores = [(lab, difflib.SequenceMatcher(None, t, lab).ratio()) for lab in lst]
            best = max(scores, key=lambda x: x[1])
            idx = lst.index(best[0])
            return labels[idx], float(best[1])
        else:
            idx = lst.index(m[0])
            return labels[idx], 1.0

    def play_label(self, label):
        seq_dirs = self.frames_index.get(label, [])
        if not seq_dirs:
            messagebox.showinfo("Thiếu dữ liệu", f"Chưa có frame nào cho nhãn '{label}'. Hãy thu thập trước.")
            return
        seq_rel = seq_dirs[-1]
        seq_dir = self.frames_root / seq_rel
        frames = sorted(seq_dir.glob("*.jpg"))
        if not frames:
            messagebox.showinfo("Thiếu dữ liệu", f"Sequence {seq_rel} rỗng.")
            return
        self.playback_frames = [Image.open(p) for p in frames]
        self.playback_idx = 0
        self.playback_label = label
        self.playback_running = True


    # --------------- Persist ---------------
    def save_dataset(self):
        with open(self.dataset_pkl, 'wb') as f:
            pickle.dump({'dataset': self.dataset, 'labels_order': self.labels_order}, f)

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
            except Exception:
                self.dataset = {}
                self.labels_order = []

    def save_frames_index(self):
        with open(self.frames_index_path, 'w', encoding='utf-8') as f:
            json.dump(self.frames_index, f, ensure_ascii=False, indent=2)

    def load_frames_index(self):
        if self.frames_index_path.exists():
            try:
                self.frames_index = json.load(open(self.frames_index_path, 'r', encoding='utf-8'))
            except Exception:
                self.frames_index = {}


    # --------------- Utils ---------------
    def set_mode(self, m):
        self.mode.set(m)
        if m == "speech_to_gesture":
            self.lbl_status.config(text="🧭 Chế độ: Giọng nói → Cử chỉ", fg='#93c5fd')
        else:
            self.lbl_status.config(text="🧭 Chế độ: Cử chỉ → Giọng nói", fg='#93c5fd')

    def update_stats(self):
        tot_labels = len([lb for lb in self.dataset if len(self.dataset[lb])>0])
        tot_seq = sum(len(v) for v in self.dataset.values())
        cur = len(self.dataset.get(self.current_label, [])) if self.current_label else 0
        self.lbl_stat_counts.config(text=f"Sequences: {cur} | Tổng nhãn: {tot_labels} | Tổng seq: {tot_seq}")
        self.lbl_train_stat.config(text=f"Dataset: {tot_labels} nhãn, {tot_seq} sequences")

    def now(self):
        return datetime.now().strftime("%H:%M:%S")


if __name__ == "__main__":
    root = tk.Tk()
    app = DynamicSignV3(root)
    root.mainloop()
