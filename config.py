"""
Configuration file for Dock Management System
"""
import os
import json

# Model Configuration
MODEL_PATH = "models/best.pt"  # Path to your YOLO custom model
CONFIDENCE_THRESHOLD = 0.5  # Detection confidence threshold
USE_GPU = True  # Use GPU (CUDA) if available, fallback to CPU if not
DEVICE = None  # Auto-detect: 'cuda' or 'cpu' (None = auto)

# Class IDs (based on your YOLO model classes)
CLASS_IDS = {
    'person': 0,     # Class 0 is person
    'forklift': 1,   # Class 1 is forklift (ignored)
    'truck': 2       # Class 2 is truck
}

# Zone Configuration File
ZONE_CONFIG_FILE = "zone_config.json"

# Zone Configuration (loaded from JSON or set manually)
ZONE_COORDINATES = None  # Will be loaded from JSON or set manually
PARKING_LINE_POINTS = None  # Will be loaded from JSON or set manually
PARKING_LINE_WAIT_TIME = 10  # Wait time in seconds before turning green after truck touches parking line
PARKING_LINE_GRACE_PERIOD = 50  # Number of consecutive "not touching" detections before resetting timer (prevents timer reset due to frame skipping or detection flicker)

# Load zone configuration from JSON if it exists
def load_zone_config():
    """Load zone and parking line configuration from JSON file"""
    global ZONE_COORDINATES, PARKING_LINE_POINTS
    if os.path.exists(ZONE_CONFIG_FILE):
        try:
            with open(ZONE_CONFIG_FILE, 'r') as f:
                config_data = json.load(f)
                # Convert lists to tuples for zone coordinates
                zone_data = config_data.get('zone_coordinates')
                if zone_data:
                    ZONE_COORDINATES = [tuple(point) if isinstance(point, list) else point for point in zone_data]
                # Convert lists to tuples for parking line points
                line_data = config_data.get('parking_line_points')
                if line_data:
                    PARKING_LINE_POINTS = [tuple(point) if isinstance(point, list) else point for point in line_data]
                if ZONE_COORDINATES or PARKING_LINE_POINTS:
                    print(f"Loaded zone configuration from {ZONE_CONFIG_FILE}")
                    return True
        except Exception as e:
            print(f"Warning: Could not load zone config from {ZONE_CONFIG_FILE}: {e}")
    return False

# Auto-load on import
load_zone_config()

# UI Configuration
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 800
SIGNAL_SIZE = 100
UPDATE_INTERVAL = 100  # milliseconds
FRAME_SKIP = 0  # Process every Nth frame (1 = every frame, 2 = every 2nd frame, etc.) - Higher = faster but less smooth

# Multi-threading Configuration
ENABLE_MULTITHREADING = True  # Enable separate threads for frame reading, detection processing, and UI updates
MAX_FRAME_QUEUE_SIZE = 5  # Maximum frames in frame reading queue (prevents memory buildup) - Increased to reduce frame drops
MAX_RESULT_QUEUE_SIZE = 3  # Maximum results in detection result queue - Increased to reduce frame drops

# Batch Processing Configuration
ENABLE_BATCH_PROCESSING = True  # Enable batch processing to increase FPS (works with or without multi-threading)
BATCH_SIZE = 2  # Number of frames to process together (1 = no batching, 2-8 recommended for GPU, 1-2 for CPU) - Reduced to reduce latency
BATCH_TIMEOUT = 0.005  # Maximum time (seconds) to wait for collecting a batch before processing available frames - Reduced to reduce latency

# Validate batch processing configuration
if ENABLE_BATCH_PROCESSING and BATCH_SIZE < 1:
    print("Warning: BATCH_SIZE must be >= 1. Setting to 1.")
    BATCH_SIZE = 1

# Video Source
VIDEO_SOURCE = "rtsp://admin:india123@192.168.1.64:554/Streaming/Channels/101?transportmode=unicast&streamtype=main&transport=tcp"  # 0 for webcam, or path to video file
#VIDEO_SOURCE = "3.mp4"  # 0 for webcam, or path to video file

# API Configuration for Audio/Visual Alerts
YELLOW_API_URL = "http://192.168.1.101/api/player?action=start&id=15&repeat=0&volume=2"  # API to call when YELLOW light glows
RED_API_URL = "http://192.168.1.101/api/player?action=start&id=16&repeat=0&volume=2"  # API to call when RED light glows
STOP_API_URL = "http://192.168.1.101/api/player?action=stop"  # API to call when GREEN light glows (stop all alerts)
ENABLE_API_CALLS = True  # Enable/disable API calls

# PLC Configuration (Modbus TCP)
ENABLE_PLC = True  # Enable/disable PLC control
PLC_HOST = "127.0.0.1"  # PLC Modbus TCP host
PLC_PORT = 502  # PLC Modbus TCP port
PLC_AUTO_OPEN = True  # Automatically open connection on initialization
PLC_AUTO_CLOSE = True  # Automatically close connection on shutdown
PLC_COIL_START_ADDRESS = 0  # Starting address for coils (adjust based on your PLC)
# Coil configurations: [coil0, coil1, coil2, coil3, coil4, coil5, coil6, coil7]
PLC_GREEN_LIGHT_COILS = [True, False, False, False, False, False, False, False]
PLC_RED_LIGHT_COILS = [False, True, False, False, False, False, False, False]
PLC_YELLOW_LIGHT_COILS = [False, False, True, False, False, False, False, False]