"""
FINAL BEAUTIFUL VERSION - Giao diện đẹp + Đầy đủ tính năng
- UI đẹp với màu sắc
- Quản lý sequences (xem, xóa từng cái, xóa toàn bộ label)
- Bảng thống kê labels
- Khóa các chế độ khi đang hoạt động
- Fix TTS nói nhiều lần
- Frame đóng khi dừng listening
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
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


class BeautifulSignLanguageApp:
    SEQ_LEN = 30
    
    # Color scheme - Modern & Beautiful
    COLOR_PRIMARY = '#2563eb'      # Blue
    COLOR_SUCCESS = '#10b981'      # Green
    COLOR_WARNING = '#f59e0b'      # Orange
    COLOR_DANGER = '#ef4444'       # Red
    COLOR_PURPLE = '#8b5cf6'       # Purple
    COLOR_BG = '#f8fafc'           # Light gray background
    COLOR_CARD = '#ffffff'         # White cards
    COLOR_TEXT = '#1e293b'         # Dark text
    COLOR_TEXT_LIGHT = '#64748b'   # Light text
    COLOR_BORDER = '#e2e8f0'       # Border
    
    def __init__(self, root):
        self.root = root
        self.root.title("🤖 Hệ Thống Ngôn Ngữ Ký Hiệu AI - Final Version")
        self.root.geometry("1400x900")
        self.root.configure(bg=self.COLOR_BG)
        
        # State
        self.current_mode = None
        self.is_locked = False  # Lock để khóa các nút khi đang hoạt động
        
        # Camera
        self.cap = None
        self.is_running = False
        self.frame_buffer = deque(maxlen=self.SEQ_LEN)
        self.raw_roi_buffer = deque(maxlen=self.SEQ_LEN)
        
        # Collection
        self.is_collecting = False
        self.current_label = ""
        
        # Data
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
        
        # Speech
        self.recognizer = sr.Recognizer() if sr else None
        self.stt_is_listening = False
        
        # TTS
        self.tts = None
        self.tts_lock = threading.Lock()
        if pyttsx3:
            try:
                self.tts = pyttsx3.init()
                self.tts.setProperty('rate', 175)
                self.tts.setProperty('volume', 1.0)
            except:
                self.tts = None
        
        # Playback
        self.playback_frames = []
        self.playback_idx = 0
        self.playback_running = False
        self.playback_label = None
        
        # Load data
        self.load_dataset()
        self.load_frames_index()
        
        # Build UI
        self.build_ui()
        
        print("\n✅ FINAL VERSION READY!\n")
    
    def build_ui(self):
        # ===== TOP HEADER =====
        header = tk.Frame(self.root, bg=self.COLOR_PRIMARY, height=80)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)
        
        tk.Label(
            header,
            text="🤖 HỆ THỐNG NGÔN NGỮ KÝ HIỆU AI",
            font=('Arial', 24, 'bold'),
            bg=self.COLOR_PRIMARY,
            fg='white'
        ).pack(side=tk.LEFT, padx=30, pady=20)
        
        tk.Label(
            header,
            text="Nhận diện động tác & giọng nói bằng Deep Learning",
            font=('Arial', 12),
            bg=self.COLOR_PRIMARY,
            fg='white'
        ).pack(side=tk.LEFT, padx=10)
        
        # ===== MODE SELECTOR =====
        mode_frame = tk.Frame(self.root, bg=self.COLOR_BG)
        mode_frame.pack(fill=tk.X, pady=15, padx=20)
        
        tk.Label(
            mode_frame,
            text="Chọn chế độ:",
            font=('Arial', 13, 'bold'),
            bg=self.COLOR_BG,
            fg=self.COLOR_TEXT
        ).pack(side=tk.LEFT, padx=10)
        
        self.mode_buttons = {}
        modes = [
            ("collect", "✋ Thu thập", self.COLOR_SUCCESS),
            ("train", "🧠 Huấn luyện", self.COLOR_PURPLE),
            ("recognize", "🎯 Nhận diện", self.COLOR_PRIMARY),
            ("speech", "🎙️ Giọng nói", self.COLOR_WARNING)
        ]
        
        for mode_id, text, color in modes:
            btn = tk.Button(
                mode_frame,
                text=text,
                font=('Arial', 12, 'bold'),
                bg=color,
                fg='white',
                relief=tk.FLAT,
                padx=20,
                pady=10,
                cursor='hand2',
                command=lambda m=mode_id: self.show_mode(m)
            )
            btn.pack(side=tk.LEFT, padx=5)
            self.mode_buttons[mode_id] = btn
        
        # ===== MAIN CONTAINER =====
        main = tk.Frame(self.root, bg=self.COLOR_BG)
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # Left: Display
        left = tk.Frame(main, bg=self.COLOR_CARD, relief=tk.SOLID, bd=1)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Display header
        disp_header = tk.Frame(left, bg=self.COLOR_CARD)
        disp_header.pack(fill=tk.X, pady=10, padx=15)
        
        tk.Label(
            disp_header,
            text="📺 Màn hình hiển thị",
            font=('Arial', 14, 'bold'),
            bg=self.COLOR_CARD,
            fg=self.COLOR_TEXT
        ).pack(side=tk.LEFT)
        
        self.lbl_mode_indicator = tk.Label(
            disp_header,
            text="",
            font=('Arial', 11, 'bold'),
            bg=self.COLOR_CARD,
            fg=self.COLOR_PRIMARY
        )
        self.lbl_mode_indicator.pack(side=tk.RIGHT)
        
        # Canvas
        canvas_container = tk.Frame(left, bg='black', relief=tk.SUNKEN, bd=2)
        canvas_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))
        
        self.canvas = tk.Canvas(canvas_container, bg='black', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Camera controls
        self.cam_controls = tk.Frame(left, bg=self.COLOR_CARD)
        self.cam_controls.pack(fill=tk.X, padx=15, pady=(0, 15))
        
        cam_btn_frame = tk.Frame(self.cam_controls, bg=self.COLOR_CARD)
        cam_btn_frame.pack(side=tk.LEFT)
        
        self.btn_cam_on = tk.Button(
            cam_btn_frame,
            text="📷 Bật Camera",
            font=('Arial', 11, 'bold'),
            bg=self.COLOR_PRIMARY,
            fg='white',
            relief=tk.FLAT,
            padx=20,
            pady=8,
            cursor='hand2',
            command=self.start_camera
        )
        self.btn_cam_on.pack(side=tk.LEFT, padx=3)
        
        self.btn_cam_off = tk.Button(
            cam_btn_frame,
            text="⏹ Tắt",
            font=('Arial', 11, 'bold'),
            bg=self.COLOR_DANGER,
            fg='white',
            relief=tk.FLAT,
            padx=20,
            pady=8,
            cursor='hand2',
            command=self.stop_camera,
            state=tk.DISABLED
        )
        self.btn_cam_off.pack(side=tk.LEFT, padx=3)
        
        cam_status = tk.Frame(self.cam_controls, bg=self.COLOR_CARD)
        cam_status.pack(side=tk.RIGHT)
        
        self.lbl_cam_status = tk.Label(
            cam_status,
            text="⚪ Tắt",
            font=('Arial', 11, 'bold'),
            bg=self.COLOR_CARD,
            fg=self.COLOR_TEXT_LIGHT
        )
        self.lbl_cam_status.pack(side=tk.LEFT, padx=10)
        
        self.lbl_buffer = tk.Label(
            cam_status,
            text="Buffer: 0/30",
            font=('Arial', 11, 'bold'),
            bg=self.COLOR_CARD,
            fg=self.COLOR_WARNING
        )
        self.lbl_buffer.pack(side=tk.LEFT, padx=10)
        
        # Right: Control Panel
        right = tk.Frame(main, bg=self.COLOR_CARD, relief=tk.SOLID, bd=1, width=500)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        right.pack_propagate(False)
        
        # Control header
        ctrl_header = tk.Frame(right, bg=self.COLOR_CARD, height=50)
        ctrl_header.pack(fill=tk.X)
        ctrl_header.pack_propagate(False)
        
        self.lbl_panel_title = tk.Label(
            ctrl_header,
            text="Bảng điều khiển",
            font=('Arial', 14, 'bold'),
            bg=self.COLOR_CARD,
            fg=self.COLOR_TEXT
        )
        self.lbl_panel_title.pack(pady=15)
        
        # Panels container
        self.panels_container = tk.Frame(right, bg=self.COLOR_CARD)
        self.panels_container.pack(fill=tk.BOTH, expand=True)
        
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
        self.collect_panel = tk.Frame(self.panels_container, bg=self.COLOR_CARD)
        
        # Input
        tk.Label(
            self.collect_panel,
            text="Tên động tác:",
            font=('Arial', 11, 'bold'),
            bg=self.COLOR_CARD,
            fg=self.COLOR_TEXT
        ).pack(pady=(10, 5), padx=15, anchor=tk.W)
        
        self.entry_label = tk.Entry(
            self.collect_panel,
            font=('Arial', 12),
            bg='#f1f5f9',
            fg=self.COLOR_TEXT,
            relief=tk.FLAT,
            insertbackground=self.COLOR_TEXT
        )
        self.entry_label.pack(fill=tk.X, padx=15, ipady=8)
        
        # Buttons
        btn_frame = tk.Frame(self.collect_panel, bg=self.COLOR_CARD)
        btn_frame.pack(pady=15)
        
        self.btn_start_collect = tk.Button(
            btn_frame,
            text="🎬 Bắt đầu ghi",
            font=('Arial', 11, 'bold'),
            bg=self.COLOR_SUCCESS,
            fg='white',
            relief=tk.FLAT,
            padx=20,
            pady=10,
            cursor='hand2',
            command=self.start_collecting
        )
        self.btn_start_collect.pack(side=tk.LEFT, padx=5)
        
        self.btn_stop_collect = tk.Button(
            btn_frame,
            text="⏸ Dừng",
            font=('Arial', 11, 'bold'),
            bg=self.COLOR_WARNING,
            fg='white',
            relief=tk.FLAT,
            padx=20,
            pady=10,
            cursor='hand2',
            command=self.stop_collecting,
            state=tk.DISABLED
        )
        self.btn_stop_collect.pack(side=tk.LEFT, padx=5)
        
        # Stats
        self.lbl_collect_stats = tk.Label(
            self.collect_panel,
            text="Sequences: 0",
            font=('Arial', 11, 'bold'),
            bg=self.COLOR_CARD,
            fg=self.COLOR_TEXT
        )
        self.lbl_collect_stats.pack(pady=10)
        
        # Separator
        tk.Frame(self.collect_panel, bg=self.COLOR_BORDER, height=1).pack(fill=tk.X, padx=15, pady=10)
        
        # Sequences list
        tk.Label(
            self.collect_panel,
            text="📋 Sequences đã thu thập:",
            font=('Arial', 11, 'bold'),
            bg=self.COLOR_CARD,
            fg=self.COLOR_TEXT
        ).pack(pady=(5, 5), padx=15, anchor=tk.W)
        
        list_frame = tk.Frame(self.collect_panel, bg=self.COLOR_CARD)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.seq_listbox = tk.Listbox(
            list_frame,
            font=('Consolas', 10),
            bg='#f1f5f9',
            fg=self.COLOR_TEXT,
            relief=tk.FLAT,
            selectmode=tk.SINGLE,
            yscrollcommand=scrollbar.set
        )
        self.seq_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.seq_listbox.yview)
        
        # Delete buttons
        del_btn_frame = tk.Frame(self.collect_panel, bg=self.COLOR_CARD)
        del_btn_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
        
        tk.Button(
            del_btn_frame,
            text="🗑️ Xóa sequence",
            font=('Arial', 10, 'bold'),
            bg=self.COLOR_DANGER,
            fg='white',
            relief=tk.FLAT,
            padx=15,
            pady=6,
            cursor='hand2',
            command=self.delete_selected_sequence
        ).pack(side=tk.LEFT, padx=3)
        
        tk.Button(
            del_btn_frame,
            text="🗑️ Xóa toàn bộ label",
            font=('Arial', 10, 'bold'),
            bg=self.COLOR_DANGER,
            fg='white',
            relief=tk.FLAT,
            padx=15,
            pady=6,
            cursor='hand2',
            command=self.delete_entire_label
        ).pack(side=tk.LEFT, padx=3)
    
    def build_train_panel(self):
        self.train_panel = tk.Frame(self.panels_container, bg=self.COLOR_CARD)
        
        # Stats
        self.lbl_train_stats = tk.Label(
            self.train_panel,
            text="Dataset: 0 nhãn, 0 sequences\nChưa có mô hình",
            font=('Arial', 12, 'bold'),
            bg=self.COLOR_CARD,
            fg=self.COLOR_TEXT,
            justify=tk.CENTER
        )
        self.lbl_train_stats.pack(pady=20)
        
        # Buttons
        btn_frame = tk.Frame(self.train_panel, bg=self.COLOR_CARD)
        btn_frame.pack(pady=10)
        
        self.btn_train = tk.Button(
            btn_frame,
            text="🚀 Huấn luyện mô hình",
            font=('Arial', 12, 'bold'),
            bg=self.COLOR_PURPLE,
            fg='white',
            relief=tk.FLAT,
            padx=30,
            pady=15,
            cursor='hand2',
            command=self.train_model
        )
        self.btn_train.pack(pady=8)
        
        tk.Button(
            btn_frame,
            text="🗑️ Xóa toàn bộ dataset",
            font=('Arial', 12, 'bold'),
            bg=self.COLOR_DANGER,
            fg='white',
            relief=tk.FLAT,
            padx=30,
            pady=15,
            cursor='hand2',
            command=self.clear_dataset
        ).pack(pady=8)
        
        # Separator
        tk.Frame(self.train_panel, bg=self.COLOR_BORDER, height=1).pack(fill=tk.X, padx=15, pady=15)
        
        # Statistics table
        tk.Label(
            self.train_panel,
            text="📊 Thống kê Labels:",
            font=('Arial', 11, 'bold'),
            bg=self.COLOR_CARD,
            fg=self.COLOR_TEXT
        ).pack(pady=(5, 10), padx=15, anchor=tk.W)
        
        # Treeview for stats
        tree_frame = tk.Frame(self.train_panel, bg=self.COLOR_CARD)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        tree_scroll = tk.Scrollbar(tree_frame)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.stats_tree = ttk.Treeview(
            tree_frame,
            columns=('label', 'sequences', 'frames'),
            show='headings',
            height=8,
            yscrollcommand=tree_scroll.set
        )
        tree_scroll.config(command=self.stats_tree.yview)
        
        self.stats_tree.heading('label', text='Label')
        self.stats_tree.heading('sequences', text='Sequences')
        self.stats_tree.heading('frames', text='Frames')
        
        self.stats_tree.column('label', width=150, anchor=tk.W)
        self.stats_tree.column('sequences', width=80, anchor=tk.CENTER)
        self.stats_tree.column('frames', width=80, anchor=tk.CENTER)
        
        self.stats_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    def build_recognize_panel(self):
        self.recognize_panel = tk.Frame(self.panels_container, bg=self.COLOR_CARD)
        
        tk.Label(
            self.recognize_panel,
            text="Kết quả nhận diện:",
            font=('Arial', 12, 'bold'),
            bg=self.COLOR_CARD,
            fg=self.COLOR_TEXT
        ).pack(pady=15)
        
        # Result display
        result_frame = tk.Frame(
            self.recognize_panel,
            bg='#f1f5f9',
            relief=tk.SOLID,
            bd=2
        )
        result_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.lbl_pred = tk.Label(
            result_frame,
            text="—",
            font=('Arial', 48, 'bold'),
            bg='#f1f5f9',
            fg=self.COLOR_PRIMARY
        )
        self.lbl_pred.pack(pady=20)
        
        self.lbl_conf = tk.Label(
            result_frame,
            text="Chờ buffer đầy...",
            font=('Arial', 13),
            bg='#f1f5f9',
            fg=self.COLOR_TEXT_LIGHT
        )
        self.lbl_conf.pack(pady=(0, 20))
        
        # Info
        info_frame = tk.Frame(self.recognize_panel, bg=self.COLOR_CARD)
        info_frame.pack(fill=tk.X, padx=20, pady=20)
        
        tk.Label(
            info_frame,
            text="🔊 Text-to-Speech:",
            font=('Arial', 11, 'bold'),
            bg=self.COLOR_CARD,
            fg=self.COLOR_TEXT
        ).pack(anchor=tk.W, pady=2)
        
        tk.Label(
            info_frame,
            text="Hệ thống sẽ tự động đọc tên động tác\nmỗi khi nhận diện thành công",
            font=('Arial', 10),
            bg=self.COLOR_CARD,
            fg=self.COLOR_TEXT_LIGHT,
            justify=tk.LEFT
        ).pack(anchor=tk.W, pady=2)
    
    def build_speech_panel(self):
        self.speech_panel = tk.Frame(self.panels_container, bg=self.COLOR_CARD)
        
        # Mic status
        self.lbl_mic = tk.Label(
            self.speech_panel,
            text="🎤 Microphone: Sẵn sàng",
            font=('Arial', 12, 'bold'),
            bg=self.COLOR_CARD,
            fg=self.COLOR_TEXT
        )
        self.lbl_mic.pack(pady=15)
        
        # Buttons
        btn_frame = tk.Frame(self.speech_panel, bg=self.COLOR_CARD)
        btn_frame.pack(pady=10)
        
        self.btn_listen = tk.Button(
            btn_frame,
            text="🎧 Bắt đầu nghe",
            font=('Arial', 11, 'bold'),
            bg=self.COLOR_SUCCESS,
            fg='white',
            relief=tk.FLAT,
            padx=20,
            pady=10,
            cursor='hand2',
            command=self.start_listening
        )
        self.btn_listen.pack(side=tk.LEFT, padx=5)
        
        self.btn_stop_listen = tk.Button(
            btn_frame,
            text="🛑 Dừng",
            font=('Arial', 11, 'bold'),
            bg=self.COLOR_DANGER,
            fg='white',
            relief=tk.FLAT,
            padx=20,
            pady=10,
            cursor='hand2',
            command=self.stop_listening,
            state=tk.DISABLED
        )
        self.btn_stop_listen.pack(side=tk.LEFT, padx=5)
        
        # Text display
        tk.Label(
            self.speech_panel,
            text="Văn bản nhận dạng:",
            font=('Arial', 11, 'bold'),
            bg=self.COLOR_CARD,
            fg=self.COLOR_TEXT
        ).pack(pady=(15, 5), padx=20, anchor=tk.W)
        
        text_frame = tk.Frame(self.speech_panel, bg=self.COLOR_CARD)
        text_frame.pack(fill=tk.X, padx=20, pady=5)
        
        self.txt_speech = tk.Text(
            text_frame,
            height=3,
            font=('Arial', 12),
            bg='#f1f5f9',
            fg=self.COLOR_TEXT,
            relief=tk.FLAT,
            wrap=tk.WORD
        )
        self.txt_speech.pack(fill=tk.X, ipady=5)
        
        # Match result
        self.lbl_match = tk.Label(
            self.speech_panel,
            text="Khớp: —",
            font=('Arial', 14, 'bold'),
            bg=self.COLOR_CARD,
            fg=self.COLOR_PRIMARY
        )
        self.lbl_match.pack(pady=15)
        
        # Info
        info_frame = tk.Frame(self.speech_panel, bg='#f1f5f9', relief=tk.SOLID, bd=1)
        info_frame.pack(fill=tk.X, padx=20, pady=15)
        
        tk.Label(
            info_frame,
            text="📹 Animation Playback",
            font=('Arial', 11, 'bold'),
            bg='#f1f5f9',
            fg=self.COLOR_TEXT
        ).pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        tk.Label(
            info_frame,
            text="Khi tìm thấy label khớp, hệ thống\nsẽ tự động phát animation",
            font=('Arial', 10),
            bg='#f1f5f9',
            fg=self.COLOR_TEXT_LIGHT,
            justify=tk.LEFT
        ).pack(anchor=tk.W, padx=10, pady=(0, 10))
    
    # ===== MODE MANAGEMENT =====
    
    def show_mode(self, mode):
        if self.is_locked:
            messagebox.showwarning("Đang hoạt động", "Vui lòng dừng hoạt động hiện tại trước!")
            return
        
        self.current_mode = mode
        
        # Hide all panels
        self.collect_panel.pack_forget()
        self.train_panel.pack_forget()
        self.recognize_panel.pack_forget()
        self.speech_panel.pack_forget()
        
        # Stop playback
        self.playback_running = False
        
        # Update UI
        mode_info = {
            "collect": ("✋ THU THẬP MẪU", "📋 Quản lý thu thập", self.COLOR_SUCCESS),
            "train": ("🧠 HUẤN LUYỆN", "🚀 Huấn luyện & Thống kê", self.COLOR_PURPLE),
            "recognize": ("🎯 NHẬN DIỆN", "🎯 Nhận diện động tác", self.COLOR_PRIMARY),
            "speech": ("🎙️ GIỌNG NÓI", "🎙️ Chuyển giọng nói", self.COLOR_WARNING)
        }
        
        indicator, title, color = mode_info[mode]
        self.lbl_mode_indicator.config(text=indicator, fg=color)
        self.lbl_panel_title.config(text=title)
        
        # Show panel
        if mode == "collect":
            self.collect_panel.pack(fill=tk.BOTH, expand=True)
            self.refresh_sequences_list()
            self.update_stats()
        elif mode == "train":
            self.train_panel.pack(fill=tk.BOTH, expand=True)
            self.refresh_stats_table()
            self.update_stats()
        elif mode == "recognize":
            self.recognize_panel.pack(fill=tk.BOTH, expand=True)
        elif mode == "speech":
            self.speech_panel.pack(fill=tk.BOTH, expand=True)
    
    def lock_interface(self, lock=True):
        """Khóa/mở khóa interface"""
        self.is_locked = lock
        state = tk.DISABLED if lock else tk.NORMAL
        
        for btn in self.mode_buttons.values():
            btn.config(state=state)
    
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
        self.lbl_cam_status.config(text="🟢 Đang chạy", fg=self.COLOR_SUCCESS)
        self.frame_buffer.clear()
        
        # Stop playback
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
        self.lbl_cam_status.config(text="⚪ Tắt", fg=self.COLOR_TEXT_LIGHT)
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
            elif self.current_mode == "recognize" and self.model:
                self.recognize_current()
        
        mask_3ch = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        frame[100:380, 100:540] = cv2.addWeighted(roi, 0.7, mask_3ch, 0.3, 0)
        
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        
        canvas_w = self.canvas.winfo_width() or 800
        canvas_h = self.canvas.winfo_height() or 600
        img = img.resize((canvas_w, canvas_h), Image.LANCZOS)
        
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
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập tên động tác!")
            return
        
        if not self.is_running:
            messagebox.showwarning("Cảnh báo", "Vui lòng bật camera trước!")
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
        self.lock_interface(True)
        
        print(f"✓ Started collecting: {label}")
    
    def stop_collecting(self):
        self.is_collecting = False
        self.current_label = ""
        
        self.btn_start_collect.config(state=tk.NORMAL)
        self.btn_stop_collect.config(state=tk.DISABLED)
        self.lock_interface(False)
        
        self.save_dataset()
        self.save_frames_index()
        self.refresh_sequences_list()
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
    
    def refresh_sequences_list(self):
        """Refresh sequences listbox"""
        self.seq_listbox.delete(0, tk.END)
        
        label = self.entry_label.get().strip()
        if not label or label not in self.dataset:
            return
        
        sequences = self.dataset[label]
        for i in range(len(sequences)):
            self.seq_listbox.insert(tk.END, f"  Sequence {i+1}")
    
    def delete_selected_sequence(self):
        """Xóa sequence được chọn"""
        label = self.entry_label.get().strip()
        if not label or label not in self.dataset:
            messagebox.showwarning("Cảnh báo", "Chọn label trước!")
            return
        
        selection = self.seq_listbox.curselection()
        if not selection:
            messagebox.showwarning("Cảnh báo", "Chọn sequence cần xóa!")
            return
        
        idx = selection[0]
        
        if not messagebox.askyesno("Xác nhận", f"Xóa Sequence {idx+1}?"):
            return
        
        # Delete from dataset
        del self.dataset[label][idx]
        
        # Delete frames
        if label in self.frames_index and idx < len(self.frames_index[label]):
            seq_rel = self.frames_index[label][idx]
            seq_dir = self.frames_root / seq_rel
            try:
                if seq_dir.exists():
                    for p in seq_dir.glob("*.jpg"):
                        p.unlink()
                    seq_dir.rmdir()
            except Exception as e:
                print(f"✗ Error deleting frames: {e}")
            
            del self.frames_index[label][idx]
        
        # If no sequences left, remove label
        if len(self.dataset[label]) == 0:
            del self.dataset[label]
            self.labels_order.remove(label)
            if label in self.frames_index:
                del self.frames_index[label]
        
        self.save_dataset()
        self.save_frames_index()
        self.refresh_sequences_list()
        self.update_stats()
        print(f"✓ Deleted sequence {idx+1} of '{label}'")
    
    def delete_entire_label(self):
        """Xóa toàn bộ dữ liệu của label"""
        label = self.entry_label.get().strip()
        if not label or label not in self.dataset:
            messagebox.showwarning("Cảnh báo", "Label không tồn tại!")
            return
        
        seq_count = len(self.dataset[label])
        if not messagebox.askyesno("Xác nhận", 
            f"Xóa toàn bộ label '{label}' ({seq_count} sequences)?"):
            return
        
        # Delete dataset
        del self.dataset[label]
        self.labels_order.remove(label)
        
        # Delete frames
        if label in self.frames_index:
            label_dir = self.frames_root / label
            try:
                if label_dir.exists():
                    for p in label_dir.rglob("*"):
                        if p.is_file():
                            p.unlink()
                    for p in sorted(label_dir.glob("*"), reverse=True):
                        if p.is_dir():
                            try:
                                p.rmdir()
                            except:
                                pass
                    label_dir.rmdir()
            except Exception as e:
                print(f"✗ Error deleting label dir: {e}")
            
            del self.frames_index[label]
        
        self.save_dataset()
        self.save_frames_index()
        self.refresh_sequences_list()
        self.update_stats()
        self.entry_label.delete(0, tk.END)
        print(f"✓ Deleted entire label '{label}'")
    
    # ===== TRAINING =====
    
    def train_model(self):
        labels = [lb for lb in self.labels_order if lb in self.dataset and len(self.dataset[lb]) > 0]
        if len(labels) < 2:
            messagebox.showwarning("Cảnh báo", "Cần ít nhất 2 nhãn để train!")
            return
        
        self.lock_interface(True)
        self.btn_train.config(state=tk.DISABLED, text="⏳ Đang train...")
        
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
            
            self.root.after(0, lambda: self._on_train_complete(len(labels), len(xs), acc))
            
        except Exception as e:
            print(f"✗ Training error: {e}")
            self.root.after(0, lambda: messagebox.showerror("Lỗi", f"Training thất bại: {e}"))
            self.root.after(0, lambda: self.lock_interface(False))
            self.root.after(0, lambda: self.btn_train.config(state=tk.NORMAL, text="🚀 Huấn luyện mô hình"))
    
    def _on_train_complete(self, n_labels, n_seqs, acc):
        """Callback when training completes"""
        self.lock_interface(False)
        self.btn_train.config(state=tk.NORMAL, text="🚀 Huấn luyện mô hình")
        self.update_stats()
        self.refresh_stats_table()
        
        messagebox.showinfo("Thành công!", 
            f"Mô hình đã được huấn luyện!\n\n"
            f"Labels: {n_labels}\n"
            f"Sequences: {n_seqs}\n"
            f"Accuracy: {acc*100:.1f}%")
    
    def clear_dataset(self):
        if not messagebox.askyesno("Xác nhận", "Xóa TOÀN BỘ dataset?"):
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
        self.refresh_stats_table()
        print("✓ Dataset cleared")
    
    def refresh_stats_table(self):
        """Refresh statistics table"""
        # Clear table
        for item in self.stats_tree.get_children():
            self.stats_tree.delete(item)
        
        # Add data
        for label in self.labels_order:
            if label in self.dataset:
                seq_count = len(self.dataset[label])
                frame_count = seq_count * self.SEQ_LEN
                self.stats_tree.insert('', tk.END, values=(label, seq_count, frame_count))
    
    # ===== RECOGNITION =====
    
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
            
            # FIX TTS: Speak every time (remove spoken_once check)
            if self.tts:
                print(f"🔊 Speaking: {label}")
                threading.Thread(target=lambda: self._speak(label), daemon=True).start()
        else:
            self.lbl_pred.config(text="❓")
            self.lbl_conf.config(text="Không chắc chắn")
    
    def _speak(self, text):
        """Speak text using TTS with lock"""
        with self.tts_lock:
            try:
                self.tts.say(text)
                self.tts.runAndWait()
            except Exception as e:
                print(f"✗ Speak error: {e}")
    
    # ===== SPEECH RECOGNITION =====
    
    def start_listening(self):
        if not sr or not self.recognizer:
            messagebox.showerror("Thiếu thư viện", 
                "speech_recognition chưa được cài đặt!\n"
                "Chạy: pip install SpeechRecognition pyaudio")
            return
        
        try:
            self.mic = sr.Microphone()
        except Exception as e:
            messagebox.showerror("Lỗi Mic", str(e))
            return
        
        self.stt_is_listening = True
        self.btn_listen.config(state=tk.DISABLED)
        self.btn_stop_listen.config(state=tk.NORMAL)
        self.lbl_mic.config(text="🎙️ Đang nghe...", fg=self.COLOR_SUCCESS)
        self.lock_interface(True)
        
        threading.Thread(target=self._listen_loop, daemon=True).start()
        print("✓ Listening started")
    
    def stop_listening(self):
        """Stop listening and close frame"""
        self.stt_is_listening = False
        self.btn_listen.config(state=tk.NORMAL)
        self.btn_stop_listen.config(state=tk.DISABLED)
        self.lbl_mic.config(text="🎤 Microphone: Sẵn sàng", fg=self.COLOR_TEXT)
        self.lock_interface(False)
        
        # CLOSE PLAYBACK FRAME
        self.playback_running = False
        self.canvas.delete("all")
        
        print("✓ Listening stopped, playback closed")
    
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
        
        m = difflib.get_close_matches(t, lst, n=1, cutoff=0.4)
        if m:
            idx = lst.index(m[0])
            return labels[idx], 1.0
        
        scores = [(lab, difflib.SequenceMatcher(None, t, lab.lower()).ratio()) for lab in labels]
        best = max(scores, key=lambda x: x[1])
        return best[0], float(best[1])
    
    def play_label(self, label):
        """Play animation for label"""
        seq_dirs = self.frames_index.get(label, [])
        if not seq_dirs:
            print(f"✗ No frames for label: {label}")
            messagebox.showinfo("Thiếu dữ liệu", f"Chưa có frames cho '{label}'")
            return
        
        seq_rel = seq_dirs[-1]
        seq_dir = self.frames_root / seq_rel
        frames = sorted(seq_dir.glob("*.jpg"))
        
        if not frames:
            print(f"✗ Empty sequence: {seq_rel}")
            return
        
        print(f"✓ Playing animation: {label} ({len(frames)} frames)")
        
        self.playback_frames = [Image.open(p) for p in frames]
        self.playback_idx = 0
        self.playback_label = label
        self.playback_running = True
        
        if self.is_running:
            self.stop_camera()
        
        self.render_playback()
    
    def render_playback(self):
        """Render playback animation"""
        if not self.playback_running or not self.playback_frames:
            return
        
        canvas_w = self.canvas.winfo_width() or 800
        canvas_h = self.canvas.winfo_height() or 600
        
        base = Image.new("RGB", (canvas_w, canvas_h), (30, 30, 30))
        
        w, h = int(canvas_w * 0.7), int(canvas_h * 0.7)
        x, y = (canvas_w - w) // 2, (canvas_h - h) // 2
        
        frame_img = self.playback_frames[self.playback_idx % len(self.playback_frames)]
        frame_img = frame_img.resize((w, h), Image.LANCZOS)
        base.paste(frame_img, (x, y))
        
        draw = ImageDraw.Draw(base)
        draw.rectangle((x, y - 40, x + 300, y - 10), fill=(50, 50, 50))
        draw.text((x + 15, y - 32), f"📹 {self.playback_label}", fill=(255, 255, 255))
        
        photo = ImageTk.PhotoImage(base)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=photo)
        self.canvas.image = photo
        
        self.playback_idx = (self.playback_idx + 1) % len(self.playback_frames)
        self.root.after(60, self.render_playback)
    
    # ===== UTILS =====
    
    def update_stats(self):
        tot_labels = len([lb for lb in self.dataset if len(self.dataset[lb]) > 0])
        tot_seq = sum(len(v) for v in self.dataset.values())
        
        if self.current_mode == "collect":
            label = self.entry_label.get().strip()
            cur = len(self.dataset.get(label, [])) if label else 0
            self.lbl_collect_stats.config(
                text=f"Sequences hiện tại: {cur} | Tổng: {tot_seq}"
            )
        
        model_status = f"✅ Sẵn sàng" if self.model else "Chưa train"
        self.lbl_train_stats.config(
            text=f"Dataset: {tot_labels} nhãn, {tot_seq} sequences\nMô hình: {model_status}"
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
            except:
                self.frames_index = {}


if __name__ == "__main__":
    print("\n" + "="*70)
    print("🤖 HỆ THỐNG NGÔN NGỮ KÝ HIỆU AI - FINAL BEAUTIFUL VERSION")
    print("="*70)
    print("\n✨ TÍNH NĂNG:")
    print("  ✅ Giao diện đẹp với màu sắc hiện đại")
    print("  ✅ Quản lý sequences (xem, xóa từng cái, xóa cả label)")
    print("  ✅ Bảng thống kê labels chi tiết")
    print("  ✅ Khóa interface khi đang hoạt động")
    print("  ✅ TTS nói mỗi lần nhận diện (đã fix)")
    print("  ✅ Frame đóng khi dừng listening")
    print("\n" + "="*70 + "\n")
    
    root = tk.Tk()
    app = BeautifulSignLanguageApp(root)
    root.mainloop()