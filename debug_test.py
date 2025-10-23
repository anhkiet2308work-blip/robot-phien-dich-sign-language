"""
DEBUG VERSION - Tìm lỗi màn hình đen
Với console output và màu cực sáng
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import cv2
import numpy as np
import pickle, json, os, time, random
from datetime import datetime
from PIL import Image, ImageTk, ImageDraw
import threading
from collections import deque
import difflib
from pathlib import Path

print("=" * 50)
print("STARTING DEBUG VERSION")
print("=" * 50)

os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL','2')
import tensorflow as tf
from tensorflow import keras
try:
    tf.get_logger().setLevel('ERROR')
except Exception:
    pass

try:
    import speech_recognition as sr
    print("✓ speech_recognition imported")
except Exception:
    sr = None
    print("✗ speech_recognition NOT available")

try:
    import pyttsx3
    print("✓ pyttsx3 imported")
except Exception:
    pyttsx3 = None
    print("✗ pyttsx3 NOT available")


class DebugApp:
    SEQ_LEN = 30
    
    def __init__(self, root):
        print("\n>>> Initializing DebugApp")
        self.root = root
        self.root.title("DEBUG - Sign Language")
        self.root.geometry("1200x800")
        
        print(">>> Setting background to WHITE (for testing)")
        self.root.configure(bg='white')  # TRẮNG để test
        
        # State
        self.app_mode = "HOME"
        
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
        
        # Speech
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
        
        # Playback
        self.playback_frames = []
        self.playback_idx = 0
        self.playback_running = False
        self.playback_label = None
        
        print(">>> Loading dataset")
        self.load_dataset()
        self.load_frames_index()
        
        print(">>> Building UI")
        self.build_ui()
        
        print(">>> Showing home screen")
        self.show_home()
        
        print("\n" + "=" * 50)
        print("INITIALIZATION COMPLETE")
        print("If you see this but screen is black,")
        print("the problem is with Tkinter rendering!")
        print("=" * 50 + "\n")
    
    def build_ui(self):
        print(">>> build_ui() called")
        
        # ===== HOME SCREEN - MÀU CỰC SÁNG =====
        print(">>> Creating home_frame")
        self.home_frame = tk.Frame(self.root, bg='yellow', width=1200, height=800)
        print(">>> home_frame created with YELLOW background")
        
        # Test label 1
        print(">>> Creating test label 1")
        test_label1 = tk.Label(
            self.home_frame,
            text="TEST 1: Nếu thấy dòng này = Tkinter OK!",
            font=('Arial', 20, 'bold'),
            bg='yellow',
            fg='red',
            pady=20
        )
        test_label1.pack(pady=10)
        print(">>> Test label 1 packed")
        
        # Robot emoji
        print(">>> Creating robot emoji")
        emoji_label = tk.Label(
            self.home_frame,
            text="🤖",
            font=('Arial', 100),
            bg='yellow',
            fg='black'
        )
        emoji_label.pack(pady=20)
        print(">>> Robot emoji packed")
        
        # Title
        print(">>> Creating title")
        title_label = tk.Label(
            self.home_frame,
            text="Hệ Thống Học Ngôn Ngữ Ký Hiệu",
            font=('Arial', 28, 'bold'),
            bg='yellow',
            fg='blue'
        )
        title_label.pack(pady=10)
        print(">>> Title packed")
        
        # Subtitle
        print(">>> Creating subtitle")
        subtitle_label = tk.Label(
            self.home_frame,
            text="DEBUG VERSION - Màu sáng để test",
            font=('Arial', 14),
            bg='yellow',
            fg='green'
        )
        subtitle_label.pack(pady=10)
        print(">>> Subtitle packed")
        
        # Button
        print(">>> Creating start button")
        btn_start = tk.Button(
            self.home_frame,
            text="BẮT ĐẦU (CLICK ĐỂ VÀO APP)",
            font=('Arial', 20, 'bold'),
            bg='red',
            fg='white',
            relief=tk.RAISED,
            bd=5,
            padx=50,
            pady=20,
            cursor='hand2',
            command=self.enter_app
        )
        btn_start.pack(pady=30)
        print(">>> Start button packed")
        
        # Status
        print(">>> Creating status label")
        status_label = tk.Label(
            self.home_frame,
            text="Nếu thấy màu vàng + text này = Tkinter hoạt động!\nNếu vẫn đen = vấn đề Tkinter/Python!",
            font=('Arial', 12),
            bg='yellow',
            fg='purple',
            pady=10
        )
        status_label.pack(pady=10)
        print(">>> Status label packed")
        
        print(">>> home_frame setup complete")
        
        # ===== APP FRAME =====
        print(">>> Creating app_frame")
        self.app_frame = tk.Frame(self.root, bg='lightblue')
        
        # Simple app UI
        tk.Label(
            self.app_frame,
            text="APP MODE - Background xanh nhạt",
            font=('Arial', 24, 'bold'),
            bg='lightblue',
            fg='darkblue',
            pady=30
        ).pack()
        
        tk.Button(
            self.app_frame,
            text="🏠 Về Home",
            font=('Arial', 18, 'bold'),
            bg='orange',
            fg='white',
            relief=tk.RAISED,
            bd=5,
            padx=40,
            pady=15,
            cursor='hand2',
            command=self.show_home
        ).pack(pady=20)
        
        tk.Label(
            self.app_frame,
            text="Nếu thấy màn hình này = UI hoạt động OK!\nVấn đề chỉ là màu tối trong version cũ.",
            font=('Arial', 14),
            bg='lightblue',
            fg='black',
            pady=20
        ).pack(pady=10)
        
        print(">>> app_frame setup complete")
        print(">>> build_ui() finished\n")
    
    def show_home(self):
        print("\n>>> show_home() called")
        print(">>> Hiding app_frame")
        self.app_frame.pack_forget()
        
        print(">>> Showing home_frame")
        self.home_frame.pack(fill=tk.BOTH, expand=True)
        
        print(">>> home_frame should be visible now")
        print(">>> Background: YELLOW")
        print(">>> Text: Various colors (red, blue, green, purple)")
        print(">>> Button: RED\n")
        
        self.app_mode = "HOME"
    
    def enter_app(self):
        print("\n>>> enter_app() called (Button clicked!)")
        print(">>> Hiding home_frame")
        self.home_frame.pack_forget()
        
        print(">>> Showing app_frame")
        self.app_frame.pack(fill=tk.BOTH, expand=True)
        
        print(">>> app_frame should be visible now")
        print(">>> Background: LIGHT BLUE\n")
        
        self.app_mode = "APP"
    
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
                print("✗ Could not load dataset")
        else:
            print("✗ No dataset file found")
    
    def load_frames_index(self):
        if self.frames_index_path.exists():
            try:
                self.frames_index = json.load(
                    open(self.frames_index_path, 'r', encoding='utf-8')
                )
                print(f"✓ Loaded frames index")
            except:
                self.frames_index = {}
                print("✗ Could not load frames index")
        else:
            print("✗ No frames index found")


print("\n" + "=" * 50)
print("CREATING TKINTER ROOT WINDOW")
print("=" * 50 + "\n")

if __name__ == "__main__":
    root = tk.Tk()
    print("✓ Tkinter root created")
    
    app = DebugApp(root)
    print("✓ DebugApp instance created")
    
    print("\n" + "=" * 50)
    print("ENTERING MAINLOOP")
    print("Window should appear now!")
    print("=" * 50 + "\n")
    
    print(">>> If window appears but is BLACK:")
    print("    - Problem: Tkinter cannot render widgets")
    print("    - Solution: Reinstall Python/Tkinter")
    print("")
    print(">>> If window appears with YELLOW background:")
    print("    - SUCCESS! Tkinter works!")
    print("    - Previous versions just used colors too dark")
    print("")
    
    root.mainloop()
    
    print("\n" + "=" * 50)
    print("MAINLOOP ENDED")
    print("=" * 50)
