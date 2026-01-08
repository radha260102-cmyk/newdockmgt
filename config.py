"""
Configuration file for Dock Management System
"""
import os
import json
import sys

# Get base directory - works for both development and PyInstaller executable
def get_base_dir():
    """Get the base directory for the application"""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        # For user files (config, models), use the executable's directory
        if hasattr(sys, '_MEIPASS'):
            # Onefile mode - use executable directory
            return os.path.dirname(sys.executable)
        else:
            # Directory mode - use executable directory
            return os.path.dirname(sys.executable)
    else:
        # Running as script
        return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller"""
    if getattr(sys, 'frozen', False):
        # PyInstaller: use executable directory for user-editable files
        base_path = os.path.dirname(sys.executable)
    else:
        # Development: use script directory
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# Model Configuration
MODEL_PATH = "models/best_doc4.pt"  # Path to your YOLO custom model (relative to BASE_DIR)
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
ZONE_CONFIG_FILE = "zone_config.json"  # Relative to BASE_DIR

# Zone Configuration (loaded from JSON or set manually)
ZONE_COORDINATES = None  # Will be loaded from JSON or set manually
PARKING_LINE_POINTS = None  # Will be loaded from JSON or set manually
PARKING_LINE_WAIT_TIME = 10  # Wait time in seconds before turning green after truck touches parking line
PARKING_LINE_GRACE_PERIOD = 50  # Number of consecutive "not touching" detections before resetting timer (prevents timer reset due to frame skipping or detection flicker)

# Human Zone Detection Configuration
# Which parts of human bounding box to check for parking zone inclusion
HUMAN_ZONE_CHECK_POINTS = {
    'top_left': True,      # Check top-left corner (x1, y1)
    'top_right': True,     # Check top-right corner (x2, y1)
    'bottom_right': True,  # Check bottom-right corner (x2, y2)
    'bottom_left': True,   # Check bottom-left corner (x1, y2)
    'center': True         # Check center point ((x1+x2)/2, (y1+y2)/2)
}

# Load zone configuration from JSON if it exists
def load_zone_config():
    """Load zone and parking line configuration from JSON file"""
    global ZONE_COORDINATES, PARKING_LINE_POINTS
    zone_config_path = get_resource_path(ZONE_CONFIG_FILE)
    if os.path.exists(zone_config_path):
        try:
            with open(zone_config_path, 'r') as f:
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
                    print(f"Loaded zone configuration from {zone_config_path}")
                    return True
        except Exception as e:
            print(f"Warning: Could not load zone config from {zone_config_path}: {e}")
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
MAX_FRAME_QUEUE_SIZE = 20  # Maximum frames in frame reading queue (prevents memory buildup) - Increased to reduce frame drops
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
#VIDEO_SOURCE = "rtsp://admin:india123@192.168.1.64:554/Streaming/Channels/101?transportmode=unicast&streamtype=main&transport=tcp"  # 0 for webcam, or path to video file
VIDEO_SOURCE = "C:/Users/yashp/OneDrive/Desktop/Final/newdockmgt/crop_3.mp4"  # 0 for webcam, or path to video file

# API Configuration for Audio/Visual Alerts (Speaker)
YELLOW_API_URL = "http://192.168.1.101/api/player?action=start&id=15&repeat=0&volume=2"  # API to call when YELLOW light glows
RED_API_URL = "http://192.168.1.101/api/player?action=start&id=16&repeat=0&volume=2"  # API to call when RED light glows
STOP_API_URL = "http://192.168.1.101/api/player?action=stop"  # API to call when GREEN light glows (stop all alerts)
SUCCESSFULLY_PARKED_API_URL = "http://192.168.1.101/api/player?action=start&id=17&repeat=0&volume=2"  # API to call when truck successfully parked (wait time completed and turned GREEN)
ENABLE_API_CALLS = True  # Enable/disable API calls

# Dock Status API Configuration
DOCK_STATUS_API_URL = "http://127.0.0.1:3041/dock1/status"  # API endpoint for dock status updates
ENABLE_DOCK_STATUS_API = True  # Enable/disable dock status API calls

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

# Settings Configuration File
SETTINGS_FILE = "settings.json"  # Relative to BASE_DIR

def load_settings():
    """Load settings from file (encrypted when running as exe)"""
    if getattr(sys, 'frozen', False):
        # Running as exe - try encrypted storage first
        from dock_utils.encrypted_storage import load_encrypted_data
        settings = load_encrypted_data(SETTINGS_FILE)
        if settings is None:
            # Fallback to plain JSON if encrypted file doesn't exist (migration)
            settings_path = get_resource_path(SETTINGS_FILE)
            if os.path.exists(settings_path):
                try:
                    with open(settings_path, 'r') as f:
                        settings = json.load(f)
                except:
                    return False
            else:
                return False
    else:
        # Development mode - load from plain JSON
        settings_path = get_resource_path(SETTINGS_FILE)
        if not os.path.exists(settings_path):
            return False
        try:
            with open(settings_path, 'r') as f:
                settings = json.load(f)
        except:
            return False
    
    if settings:
        try:
            # Update config values from settings file
            global VIDEO_SOURCE, MODEL_PATH, CONFIDENCE_THRESHOLD, USE_GPU, LICENSE_KEY
            global YELLOW_API_URL, RED_API_URL, STOP_API_URL, SUCCESSFULLY_PARKED_API_URL, ENABLE_API_CALLS
            global DOCK_STATUS_API_URL, ENABLE_DOCK_STATUS_API
            global ENABLE_PLC, PLC_HOST, PLC_PORT
            global PLC_GREEN_LIGHT_COILS, PLC_RED_LIGHT_COILS, PLC_YELLOW_LIGHT_COILS
            global PARKING_LINE_WAIT_TIME, PARKING_LINE_GRACE_PERIOD
            global BATCH_SIZE, BATCH_TIMEOUT, ENABLE_BATCH_PROCESSING
            global ENABLE_MULTITHREADING, FRAME_SKIP, SHOW_LICENSE_EXPIRY
            global HUMAN_ZONE_CHECK_POINTS
            
            if 'video_source' in settings:
                VIDEO_SOURCE = settings['video_source']
            if 'model_path' in settings:
                model_path = settings['model_path']
                # Resolve relative paths relative to base directory
                if not os.path.isabs(model_path):
                    MODEL_PATH = get_resource_path(model_path)
                else:
                    MODEL_PATH = model_path
            if 'confidence_threshold' in settings:
                CONFIDENCE_THRESHOLD = float(settings['confidence_threshold'])
            if 'use_gpu' in settings:
                USE_GPU = bool(settings['use_gpu'])
            if 'license_key' in settings:
                LICENSE_KEY = settings['license_key'] if settings['license_key'] else None
            if 'yellow_api_url' in settings:
                YELLOW_API_URL = settings['yellow_api_url']
            if 'red_api_url' in settings:
                RED_API_URL = settings['red_api_url']
            if 'stop_api_url' in settings:
                STOP_API_URL = settings['stop_api_url']
            if 'successfully_parked_api_url' in settings:
                SUCCESSFULLY_PARKED_API_URL = settings['successfully_parked_api_url']
            if 'enable_api_calls' in settings:
                ENABLE_API_CALLS = bool(settings['enable_api_calls'])
            if 'dock_status_api_url' in settings:
                DOCK_STATUS_API_URL = settings['dock_status_api_url']
            if 'enable_dock_status_api' in settings:
                ENABLE_DOCK_STATUS_API = bool(settings['enable_dock_status_api'])
            if 'enable_plc' in settings:
                ENABLE_PLC = bool(settings['enable_plc'])
            if 'plc_host' in settings:
                PLC_HOST = settings['plc_host']
            if 'plc_port' in settings:
                PLC_PORT = int(settings['plc_port'])
            if 'plc_green_coils' in settings:
                PLC_GREEN_LIGHT_COILS = settings['plc_green_coils']
            if 'plc_red_coils' in settings:
                PLC_RED_LIGHT_COILS = settings['plc_red_coils']
            if 'plc_yellow_coils' in settings:
                PLC_YELLOW_LIGHT_COILS = settings['plc_yellow_coils']
            if 'parking_line_wait_time' in settings:
                PARKING_LINE_WAIT_TIME = int(settings['parking_line_wait_time'])
            if 'parking_line_grace_period' in settings:
                PARKING_LINE_GRACE_PERIOD = int(settings['parking_line_grace_period'])
            if 'batch_size' in settings:
                BATCH_SIZE = int(settings['batch_size'])
            if 'batch_timeout' in settings:
                BATCH_TIMEOUT = float(settings['batch_timeout'])
            if 'enable_batch_processing' in settings:
                ENABLE_BATCH_PROCESSING = bool(settings['enable_batch_processing'])
            if 'enable_multithreading' in settings:
                ENABLE_MULTITHREADING = bool(settings['enable_multithreading'])
            if 'frame_skip' in settings:
                FRAME_SKIP = int(settings['frame_skip'])
            if 'show_license_expiry' in settings:
                SHOW_LICENSE_EXPIRY = bool(settings['show_license_expiry'])
            if 'human_zone_check_points' in settings:
                HUMAN_ZONE_CHECK_POINTS = settings['human_zone_check_points']
            
            if getattr(sys, 'frozen', False):
                print(f"Settings loaded from encrypted storage")
            else:
                print(f"Settings loaded from {SETTINGS_FILE}")
            return True
        except Exception as e:
            print(f"Warning: Could not load settings: {e}")
            return False
    
    return False

def save_settings_to_file(settings_dict):
    """Save settings dictionary to file (encrypted when running as exe)"""
    try:
        if getattr(sys, 'frozen', False):
            # Running as exe - use encrypted storage
            from dock_utils.encrypted_storage import save_encrypted_data
            return save_encrypted_data(settings_dict, SETTINGS_FILE)
        else:
            # Development mode - save as plain JSON
            settings_path = get_resource_path(SETTINGS_FILE)
            with open(settings_path, 'w') as f:
                json.dump(settings_dict, f, indent=4)
            print(f"Settings saved to {settings_path}")
            return True
    except Exception as e:
        print(f"Error saving settings: {e}")
        return False

def get_current_settings():
    """Get current settings as a dictionary"""
    # Load zone config if exists
    zone_coords = None
    parking_line_points = None
    zone_config_path = get_resource_path(ZONE_CONFIG_FILE)
    if os.path.exists(zone_config_path):
        try:
            with open(zone_config_path, 'r') as f:
                zone_config = json.load(f)
                zone_coords = zone_config.get('zone_coordinates', [])
                parking_line_points = zone_config.get('parking_line_points', [])
        except:
            pass
    
    return {
        'video_source': VIDEO_SOURCE,
        'model_path': MODEL_PATH,
        'confidence_threshold': CONFIDENCE_THRESHOLD,
        'use_gpu': USE_GPU,
        'license_key': LICENSE_KEY or '',
        'yellow_api_url': YELLOW_API_URL,
        'red_api_url': RED_API_URL,
        'stop_api_url': STOP_API_URL,
        'successfully_parked_api_url': SUCCESSFULLY_PARKED_API_URL,
        'enable_api_calls': ENABLE_API_CALLS,
        'dock_status_api_url': DOCK_STATUS_API_URL,
        'enable_dock_status_api': ENABLE_DOCK_STATUS_API,
        'enable_plc': ENABLE_PLC,
        'plc_host': PLC_HOST,
        'plc_port': PLC_PORT,
        'plc_green_coils': PLC_GREEN_LIGHT_COILS,
        'plc_red_coils': PLC_RED_LIGHT_COILS,
        'plc_yellow_coils': PLC_YELLOW_LIGHT_COILS,
        'parking_line_wait_time': PARKING_LINE_WAIT_TIME,
        'parking_line_grace_period': PARKING_LINE_GRACE_PERIOD,
        'batch_size': BATCH_SIZE,
        'batch_timeout': BATCH_TIMEOUT,
        'enable_batch_processing': ENABLE_BATCH_PROCESSING,
        'enable_multithreading': ENABLE_MULTITHREADING,
        'frame_skip': FRAME_SKIP,
        'zone_coordinates': zone_coords,
        'parking_line_points': parking_line_points,
        'human_zone_check_points': HUMAN_ZONE_CHECK_POINTS
    }

def update_settings_from_dict(settings_dict):
    """Update config values from a dictionary (used by settings UI)"""
    global VIDEO_SOURCE, MODEL_PATH, CONFIDENCE_THRESHOLD, USE_GPU, LICENSE_KEY
    global YELLOW_API_URL, RED_API_URL, STOP_API_URL, ENABLE_API_CALLS
    global ENABLE_PLC, PLC_HOST, PLC_PORT
    global PLC_GREEN_LIGHT_COILS, PLC_RED_LIGHT_COILS, PLC_YELLOW_LIGHT_COILS
    global PARKING_LINE_WAIT_TIME, PARKING_LINE_GRACE_PERIOD
    global BATCH_SIZE, BATCH_TIMEOUT, ENABLE_BATCH_PROCESSING
    global ENABLE_MULTITHREADING, FRAME_SKIP, SHOW_LICENSE_EXPIRY
    global HUMAN_ZONE_CHECK_POINTS
    
    if 'video_source' in settings_dict:
        VIDEO_SOURCE = settings_dict['video_source']
    if 'model_path' in settings_dict:
        MODEL_PATH = settings_dict['model_path']
    if 'confidence_threshold' in settings_dict:
        CONFIDENCE_THRESHOLD = float(settings_dict['confidence_threshold'])
    if 'use_gpu' in settings_dict:
        USE_GPU = bool(settings_dict['use_gpu'])
    if 'license_key' in settings_dict:
        LICENSE_KEY = settings_dict['license_key'] if settings_dict['license_key'] else None
    if 'yellow_api_url' in settings_dict:
        YELLOW_API_URL = settings_dict['yellow_api_url']
    if 'red_api_url' in settings_dict:
        RED_API_URL = settings_dict['red_api_url']
    if 'stop_api_url' in settings_dict:
        STOP_API_URL = settings_dict['stop_api_url']
    if 'successfully_parked_api_url' in settings_dict:
        SUCCESSFULLY_PARKED_API_URL = settings_dict['successfully_parked_api_url']
    if 'enable_api_calls' in settings_dict:
        ENABLE_API_CALLS = bool(settings_dict['enable_api_calls'])
    if 'dock_status_api_url' in settings_dict:
        DOCK_STATUS_API_URL = settings_dict['dock_status_api_url']
    if 'enable_dock_status_api' in settings_dict:
        ENABLE_DOCK_STATUS_API = bool(settings_dict['enable_dock_status_api'])
    if 'enable_plc' in settings_dict:
        ENABLE_PLC = bool(settings_dict['enable_plc'])
    if 'plc_host' in settings_dict:
        PLC_HOST = settings_dict['plc_host']
    if 'plc_port' in settings_dict:
        PLC_PORT = int(settings_dict['plc_port'])
    if 'plc_green_coils' in settings_dict:
        PLC_GREEN_LIGHT_COILS = settings_dict['plc_green_coils']
    if 'plc_red_coils' in settings_dict:
        PLC_RED_LIGHT_COILS = settings_dict['plc_red_coils']
    if 'plc_yellow_coils' in settings_dict:
        PLC_YELLOW_LIGHT_COILS = settings_dict['plc_yellow_coils']
    if 'parking_line_wait_time' in settings_dict:
        PARKING_LINE_WAIT_TIME = int(settings_dict['parking_line_wait_time'])
    if 'parking_line_grace_period' in settings_dict:
        PARKING_LINE_GRACE_PERIOD = int(settings_dict['parking_line_grace_period'])
    if 'batch_size' in settings_dict:
        BATCH_SIZE = int(settings_dict['batch_size'])
    if 'batch_timeout' in settings_dict:
        BATCH_TIMEOUT = float(settings_dict['batch_timeout'])
    if 'enable_batch_processing' in settings_dict:
        ENABLE_BATCH_PROCESSING = bool(settings_dict['enable_batch_processing'])
    if 'enable_multithreading' in settings_dict:
        ENABLE_MULTITHREADING = bool(settings_dict['enable_multithreading'])
    if 'frame_skip' in settings_dict:
        FRAME_SKIP = int(settings_dict['frame_skip'])
    if 'show_license_expiry' in settings_dict:
        SHOW_LICENSE_EXPIRY = bool(settings_dict['show_license_expiry'])
    if 'human_zone_check_points' in settings_dict:
        HUMAN_ZONE_CHECK_POINTS = settings_dict['human_zone_check_points']
    
    # Save zone configuration if provided
    if 'zone_coordinates' in settings_dict or 'parking_line_points' in settings_dict:
        try:
            zone_config_path = get_resource_path(ZONE_CONFIG_FILE)
            zone_config = {}
            if os.path.exists(zone_config_path):
                with open(zone_config_path, 'r') as f:
                    zone_config = json.load(f)
            if 'zone_coordinates' in settings_dict:
                zone_config['zone_coordinates'] = settings_dict['zone_coordinates']
            if 'parking_line_points' in settings_dict:
                zone_config['parking_line_points'] = settings_dict['parking_line_points']
            with open(zone_config_path, 'w') as f:
                json.dump(zone_config, f, indent=4)
            # Reload zone config
            load_zone_config()
        except Exception as e:
            print(f"Warning: Could not save zone configuration: {e}")

# License Configuration
# License key can be set here, via LICENSE_KEY environment variable, or loaded from cache
# Set to None or empty string to load from cache only
_license_key_env = os.getenv('LICENSE_KEY', "488668-B5FFC8-108E83-B72C63-201295-V3")
LICENSE_KEY = _license_key_env if _license_key_env else None
LICENSE_CACHE_FILE = "license_cache.json"  # File to store license data for offline use
SHOW_LICENSE_EXPIRY = True  # Show/hide the free license expiry warning text
