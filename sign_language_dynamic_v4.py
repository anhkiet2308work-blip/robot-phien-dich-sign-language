
"""
Ký hiệu ĐỘNG v4 — Landing (mắt chớp), UI to hơn, Speech→Gesture không dùng camera,
quản lý dữ liệu (xoá sequence vừa ghi / xoá nhãn).
"""


import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext
import cv2
import numpy as np
import pickle, json, os, time, random
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
    tf.get_logger().setLevel('ERROR')
except Exception:
    pass

try:
    import speech_recognition as sr
except Exception:
    sr = None

try:
    import pyttsx3
except Exception:
    pyttsx3 = None


class AppV4:
    SEQ_LEN = 30
    def __init__(self, root):
        self.root = root
        self.root.title("Ký hiệu ĐỘNG v4 — GIỌNG NÓI ↔ CỬ CHỈ (VN)")
        self.root.geometry("1320x860")
        self.root.minsize(1120, 760)

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
        self.frames_root = Path("frames"); self.frames_root.mkdir(exist_ok=True)
        self.frames_index_path = Path("frames_index.json")
        self.frames_index = {}

        self.lower_skin = np.array([0, 20, 70], dtype=np.uint8)
        self.upper_skin = np.array([20, 255, 255], dtype=np.uint8)

        self.mode = tk.StringVar(value="gesture_to_speech")
        self.train_locked = True
        self.TRAIN_PASSWORD = "1234"

        self.recognizer = sr.Recognizer() if sr else None
        self.stt_is_listening = False

        self.tts = None
        if pyttsx3:
            try:
                self.tts = pyttsx3.init()
                self.tts.setProperty('rate', 175)
                self.tts.setProperty('volume', 1.0)
            except Exception:
                self.tts = None
        self.spoken_once = set()

        self.playback_frames = []
        self.playback_idx = 0
        self.playback_running = False
        self.playback_label = None

        self.on_home = True
        self.eye_state = {"blink": False, "gaze": (0,0), "expr": "happy"}
        self.next_blink_t = time.time() + random.uniform(1.2, 3.0)
        self.next_gaze_t  = time.time() + random.uniform(0.8, 1.6)
        self.next_expr_t  = time.time() + random.uniform(3, 6)

        self.load_dataset(); self.load_frames_index()
        self.build_ui()
        self.start_idle_loop()


    def build_ui(self):
        style = ttk.Style(); style.theme_use('clam')
        style.configure('TNotebook.Tab', padding=[18, 10])

        self.topbar = tk.Frame(self.root, bg='#0b1220'); self.topbar.pack(fill=tk.X)
        self.btn_home = tk.Button(self.topbar, text="🏠 Home", font=('Arial', 14, 'bold'),
                                  bg='#374151', fg='white', relief=tk.FLAT, padx=18, pady=8,
                                  command=self.go_home)
        self.btn_home.pack(side=tk.LEFT, padx=8, pady=8)
        self.btn_start_app = tk.Button(self.topbar, text="🚀 BẮT ĐẦU", font=('Arial', 16, 'bold'),
                                       bg='#10b981', fg='white', relief=tk.FLAT, padx=22, pady=10,
                                       command=self.leave_home)
        self.btn_start_app.pack(side=tk.RIGHT, padx=8, pady=8)

        self.container = tk.Frame(self.root, bg='#0b1220'); self.container.pack(fill=tk.BOTH, expand=True)
        self.left = tk.Frame(self.container, bg='#0b1220')
        self.left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(12,6), pady=(6,12))
        tk.Label(self.left, text="Màn hình hiển thị", fg='white', bg='#0b1220',
                 font=('Arial', 16, 'bold')).pack(anchor='w', pady=(0,6))
        self.canvas = tk.Canvas(self.left, width=860, height=540, bg='black', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        ctrl = tk.Frame(self.left, bg='#0b1220'); ctrl.pack(fill=tk.X, pady=10)
        self.btn_cam_on  = tk.Button(ctrl, text="📷 Bật Camera", font=('Arial', 13, 'bold'),
                                     bg='#2563eb', fg='white', relief=tk.FLAT, padx=18, pady=10,
                                     command=self.start_camera)
        self.btn_cam_on.pack(side=tk.LEFT, padx=6)
        self.btn_cam_off = tk.Button(ctrl, text="⏹ Tắt Camera", font=('Arial', 13, 'bold'),
                                     bg='#ef4444', fg='white', relief=tk.FLAT, padx=18, pady=10,
                                     command=self.stop_camera, state=tk.DISABLED)
        self.btn_cam_off.pack(side=tk.LEFT, padx=6)
        self.lbl_status = tk.Label(ctrl, text="⚪ Home", fg='#9ca3af', bg='#0b1220', font=('Arial', 12))
        self.lbl_status.pack(side=tk.LEFT, padx=14)
        self.lbl_buffer = tk.Label(ctrl, text="Buffer 0/30", fg='#f59e0b', bg='#0b1220', font=('Arial', 12))
        self.lbl_buffer.pack(side=tk.LEFT, padx=10)

        self.right = tk.Frame(self.container, bg='#0b1220')
        self.right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(6,12), pady=(6,12))
        self.nb = ttk.Notebook(self.right); self.nb.pack(fill=tk.BOTH, expand=True)

        self.tab_mode = tk.Frame(self.nb, bg='#0f172a'); self.nb.add(self.tab_mode, text="🧭 Chế độ")
        self.tab_collect = tk.Frame(self.nb, bg='#0f172a'); self.nb.add(self.tab_collect, text="📚 Thu thập")
        self.tab_train = tk.Frame(self.nb, bg='#0f172a'); self.nb.add(self.tab_train, text="🧠 Huấn luyện (🔒)")
        self.tab_recog = tk.Frame(self.nb, bg='#0f172a'); self.nb.add(self.tab_recog, text="🎯 Nhận diện")

        self.build_mode_tab(); self.build_collect_tab(); self.build_train_tab(); self.build_recog_tab()


    def build_mode_tab(self):
        row = tk.Frame(self.tab_mode, bg='#0f172a'); row.pack(padx=16, pady=16, anchor='w')
        tk.Button(row, text="🎙️ Giọng nói → Cử chỉ", bg='#10b981', fg='white',
                  font=('Arial', 14, 'bold'), padx=18, pady=10,
                  command=lambda: self.set_mode("speech_to_gesture")).pack(side=tk.LEFT, padx=8)
        tk.Button(row, text="✋ Cử chỉ → Giọng nói", bg='#2563eb', fg='white',
                  font=('Arial', 14, 'bold'), padx=18, pady=10,
                  command=lambda: self.set_mode("gesture_to_speech")).pack(side=tk.LEFT, padx=8)

        box = tk.LabelFrame(self.tab_mode, text="🎙️ Giọng nói → Cử chỉ", bg='#0f172a', fg='white', font=('Arial', 12, 'bold'))
        box.pack(fill=tk.X, padx=16, pady=10)

        self.lbl_stt = tk.Label(box, text="Mic: sẵn sàng", fg='#9ca3af', bg='#0f172a', font=('Arial', 11))
        self.lbl_stt.pack(anchor='w', pady=(4,2))

        ctrl = tk.Frame(box, bg='#0f172a'); ctrl.pack(anchor='w', pady=4)
        self.btn_listen = tk.Button(ctrl, text="🎧 BẮT ĐẦU NGHE", bg='#10b981', fg='white',
                                    font=('Arial', 13, 'bold'), padx=16, pady=8, command=self.start_listening)
        self.btn_listen.pack(side=tk.LEFT, padx=6)
        self.btn_stop_listen = tk.Button(ctrl, text="🛑 DỪNG", bg='#ef4444', fg='white',
                                         font=('Arial', 13, 'bold'), padx=16, pady=8, command=self.stop_listening, state=tk.DISABLED)
        self.btn_stop_listen.pack(side=tk.LEFT, padx=6)

        tk.Label(box, text="Văn bản:", fg='white', bg='#0f172a', font=('Arial', 11, 'bold')).pack(anchor='w')
        self.txt_text = tk.Text(box, height=3, bg='#0b1220', fg='#cbd5e1', relief=tk.FLAT, font=('Courier New', 11))
        self.txt_text.pack(fill=tk.X, padx=2, pady=6)

        self.lbl_best = tk.Label(box, text="Nhãn khớp: —", fg='#93c5fd', bg='#0f172a', font=('Arial', 13, 'bold'))
        self.lbl_best.pack(anchor='w', pady=(2,6))

        tk.Label(self.tab_mode, text="Gợi ý: Ở chế độ này **camera sẽ TẮT**. Hệ thống sẽ phát lại sequence thật của nhãn tương ứng trong khung bên trái.",
                 fg='#9ca3af', bg='#0f172a', wraplength=560, justify=tk.LEFT, font=('Arial', 10)).pack(anchor='w', padx=16, pady=6)


    def build_collect_tab(self):
        row = tk.Frame(self.tab_collect, bg='#0f172a'); row.pack(fill=tk.X, padx=16, pady=(12,6))
        tk.Label(row, text="Nhãn:", fg='white', bg='#0f172a', font=('Arial', 12)).pack(side=tk.LEFT, padx=(0,8))
        self.ent_label = tk.Entry(row, width=24, bg='#0b1220', fg='white', insertbackground='white', relief=tk.FLAT, font=('Arial', 12))
        self.ent_label.pack(side=tk.LEFT)
        self.btn_begin = tk.Button(row, text="🎬 BẮT ĐẦU GHI", bg='#10b981', fg='white', font=('Arial', 13, 'bold'), padx=16, pady=8, command=self.start_collect)
        self.btn_begin.pack(side=tk.LEFT, padx=8)
        self.btn_end = tk.Button(row, text="⏸ DỪNG", bg='#f59e0b', fg='white', font=('Arial', 13, 'bold'), padx=16, pady=8, command=self.stop_collect, state=tk.DISABLED)
        self.btn_end.pack(side=tk.LEFT, padx=8)
        self.btn_undo = tk.Button(row, text="↩️ XOÁ SEQ CUỐI", bg='#374151', fg='white', font=('Arial', 12, 'bold'), padx=12, pady=8, command=self.undo_last_seq)
        self.btn_undo.pack(side=tk.LEFT, padx=8)

        manage = tk.LabelFrame(self.tab_collect, text="Quản lý dữ liệu", bg='#0f172a', fg='white', font=('Arial', 12, 'bold'))
        manage.pack(fill=tk.X, padx=16, pady=8)
        mrow = tk.Frame(manage, bg='#0f172a'); mrow.pack(fill=tk.X, pady=6)
        tk.Label(mrow, text="Xoá N sequence cuối của nhãn:", fg='white', bg='#0f172a').pack(side=tk.LEFT, padx=(0,8))
        self.ent_delete_n = tk.Entry(mrow, width=6, bg='#0b1220', fg='white', insertbackground='white', relief=tk.FLAT); self.ent_delete_n.insert(0,"3")
        self.ent_delete_n.pack(side=tk.LEFT)
        tk.Button(mrow, text="🗑 XOÁ N SEQ", bg='#ef4444', fg='white', padx=12, pady=6, command=self.delete_last_n_sequences).pack(side=tk.LEFT, padx=8)
        mrow2 = tk.Frame(manage, bg='#0f172a'); mrow2.pack(fill=tk.X, pady=6)
        tk.Label(mrow2, text="Xoá toàn bộ nhãn (features + frames):", fg='white', bg='#0f172a').pack(side=tk.LEFT, padx=(0,8))
        self.ent_label_delete = tk.Entry(mrow2, width=24, bg='#0b1220', fg='white', insertbackground='white', relief=tk.FLAT)
        self.ent_label_delete.pack(side=tk.LEFT)
        tk.Button(mrow2, text="☠ XOÁ NHÃN", bg='#991b1b', fg='white', padx=12, pady=6, command=self.delete_label_all).pack(side=tk.LEFT, padx=8)

        stats = tk.Frame(self.tab_collect, bg='#0f172a'); stats.pack(fill=tk.X, padx=16)
        self.lbl_stat_label = tk.Label(stats, text="Label hiện tại: —", fg='#9ca3af', bg='#0f172a', font=('Arial', 11))
        self.lbl_stat_label.pack(side=tk.LEFT, padx=(0,16))
        self.lbl_stat_counts = tk.Label(stats, text="Sequences: 0 | Tổng nhãn: 0 | Tổng seq: 0", fg='#9ca3af', bg='#0f172a', font=('Arial', 11))
        self.lbl_stat_counts.pack(side=tk.LEFT)

        tk.Label(self.tab_collect, text="Log:", fg='white', bg='#0f172a', font=('Arial', 12, 'bold')).pack(anchor='w', padx=16, pady=(8,4))
        self.log_collect = scrolledtext.ScrolledText(self.tab_collect, height=10, bg='#0b1220', fg='#cbd5e1', relief=tk.FLAT, font=('Courier New', 10))
        self.log_collect.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0,12))


    def build_train_tab(self):
        lock = tk.Frame(self.tab_train, bg='#0f172a'); lock.pack(fill=tk.X, padx=16, pady=(12,6))
        self.btn_unlock = tk.Button(lock, text="🔓 MỞ KHOÁ", bg='#10b981', fg='white', font=('Arial', 13, 'bold'), padx=16, pady=8, command=self.unlock)
        self.btn_unlock.pack(side=tk.LEFT, padx=(0,10))
        self.lbl_lock = tk.Label(lock, text="Đang khoá — nhập mật khẩu để train.", fg='#fbbf24', bg='#0f172a', font=('Arial', 11))
        self.lbl_lock.pack(side=tk.LEFT)

        row = tk.Frame(self.tab_train, bg='#0f172a'); row.pack(fill=tk.X, padx=16, pady=8)
        self.btn_train = tk.Button(row, text="🚀 HUẤN LUYỆN LSTM", bg='#2563eb', fg='white', font=('Arial', 14, 'bold'), padx=18, pady=10, command=self.train_model, state=tk.DISABLED)
        self.btn_train.pack(side=tk.LEFT, padx=8)
        self.btn_clear = tk.Button(row, text="🗑 XOÁ DATASET", bg='#ef4444', fg='white', font=('Arial', 14, 'bold'), padx=18, pady=10, command=self.clear_dataset, state=tk.DISABLED)
        self.btn_clear.pack(side=tk.LEFT, padx=8)

        self.lbl_train_stat = tk.Label(self.tab_train, text="Dataset: —", fg='#9ca3af', bg='#0f172a', font=('Arial', 11))
        self.lbl_train_stat.pack(anchor='w', padx=16, pady=6)

        tk.Label(self.tab_train, text="Log:", fg='white', bg='#0f172a', font=('Arial', 12, 'bold')).pack(anchor='w', padx=16, pady=(6,4))
        self.log_train = scrolledtext.ScrolledText(self.tab_train, height=12, bg='#0b1220', fg='#cbd5e1', relief=tk.FLAT, font=('Courier New', 10))
        self.log_train.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0,12))


    def build_recog_tab(self):
        box = tk.Frame(self.tab_recog, bg='#0f172a'); box.pack(fill=tk.X, padx=16, pady=12)
        self.lbl_pred = tk.Label(box, text="—", font=('Arial', 36, 'bold'), fg='#93c5fd', bg='#0f172a')
        self.lbl_pred.pack(anchor='w')
        self.lbl_conf = tk.Label(box, text="Hãy thực hiện động tác trong khung.", fg='#9ca3af', bg='#0f172a', font=('Arial', 12))
        self.lbl_conf.pack(anchor='w', pady=(4,2))
        self.btn_clear_spoken = tk.Button(box, text="🧹 Xoá danh sách đã nói", bg='#374151', fg='white', font=('Arial', 12, 'bold'), padx=12, pady=8, command=lambda: self.spoken_once.clear())
        self.btn_clear_spoken.pack(anchor='w', pady=6)

        tk.Label(self.tab_recog, text="Log:", fg='white', bg='#0f172a', font=('Arial', 12, 'bold')).pack(anchor='w', padx=16, pady=(8,4))
        self.log_recog = scrolledtext.ScrolledText(self.tab_recog, height=10, bg='#0b1220', fg='#cbd5e1', relief=tk.FLAT, font=('Courier New', 10))
        self.log_recog.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0,12))


    # ---- Home / idle eyes ----
    def go_home(self):
        self.stop_listening(); self.stop_camera()
        self.on_home = True
        self.lbl_status.config(text="⚪ Home")
        self.canvas.delete("all")

    def leave_home(self):
        self.on_home = False
        self.lbl_status.config(text="🧭 Hãy chọn chế độ ở tab 'Chế độ'")

    def start_idle_loop(self):
        def tick():
            if self.on_home:
                self.draw_eyes()
            self.root.after(60, tick)
        tick()

    def draw_eyes(self):
        W = self.canvas.winfo_width() or 860
        H = self.canvas.winfo_height() or 540
        img = Image.new("RGB", (W,H), "#0b1220")
        draw = ImageDraw.Draw(img)
        t = time.time()
        if t >= self.next_blink_t:
            self.eye_state["blink"] = not self.eye_state["blink"]
            self.next_blink_t = t + (0.15 if self.eye_state["blink"] else random.uniform(1.2, 3.0))
        if t >= self.next_gaze_t:
            self.eye_state["gaze"] = (random.uniform(-1,1), random.uniform(-1,1))
            self.next_gaze_t = t + random.uniform(0.8, 1.6)
        if t >= self.next_expr_t:
            self.eye_state["expr"] = random.choice(["happy","curious","angry","excited"])
            self.next_expr_t = t + random.uniform(3, 6)

        cx1, cy = int(W*0.38), int(H*0.45)
        cx2 = int(W*0.62)
        rx, ry = int(W*0.11), int(H*0.16)
        lid = 0.0 if not self.eye_state["blink"] else 0.85

        sclera = (245,246,248)
        draw.ellipse((cx1-rx, cy-ry*(1-lid), cx1+rx, cy+ry*(1-lid)), fill=sclera)
        draw.ellipse((cx2-rx, cy-ry*(1-lid), cx2+rx, cy+ry*(1-lid)), fill=sclera)

        gx, gy = self.eye_state["gaze"]
        iris_r = int(min(rx,ry)*0.45)
        offx = int(gx*rx*0.35); offy = int(gy*ry*0.35)
        iris_color = {"happy":(90,180,255), "curious":(90,255,160), "angry":(255,90,90), "excited":(255,200,90)}.get(self.eye_state["expr"], (90,180,255))
        for cx in (cx1, cx2):
            draw.ellipse((cx-iris_r+offx, cy-iris_r+offy, cx+iris_r+offx, cy+iris_r+offy), fill=iris_color)
            pr = int(iris_r*0.45)
            draw.ellipse((cx-pr+offx, cy-pr+offy, cx+pr+offx, cy+pr+offy), fill=(20,20,30))

        mx, my = int(W*0.5), int(H*0.68)
        if self.eye_state["expr"] == "angry":
            draw.arc((mx-120,my-30,mx+120,my+60), start=200, end=340, fill=(255,90,90), width=6)
        elif self.eye_state["expr"] == "curious":
            draw.arc((mx-120,my-60,mx+120,my+30), start=20, end=160, fill=(90,255,160), width=6)
        elif self.eye_state["expr"] == "excited":
            draw.arc((mx-140,my-40,mx+140,my+40), start=20, end=160, fill=(255,200,90), width=8)
        else:
            draw.arc((mx-120,my-20,mx+120,my+60), start=20, end=160, fill=(90,180,255), width=6)

        draw.text((int(W*0.5-190), int(H*0.12)), "Nhấn 🚀 BẮT ĐẦU để vào giao diện chính", fill=(200,230,255))
        imgtk = ImageTk.PhotoImage(img)
        self.canvas.create_image(0,0, anchor=tk.NW, image=imgtk)
        self.canvas.imgtk = imgtk


    # ---- Camera (gesture→speech & collect only) ----
    def start_camera(self):
        if self.mode.get() == "speech_to_gesture":
            messagebox.showinfo("Chú ý", "Chế độ Giọng nói → Cử chỉ không dùng camera.")
            return
        if self.is_running: return
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            messagebox.showerror("Lỗi", "Không mở được camera."); return
        self.is_running = True
        self.btn_cam_on.config(state=tk.DISABLED); self.btn_cam_off.config(state=tk.NORMAL)
        self.lbl_status.config(text="🟢 Camera hoạt động", fg='#34d399')
        self.frame_buffer.clear(); self.raw_roi_buffer.clear()
        self.loop()

    def stop_camera(self):
        self.is_running = False
        if self.cap: self.cap.release()
        self.btn_cam_on.config(state=tk.NORMAL); self.btn_cam_off.config(state=tk.DISABLED)
        self.lbl_status.config(text=("⚪ Home" if self.on_home else "⚪ Camera tắt"), fg='#9ca3af')
        self.canvas.delete("all")


    def loop(self):
        if not self.is_running: return
        ok, frame = self.cap.read()
        if ok:
            frame = cv2.flip(frame, 1)
            H, W = frame.shape[:2]
            x1, y1, x2, y2 = 100, 100, min(620, W-10), min(420, H-10)
            cv2.rectangle(frame, (x1,y1), (x2,y2), (0,255,0), 2)
            cv2.putText(frame, "ROI", (x1+4, y1-8), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
            roi = frame[y1:y2, x1:x2]

            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, self.lower_skin, self.upper_skin)
            kernel = np.ones((3,3), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, 2)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, 2)
            mask = cv2.GaussianBlur(mask, (5,5), 100)

            features = cv2.resize(mask, (28,28)).flatten()/255.0
            self.frame_buffer.append(features)

            roi_rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
            pil = Image.fromarray(roi_rgb).resize((int((x2-x1)), int((y2-y1))), Image.BILINEAR)
            self.raw_roi_buffer.append(pil)

            if self.is_collecting and len(self.frame_buffer) == self.SEQ_LEN:
                self.collect_sequence()
            elif self.nb.index('current') == 3 and self.model is not None and len(self.frame_buffer) == self.SEQ_LEN:
                if self.mode.get() == "gesture_to_speech":
                    self.recognize_current()

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb).resize((860,540), Image.BILINEAR)
            imgtk = ImageTk.PhotoImage(img)
            self.canvas.create_image(0,0, anchor=tk.NW, image=imgtk); self.canvas.imgtk = imgtk
            self.lbl_buffer.config(text=f"Buffer {len(self.frame_buffer)}/{self.SEQ_LEN}")
        self.root.after(10, self.loop)


    # ---- Collect ----
    def start_collect(self):
        label = self.ent_label.get().strip()
        if not label:
            messagebox.showwarning("Thiếu nhãn", "Nhập nhãn trước khi ghi."); return
        if not self.is_running:
            messagebox.showwarning("Camera", "Hãy bật camera trước."); return
        self.current_label = label; self.is_collecting = True
        self.frame_buffer.clear(); self.raw_roi_buffer.clear()
        if label not in self.dataset: self.dataset[label] = []
        if label not in self.labels_order: self.labels_order.append(label)
        if label not in self.frames_index: self.frames_index[label] = []
        self.btn_begin.config(state=tk.DISABLED); self.btn_end.config(state=tk.NORMAL)
        self.lbl_stat_label.config(text=f"Label hiện tại: {label}")
        self._log(self.log_collect, f"Bắt đầu ghi: {label}")

    def stop_collect(self):
        self.is_collecting = False
        self.btn_begin.config(state=tk.NORMAL); self.btn_end.config(state=tk.DISABLED)
        self.save_dataset(); self.save_frames_index(); self.update_stats()
        self._log(self.log_collect, "Dừng ghi.")

    def collect_sequence(self):
        seq = np.array(list(self.frame_buffer))
        self.dataset[self.current_label].append(seq)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        seq_dir = self.frames_root / self.current_label / ts
        seq_dir.mkdir(parents=True, exist_ok=True)
        for i, pil in enumerate(list(self.raw_roi_buffer)):
            pil.save(seq_dir / f"{i:02d}.jpg", quality=85)
        self.frames_index[self.current_label].append(str(seq_dir.relative_to(self.frames_root)))
        n_label = len(self.dataset[self.current_label])
        self._log(self.log_collect, f"✔ Ghi sequence #{n_label} ({self.current_label})")
        self.frame_buffer.clear(); self.raw_roi_buffer.clear()
        self.update_stats()

    def undo_last_seq(self):
        label = self.current_label or self.ent_label.get().strip()
        if not label or label not in self.dataset or len(self.dataset[label]) == 0:
            messagebox.showinfo("Thông báo", "Không có sequence nào để xoá."); return
        self._delete_last_sequences(label, 1)
        self._log(self.log_collect, f"↩️ Đã xoá sequence cuối của '{label}'")
        self.save_dataset(); self.save_frames_index(); self.update_stats()

    def delete_last_n_sequences(self):
        label = self.ent_label.get().strip() or self.current_label
        if not label:
            messagebox.showwarning("Thiếu nhãn", "Nhập nhãn trước khi xoá."); return
        try: n = int(self.ent_delete_n.get().strip())
        except Exception: n = 1
        self._delete_last_sequences(label, n)
        self._log(self.log_collect, f"🗑 Đã xoá {n} sequence cuối của '{label}'")
        self.save_dataset(); self.save_frames_index(); self.update_stats()

    def delete_label_all(self):
        label = self.ent_label_delete.get().strip()
        if not label:
            messagebox.showwarning("Thiếu nhãn", "Nhập nhãn cần xoá."); return
        if not messagebox.askyesno("Xác nhận", f"Xoá toàn bộ dữ liệu của nhãn '{label}'?"): return
        if label in self.dataset: del self.dataset[label]
        if label in self.labels_order: self.labels_order.remove(label)
        if label in self.frames_index:
            for rel in self.frames_index[label]:
                seq_dir = self.frames_root / rel
                try:
                    for p in sorted(seq_dir.glob("*")): p.unlink()
                    seq_dir.rmdir()
                except Exception: pass
            del self.frames_index[label]
        label_dir = self.frames_root / label
        if label_dir.exists():
            try:
                for p in label_dir.glob("*"):
                    for f in p.glob("*"): f.unlink()
                    p.rmdir()
                label_dir.rmdir()
            except Exception: pass
        self._log(self.log_collect, f"☠ Đã xoá toàn bộ nhãn '{label}'")
        self.save_dataset(); self.save_frames_index(); self.update_stats()

    def _delete_last_sequences(self, label, n):
        if label not in self.dataset: return
        n = min(n, len(self.dataset[label]))
        for _ in range(n):
            if self.dataset[label]: self.dataset[label].pop()
        dirs = self.frames_index.get(label, [])
        for _ in range(min(n, len(dirs))):
            last_rel = dirs.pop()
            seq_dir = self.frames_root / last_rel
            try:
                for p in sorted(seq_dir.glob("*")): p.unlink()
                seq_dir.rmdir()
            except Exception: pass


    # ---- Train ----
    def unlock(self):
        pwd = simpledialog.askstring("Mật khẩu", "Nhập mật khẩu huấn luyện:", show='*')
        if pwd == self.TRAIN_PASSWORD:
            self.train_locked = False
            self.btn_train.config(state=tk.NORMAL); self.btn_clear.config(state=tk.NORMAL)
            self.lbl_lock.config(text="ĐÃ MỞ KHOÁ — có thể train/xoá dataset.", fg='#34d399')
            self.nb.tab(2, text="🧠 Huấn luyện")
        else:
            messagebox.showerror("Sai mật khẩu", "Không đúng.")

    def train_model(self):
        if self.train_locked: return
        labels = [lb for lb in self.labels_order if lb in self.dataset and len(self.dataset[lb])>0]
        if len(labels) < 2:
            messagebox.showwarning("Thiếu dữ liệu", "Cần >= 2 nhãn, mỗi nhãn >= 1 sequence."); return
        self._log(self.log_train, "Bắt đầu train...")
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
            model = keras.Sequential([
                keras.Input(shape=(self.SEQ_LEN, 784)),
                keras.layers.LSTM(64, return_sequences=True),
                keras.layers.Dropout(0.3),
                keras.layers.LSTM(32),
                keras.layers.Dropout(0.2),
                keras.layers.Dense(32, activation='relu'),
                keras.layers.Dense(len(labels), activation='softmax')
            ])
            model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
            hist = model.fit(xs, ys, epochs=40, batch_size=16, validation_split=0.2, verbose=0)
            acc = float(hist.history['val_accuracy'][-1])
            self.model = model
            self._log(self.log_train, f"✅ Train xong. Val acc: {acc*100:.1f}% | Samples: {len(xs)} | Classes: {len(labels)}")
            self.lbl_train_stat.config(text=f"Dataset: {len(labels)} nhãn, {len(xs)} sequences")
        except Exception as e:
            self._log(self.log_train, f"❌ Lỗi train: {e}")

    def clear_dataset(self):
        if not messagebox.askyesno("Xác nhận", "Xoá tất cả dữ liệu & khung hình đã lưu?"): return
        self.dataset = {}; self.labels_order = []; self.model = None
        try:
            if self.frames_root.exists():
                for p in self.frames_root.rglob("*"):
                    if p.is_file(): p.unlink()
                for p in sorted(self.frames_root.glob("*"), reverse=True):
                    if p.is_dir():
                        try: p.rmdir()
                        except Exception: pass
        except Exception: pass
        self.frames_index = {}
        self.save_dataset(); self.save_frames_index(); self.update_stats()
        self._log(self.log_train, "Đã xoá sạch dataset.")


    # ---- Recognition (gesture→speech) ----
    def recognize_current(self):
        if self.model is None: return
        seq = np.array(list(self.frame_buffer)).reshape(1, self.SEQ_LEN, 784)
        probs = self.model.predict(seq, verbose=0)[0]
        idx = int(np.argmax(probs)); conf = float(probs[idx])
        labels = [lb for lb in self.labels_order if lb in self.dataset and len(self.dataset[lb])>0]
        label = labels[idx] if idx < len(labels) else "—"
        if conf > 0.6:
            self.lbl_pred.config(text=label)
            self.lbl_conf.config(text=f"Độ tin cậy: {conf*100:.1f}%")
            self._log(self.log_recog, f"✔ {label} ({conf*100:.1f}%)")
            if self.tts and label not in self.spoken_once:
                self.spoken_once.add(label)
                try: self.tts.say(label); self.tts.runAndWait()
                except Exception: pass
        else:
            self.lbl_pred.config(text="❓"); self.lbl_conf.config(text="Không chắc chắn")


    # ---- Speech→Gesture (no camera) ----
    def start_listening(self):
        if not sr or not self.recognizer:
            messagebox.showerror("Thiếu thư viện", "speech_recognition chưa sẵn sàng."); return
        try:
            self.mic = sr.Microphone()
        except Exception as e:
            messagebox.showerror("Mic", str(e)); return
        self.stt_is_listening = True
        self.btn_listen.config(state=tk.DISABLED); self.btn_stop_listen.config(state=tk.NORMAL)
        self.lbl_stt.config(text="🎙️ Đang nghe...", fg='#34d399')
        self.stop_camera()
        threading.Thread(target=self._listen_loop, daemon=True).start()

    def stop_listening(self):
        self.stt_is_listening = False
        self.btn_listen.config(state=tk.NORMAL); self.btn_stop_listen.config(state=tk.DISABLED)
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
        self.txt_text.delete('1.0', tk.END); self.txt_text.insert(tk.END, text)
        best, score = self.best_label(text)
        self.lbl_best.config(text=f"Nhãn khớp: {best or '—'} ({int(score*100)}%)")
        if best: self.play_label(best)

    def best_label(self, text):
        labels = [lb for lb in self.labels_order if lb in self.dataset and len(self.dataset[lb])>0]
        if not labels: return None, 0.0
        t = text.strip().lower(); lst = [s.lower() for s in labels]
        m = difflib.get_close_matches(t, lst, n=1, cutoff=0.4)
        if not m:
            scores = [(lab, difflib.SequenceMatcher(None, t, lab).ratio()) for lab in lst]
            best = max(scores, key=lambda x: x[1]); idx = lst.index(best[0])
            return labels[idx], float(best[1])
        else:
            idx = lst.index(m[0]); return labels[idx], 1.0

    def play_label(self, label):
        seq_dirs = self.frames_index.get(label, [])
        if not seq_dirs:
            messagebox.showinfo("Thiếu dữ liệu", f"Chưa có frame nào cho nhãn '{label}'."); return
        seq_rel = seq_dirs[-1]; seq_dir = self.frames_root / seq_rel
        frames = sorted(seq_dir.glob("*.jpg"))
        if not frames:
            messagebox.showinfo("Thiếu dữ liệu", f"Sequence {seq_rel} rỗng."); return
        self.playback_frames = [Image.open(p) for p in frames]
        self.playback_idx = 0; self.playback_label = label; self.playback_running = True
        self.render_playback_loop()

    def render_playback_loop(self):
        if not self.playback_running or not self.playback_frames: return
        W = self.canvas.winfo_width() or 860; H = self.canvas.winfo_height() or 540
        base = Image.new("RGB", (W,H), (5,10,20))
        w, h = int(W*0.72), int(H*0.72); x = (W - w)//2; y = (H - h)//2
        cur = self.playback_frames[self.playback_idx % len(self.playback_frames)].resize((w,h), Image.BILINEAR)
        base.paste(cur, (x,y))
        draw = ImageDraw.Draw(base); draw.rectangle((x, y-44, x+260, y-12), fill=(0,0,0,160))
        draw.text((x+10, y-36), f"Label: {self.playback_label}", fill=(200,230,255))
        imgtk = ImageTk.PhotoImage(base); self.canvas.create_image(0,0, anchor=tk.NW, image=imgtk); self.canvas.imgtk = imgtk
        self.playback_idx = (self.playback_idx + 1) % len(self.playback_frames)
        self.root.after(60, self.render_playback_loop)


    # ---- Persist / Utils ----
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
                    self.dataset = obj; self.labels_order = list(self.dataset.keys())
            except Exception:
                self.dataset = {}; self.labels_order = []

    def save_frames_index(self):
        with open(self.frames_index_path, 'w', encoding='utf-8') as f:
            json.dump(self.frames_index, f, ensure_ascii=False, indent=2)

    def load_frames_index(self):
        if self.frames_index_path.exists():
            try:
                self.frames_index = json.load(open(self.frames_index_path, 'r', encoding='utf-8'))
            except Exception:
                self.frames_index = {}

    def update_stats(self):
        tot_labels = len([lb for lb in self.dataset if len(self.dataset[lb])>0])
        tot_seq = sum(len(v) for v in self.dataset.values())
        cur = len(self.dataset.get(self.current_label, [])) if self.current_label else 0
        self.lbl_stat_counts.config(text=f"Sequences: {cur} | Tổng nhãn: {tot_labels} | Tổng seq: {tot_seq}")
        self.lbl_train_stat.config(text=f"Dataset: {tot_labels} nhãn, {tot_seq} sequences")

    def set_mode(self, m):
        self.mode.set(m)
        if m == "speech_to_gesture":
            self.lbl_status.config(text="🧭 Giọng nói → Cử chỉ (Camera OFF)", fg='#93c5fd')
            self.stop_camera()
        else:
            self.lbl_status.config(text="🧭 Cử chỉ → Giọng nói", fg='#93c5fd')
        self.on_home = False

    def _log(self, widget, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        widget.insert(tk.END, f"[{ts}] {msg}\n"); widget.see(tk.END)


if __name__ == "__main__":
    root = tk.Tk()
    app = AppV4(root)
    root.mainloop()
