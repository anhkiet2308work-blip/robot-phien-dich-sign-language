"""
🤖 RASPBERRY PI 4 - OPTIMIZED CONFIGURATION
Cấu hình tối ưu cho Raspberry Pi 4

Thêm vào đầu file sign_language_dynamic_v7.py
"""

import os
import platform

# ============================================================================
# RASPBERRY PI 4 DETECTION & OPTIMIZATION
# ============================================================================

def is_raspberry_pi():
    """Check if running on Raspberry Pi"""
    try:
        with open('/proc/cpuinfo', 'r') as f:
            return 'Raspberry Pi' in f.read()
    except:
        return False

def get_cpu_temp():
    """Get CPU temperature (Celsius)"""
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp = float(f.read()) / 1000.0
            return temp
    except:
        return None

def optimize_for_rpi():
    """Apply optimizations for Raspberry Pi"""
    if not is_raspberry_pi():
        return
    
    print("\n🔧 Detected Raspberry Pi - Applying optimizations...")
    
    # Limit TensorFlow threads (prevent CPU overload)
    os.environ['TF_NUM_INTRAOP_THREADS'] = '2'
    os.environ['TF_NUM_INTEROP_THREADS'] = '2'
    
    # Disable oneDNN optimizations (may cause issues on ARM)
    os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
    
    # Reduce TensorFlow verbosity
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
    
    # Check temperature
    temp = get_cpu_temp()
    if temp:
        print(f"🌡️  CPU Temperature: {temp:.1f}°C")
        if temp > 70:
            print("⚠️  WARNING: CPU temperature is high! Add cooling.")
        elif temp > 60:
            print("⚠️  CPU temperature elevated. Monitor during training.")
    
    print("✅ RPi optimizations applied\n")

# Apply optimizations at import time
optimize_for_rpi()


# ============================================================================
# RASPBERRY PI 4 OPTIMIZED SETTINGS
# ============================================================================

class RPi4Config:
    """Optimized configuration for Raspberry Pi 4"""
    
    # Reduced sequence length for faster processing
    SEQ_LEN = 20  # Instead of 30
    
    # Camera settings (lower resolution for better FPS)
    CAMERA_WIDTH = 640
    CAMERA_HEIGHT = 480
    CAMERA_FPS = 20  # Target FPS
    
    # Performance settings
    FRAME_SKIP = 2  # Process every 2nd frame for display
    RECOGNITION_COOLDOWN = 15  # Longer cooldown (frames)
    
    # Training settings
    EPOCHS = 30  # Reduced from 50
    BATCH_SIZE = 8  # Smaller batch
    
    # UI settings
    DISABLE_ANIMATIONS = False  # Set True for max performance
    CANVAS_SIZE = (640, 480)  # Smaller canvas
    
    # Memory settings
    CLEAR_SESSION_ON_TRAIN = True  # Clear Keras session after training
    
    @staticmethod
    def get_model_config():
        """Get optimized model architecture for RPi 4"""
        return {
            'lstm_units_1': 48,  # Reduced from 64
            'lstm_units_2': 24,  # Reduced from 32
            'dense_units': 24,   # Reduced from 32
            'dropout': 0.3
        }
    
    @staticmethod
    def print_info():
        """Print RPi 4 configuration info"""
        print("\n" + "="*70)
        print("🤖 RASPBERRY PI 4 OPTIMIZED CONFIGURATION")
        print("="*70)
        print(f"📊 Sequence Length: {RPi4Config.SEQ_LEN} frames")
        print(f"📷 Camera: {RPi4Config.CAMERA_WIDTH}x{RPi4Config.CAMERA_HEIGHT} @ {RPi4Config.CAMERA_FPS}fps")
        print(f"🎯 Recognition Cooldown: {RPi4Config.RECOGNITION_COOLDOWN} frames")
        print(f"🧠 Training Epochs: {RPi4Config.EPOCHS}")
        print(f"💾 Batch Size: {RPi4Config.BATCH_SIZE}")
        
        # Check system info
        import psutil
        ram = psutil.virtual_memory()
        print(f"\n💻 System Info:")
        print(f"  • RAM: {ram.total / (1024**3):.1f}GB total, {ram.available / (1024**3):.1f}GB available")
        print(f"  • Used: {ram.percent}%")
        
        temp = get_cpu_temp()
        if temp:
            print(f"  • CPU Temp: {temp:.1f}°C")
        
        print("="*70 + "\n")


# ============================================================================
# TEMPERATURE MONITORING
# ============================================================================

class TemperatureMonitor:
    """Monitor CPU temperature and warn if too hot"""
    
    def __init__(self, warning_temp=70, critical_temp=80):
        self.warning_temp = warning_temp
        self.critical_temp = critical_temp
        self.last_warning = 0
    
    def check(self):
        """Check temperature and return status"""
        temp = get_cpu_temp()
        if not temp:
            return None
        
        import time
        current_time = time.time()
        
        if temp >= self.critical_temp:
            if current_time - self.last_warning > 60:  # Warn every minute
                print(f"\n🔥 CRITICAL: CPU {temp:.1f}°C! Throttling may occur!")
                self.last_warning = current_time
            return 'critical'
        elif temp >= self.warning_temp:
            if current_time - self.last_warning > 300:  # Warn every 5 min
                print(f"\n⚠️  WARNING: CPU {temp:.1f}°C - Add cooling recommended")
                self.last_warning = current_time
            return 'warning'
        
        return 'ok'


# ============================================================================
# USAGE IN MAIN APP
# ============================================================================

"""
Thêm vào class UltimateSignLanguageApp:

class UltimateSignLanguageApp:
    # Use RPi4 config if on Raspberry Pi
    if is_raspberry_pi():
        SEQ_LEN = RPi4Config.SEQ_LEN
        EPOCHS = RPi4Config.EPOCHS
        BATCH_SIZE = RPi4Config.BATCH_SIZE
        
        # Initialize temperature monitor
        temp_monitor = TemperatureMonitor()
    else:
        SEQ_LEN = 30
        EPOCHS = 50
        BATCH_SIZE = 16
        temp_monitor = None
    
    def __init__(self, root):
        # Print config on RPi
        if is_raspberry_pi():
            RPi4Config.print_info()
        
        # ... rest of init ...
    
    def start_camera(self):
        # Use optimized settings on RPi
        if is_raspberry_pi():
            self.cap = cv2.VideoCapture(0)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, RPi4Config.CAMERA_WIDTH)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, RPi4Config.CAMERA_HEIGHT)
            self.cap.set(cv2.CAP_PROP_FPS, RPi4Config.CAMERA_FPS)
        else:
            self.cap = cv2.VideoCapture(0)
        
        # ... rest of code ...
    
    def train_model(self):
        # Check temperature before training
        if self.temp_monitor:
            status = self.temp_monitor.check()
            if status == 'critical':
                if not messagebox.askyesno("Nhiệt độ cao!", 
                    "CPU đang quá nóng! Tiếp tục train có thể gây throttling.\nTiếp tục?"):
                    return
        
        # Use RPi optimized model if on Pi
        if is_raspberry_pi():
            config = RPi4Config.get_model_config()
            self.model = keras.Sequential([
                keras.layers.LSTM(config['lstm_units_1'], return_sequences=True, 
                                 input_shape=(self.SEQ_LEN, 784)),
                keras.layers.Dropout(config['dropout']),
                keras.layers.LSTM(config['lstm_units_2']),
                keras.layers.Dropout(config['dropout']),
                keras.layers.Dense(config['dense_units'], activation='relu'),
                keras.layers.Dense(len(labels), activation='softmax')
            ])
        else:
            # Full model for PC
            # ... original model ...
        
        # ... rest of training ...
        
        # Clear session to free memory on RPi
        if is_raspberry_pi() and RPi4Config.CLEAR_SESSION_ON_TRAIN:
            import keras.backend as K
            K.clear_session()
"""


# ============================================================================
# STARTUP CHECK
# ============================================================================

def startup_check():
    """Run startup checks for Raspberry Pi"""
    if not is_raspberry_pi():
        print("ℹ️  Not running on Raspberry Pi - using default settings")
        return
    
    print("\n" + "="*70)
    print("🔍 RASPBERRY PI STARTUP CHECK")
    print("="*70)
    
    # Check Python version
    import sys
    print(f"✅ Python: {sys.version.split()[0]}")
    
    # Check TensorFlow
    try:
        import tensorflow as tf
        print(f"✅ TensorFlow: {tf.__version__}")
    except ImportError:
        print("❌ TensorFlow not installed!")
        return False
    
    # Check OpenCV
    try:
        import cv2
        print(f"✅ OpenCV: {cv2.__version__}")
    except ImportError:
        print("❌ OpenCV not installed!")
        return False
    
    # Check camera
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        print("✅ Camera detected")
        cap.release()
    else:
        print("⚠️  Camera not detected - check connections")
    
    # Check temperature
    temp = get_cpu_temp()
    if temp:
        print(f"✅ CPU Temperature: {temp:.1f}°C")
        if temp > 60:
            print("⚠️  CPU is warm - ensure adequate cooling during training")
    
    # Check RAM
    try:
        import psutil
        ram = psutil.virtual_memory()
        print(f"✅ RAM: {ram.available / (1024**3):.1f}GB available of {ram.total / (1024**3):.1f}GB")
        if ram.available < 1 * (1024**3):  # Less than 1GB
            print("⚠️  Low RAM - close other applications")
    except:
        pass
    
    print("="*70 + "\n")
    return True


# ============================================================================
# Run startup check
# ============================================================================
if __name__ == "__main__":
    startup_check()
    RPi4Config.print_info()
