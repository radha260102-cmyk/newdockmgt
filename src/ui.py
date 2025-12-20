"""
UI Module for Dock Management System
Provides a simple GUI with red/yellow/green signal indicators
"""
import tkinter as tk
from tkinter import ttk, messagebox
import cv2
from PIL import Image, ImageTk
import threading
import queue
import time
import json
import config


class DockManagementUI:
    """Main UI class for dock management system"""
    
    def __init__(self, detector, dock_manager, video_source=None):
        """
        Initialize UI
        Args:
            detector: YOLODetector instance
            dock_manager: DockManager instance
            video_source: Video source (0 for webcam or file path)
        """
        self.detector = detector
        self.dock_manager = dock_manager
        self.video_source = video_source or config.VIDEO_SOURCE
        
        # UI Components
        self.root = None
        self.video_label = None
        self.red_light_canvas = None
        self.yellow_light_canvas = None
        self.green_light_canvas = None
        self.status_label = None
        self.license_expiry_label = None
        self.thread_fps_label = None
        self.info_text = None
        
        # Video capture
        self.cap = None
        self.is_running = False
        self.current_frame = None
        
        # Store last detection results for frame skipping (prediction/interpolation)
        self.last_detections = None
        self.last_detection_summary = None
        self.last_state = "UNKNOWN"
        
        # FPS calculation
        self.fps_start_time = None
        self.fps_frame_count = 0
        self.current_fps = 0.0
        self.fps_update_interval = 1.0  # Update FPS every 1 second
        
        # Individual thread FPS tracking
        self.frame_reading_fps = 0.0
        self.detection_fps = 0.0
        self.ui_update_fps = 0.0
        self.fps_lock = threading.Lock()  # Thread-safe FPS updates
        
        # Multi-threading support
        self.enable_multithreading = config.ENABLE_MULTITHREADING
        self.frame_queue = None  # Queue for frames from reading thread
        self.result_queue = None  # Queue for detection results
        self.frame_reading_thread = None
        self.detection_thread = None
        self.ui_update_thread = None
        
        # Batch processing support
        self.enable_batch_processing = config.ENABLE_BATCH_PROCESSING
        self.batch_size = config.BATCH_SIZE if self.enable_batch_processing else 1
        
        # Signal colors
        self.colors = {
            'RED': '#FF0000',
            'YELLOW': '#FFFF00',
            'GREEN': '#00FF00',
            'OFF': '#808080'
        }
        
        # Error tracking and monitoring
        self.error_stats = {
            'frame_queue_full_count': 0,
            'result_queue_full_count': 0,
            'dropped_frames_count': 0,
            'detection_errors': [],
            'video_read_errors': 0,
            'last_error': None,
            'last_error_time': None
        }
        self.error_lock = threading.Lock()  # Thread-safe error tracking
        
        self.setup_ui()
        # Auto-start video when UI is ready
        self.root.after(100, self.start_detection)
    
    def setup_ui(self):
        """Setup the user interface"""
        self.root = tk.Tk()
        self.root.title("Dock Management System")
        # Larger window for side-by-side layout
        self.root.geometry("1400x800")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Configure root grid
        self.root.columnconfigure(0, weight=2)  # Video takes 2/3 of space
        self.root.columnconfigure(1, weight=1)  # Status/Info takes 1/3 of space
        self.root.rowconfigure(0, weight=1)
        
        # Main container - no padding for full screen usage
        main_frame = ttk.Frame(self.root)
        main_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(0, weight=2)  # Video column
        main_frame.columnconfigure(1, weight=1)  # Status/Info column
        main_frame.rowconfigure(0, weight=1)
        
        # ========== LEFT SIDE: VIDEO FEED ==========
        video_frame = ttk.LabelFrame(main_frame, text="Video Feed", padding="5")
        video_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        video_frame.columnconfigure(0, weight=1)
        video_frame.rowconfigure(0, weight=1)
        
        self.video_label = tk.Label(video_frame, bg="black")
        self.video_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # ========== RIGHT SIDE: STATUS AND DETECTION INFO ==========
        right_panel = ttk.Frame(main_frame)
        right_panel.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(0, weight=1)  # Status frame
        right_panel.rowconfigure(1, weight=2)  # Detection info frame (takes more space)
        
        # ========== STATUS BOX (TOP RIGHT) ==========
        status_frame = ttk.LabelFrame(right_panel, text="Status", padding="10")
        status_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))
        status_frame.columnconfigure(0, weight=1)
        
        # Signal lights container
        signal_container = ttk.Frame(status_frame)
        signal_container.pack(pady=10)
        
        ttk.Label(signal_container, text="Dock Status", font=("Arial", 14, "bold")).pack(pady=(0, 15))
        
        # Three signal lights (Red, Yellow, Green)
        lights_frame = ttk.Frame(signal_container)
        lights_frame.pack()
        
        # Red light with label
        red_container = ttk.Frame(lights_frame)
        red_container.pack(side=tk.LEFT, padx=10)
        self.red_light_canvas = tk.Canvas(
            red_container,
            width=80,
            height=80,
            bg="white",
            highlightthickness=2,
            highlightbackground="black"
        )
        self.red_light_canvas.pack()
        ttk.Label(red_container, text="RED", font=("Arial", 10, "bold")).pack(pady=(5, 0))
        
        # Yellow light with label
        yellow_container = ttk.Frame(lights_frame)
        yellow_container.pack(side=tk.LEFT, padx=10)
        self.yellow_light_canvas = tk.Canvas(
            yellow_container,
            width=80,
            height=80,
            bg="white",
            highlightthickness=2,
            highlightbackground="black"
        )
        self.yellow_light_canvas.pack()
        ttk.Label(yellow_container, text="YELLOW", font=("Arial", 10, "bold")).pack(pady=(5, 0))
        
        # Green light with label
        green_container = ttk.Frame(lights_frame)
        green_container.pack(side=tk.LEFT, padx=10)
        self.green_light_canvas = tk.Canvas(
            green_container,
            width=80,
            height=80,
            bg="white",
            highlightthickness=2,
            highlightbackground="black"
        )
        self.green_light_canvas.pack()
        ttk.Label(green_container, text="GREEN", font=("Arial", 10, "bold")).pack(pady=(5, 0))
        
        # Initialize all lights to OFF
        self.update_signal_lights("OFF")
        
        # Status label
        self.status_label = ttk.Label(
            status_frame,
            text="Status: Initializing...", 
            font=("Arial", 11, "bold")
        )
        self.status_label.pack(pady=10)
        
        # Wait time label (for parking line countdown)
        self.wait_time_label = ttk.Label(
            status_frame,
            text="",
            font=("Arial", 10),
            foreground="orange"
        )
        self.wait_time_label.pack(pady=5)
        
        # FPS label (overall)
        self.fps_label = ttk.Label(
            status_frame,
            text="FPS: 0.0",
            font=("Arial", 9),
            foreground="blue"
        )
        self.fps_label.pack(pady=2)
        
        # Individual thread FPS labels (only show if multithreading enabled) - compact flex format
        if self.enable_multithreading:
            # Single label with all FPS in one line
            self.thread_fps_label = ttk.Label(
                status_frame,
                text="Thread FPS: Read=0.0 | Detect=0.0 | UI=0.0",
                font=("Arial", 8),
                foreground="green"
            )
            self.thread_fps_label.pack(pady=1)
        
        # Device info label (GPU/CPU)
        import torch
        device_info = "GPU" if torch.cuda.is_available() else "CPU"
        if torch.cuda.is_available():
            device_info += f" ({torch.cuda.get_device_name(0)})"
        self.device_label = ttk.Label(
            status_frame,
            text=f"Device: {device_info}",
            font=("Arial", 8),
            foreground="green" if torch.cuda.is_available() else "gray"
        )
        self.device_label.pack(pady=2)
        
        # License expiry label
        self.license_expiry_label = ttk.Label(
            status_frame,
            text="",
            font=("Arial", 8),
            foreground="red"
        )
        self.license_expiry_label.pack(pady=2)
        self.update_license_expiry_display()
        
        # Settings button
        settings_button = ttk.Button(
            status_frame,
            text="⚙ Settings",
            command=self.open_settings
        )
        settings_button.pack(pady=10)
        
        # ========== DETECTION INFO (BOTTOM RIGHT) ==========
        info_frame = ttk.LabelFrame(right_panel, text="Detection Info", padding="5")
        info_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 0))
        info_frame.columnconfigure(0, weight=1)
        info_frame.rowconfigure(0, weight=1)
        
        self.info_text = tk.Text(info_frame, wrap=tk.WORD, font=("Arial", 9))
        self.info_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        scrollbar = ttk.Scrollbar(info_frame, orient=tk.VERTICAL, command=self.info_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.info_text.config(yscrollcommand=scrollbar.set)
        
    def update_signal_lights(self, state):
        """
        Update signal indicator lights (all three: red, yellow, green)
        Args:
            state: 'RED', 'YELLOW', 'GREEN', or 'OFF'
        """
        # Helper function to draw a light
        def draw_light(canvas, color, is_active):
            canvas.delete("all")
            margin = 8
            if is_active:
                # Active light - bright color
                fill_color = color
                outline_color = "black"
                outline_width = 3
            else:
                # Inactive light - dim gray
                fill_color = "#404040"  # Dark gray
                outline_color = "#808080"
                outline_width = 2
            
            canvas.create_oval(
                margin, margin,
                80 - margin,
                80 - margin,
                fill=fill_color,
                outline=outline_color,
                width=outline_width
            )
            
            # Add glow effect for active light
            if is_active:
                canvas.create_oval(
                    margin + 5, margin + 5,
                    80 - margin - 5,
                    80 - margin - 5,
                    fill="",
                    outline=fill_color,
                    width=1
                )
        
        # Update each light based on state
        draw_light(self.red_light_canvas, "#FF0000", state == "RED")
        draw_light(self.yellow_light_canvas, "#FFFF00", state == "YELLOW")
        draw_light(self.green_light_canvas, "#00FF00", state == "GREEN")
    
    def update_signal(self, state):
        """Wrapper for backward compatibility"""
        self.update_signal_lights(state)
    
    def update_license_expiry_display(self):
        """Update license expiry label with days remaining"""
        # Check if license expiry display is enabled in settings
        if not config.SHOW_LICENSE_EXPIRY:
            self.license_expiry_label.config(text="")
            return
        
        try:
            import json
            import os
            from datetime import datetime, timezone
            
            cache_file = config.LICENSE_CACHE_FILE
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                
                expiry_date = cache_data.get('expiry_date')
                if expiry_date:
                    try:
                        expiry_dt = datetime.fromisoformat(expiry_date.replace('Z', '+00:00'))
                        now = datetime.now(timezone.utc)
                        days_left = (expiry_dt - now).days
                        
                        if days_left > 0:
                            self.license_expiry_label.config(
                                text=f"Free licence will be expired in {days_left} days",
                                foreground="red"
                            )
                        elif days_left == 0:
                            self.license_expiry_label.config(
                                text="Free licence will be expired today",
                                foreground="red"
                            )
                        else:
                            self.license_expiry_label.config(
                                text=f"Free licence expired {abs(days_left)} days ago",
                                foreground="red"
                            )
                        return
                    except Exception as e:
                        print(f"Warning: Could not parse expiry date: {e}")
            
            # No expiry date or cache file not found
            self.license_expiry_label.config(text="", foreground="red")
            
        except Exception as e:
            print(f"Warning: Could not update license expiry display: {e}")
            self.license_expiry_label.config(text="", foreground="red")
    
    def track_error(self, error_type, message=None):
        """
        Track errors in a thread-safe manner
        Auto-resets counters when they reach 1000 to prevent unbounded growth in 24/7 operation
        Args:
            error_type: 'frame_queue_full', 'result_queue_full', 'dropped_frame', 
                       'detection_error', 'video_read_error', 'general_error'
            message: Optional error message
        """
        import time
        MAX_COUNTER_VALUE = 1000  # Reset counters when they reach this value
        
        with self.error_lock:
            # Increment appropriate counter
            if error_type == 'frame_queue_full':
                self.error_stats['frame_queue_full_count'] += 1
            elif error_type == 'result_queue_full':
                self.error_stats['result_queue_full_count'] += 1
            elif error_type == 'dropped_frame':
                self.error_stats['dropped_frames_count'] += 1
            elif error_type == 'detection_error':
                if message:
                    # Keep only last 10 errors
                    self.error_stats['detection_errors'].append(str(message))
                    if len(self.error_stats['detection_errors']) > 10:
                        self.error_stats['detection_errors'].pop(0)
            elif error_type == 'video_read_error':
                self.error_stats['video_read_errors'] += 1
            
            # Check if any counter reached max value and reset all counters
            if (self.error_stats['frame_queue_full_count'] >= MAX_COUNTER_VALUE or
                self.error_stats['result_queue_full_count'] >= MAX_COUNTER_VALUE or
                self.error_stats['dropped_frames_count'] >= MAX_COUNTER_VALUE or
                self.error_stats['video_read_errors'] >= MAX_COUNTER_VALUE):
                # Reset all counters to prevent unbounded growth
                print(f"Info: Error counters reached {MAX_COUNTER_VALUE}, resetting counters for 24/7 operation")
                self.error_stats['frame_queue_full_count'] = 0
                self.error_stats['result_queue_full_count'] = 0
                self.error_stats['dropped_frames_count'] = 0
                self.error_stats['video_read_errors'] = 0
                # Keep detection_errors list but clear if too large
                if len(self.error_stats['detection_errors']) > 10:
                    self.error_stats['detection_errors'] = self.error_stats['detection_errors'][-10:]
            
            # Update last error
            if message:
                self.error_stats['last_error'] = f"{error_type}: {message}"
            else:
                self.error_stats['last_error'] = error_type
            self.error_stats['last_error_time'] = time.strftime("%H:%M:%S")
    
    def reset_error_stats(self):
        """Reset all error statistics"""
        with self.error_lock:
            self.error_stats = {
                'frame_queue_full_count': 0,
                'result_queue_full_count': 0,
                'dropped_frames_count': 0,
                'detection_errors': [],
                'video_read_errors': 0,
                'last_error': None,
                'last_error_time': None
            }
    
    def update_info(self, detection_summary, state):
        """Update information text in compact columnar format"""
        self.info_text.delete(1.0, tk.END)
        
        # Header
        info = f"{'='*60}\n"
        info += f"{'DETECTION SUMMARY':^60}\n"
        info += f"{'='*60}\n"
        info += f"{'Truck Present':<20}| {detection_summary['truck_present']}\n"
        info += f"{'Truck Count':<20}| {detection_summary['truck_count']}\n"
        info += f"{'Human Present':<20}| {detection_summary['human_present']}\n"
        info += f"{'Human Count':<20}| {detection_summary['human_count']}\n"
        
        # Timer info
        remaining_wait = self.dock_manager.get_parking_wait_remaining()
        if remaining_wait is not None:
            info += f"{'Timer (s)':<20}| {remaining_wait}\n"
        
        info += f"{'-'*60}\n"
        
        # Trucks and Humans in compact format
        if detection_summary['trucks']:
            info += f"{'TRUCKS':^60}\n"
            for i, truck in enumerate(detection_summary['trucks']):
                truck_bbox = truck['bbox']
                in_zone = self.dock_manager.is_truck_in_zone(truck_bbox) if self.dock_manager.zone_coordinates else False
                touching, _ = self.dock_manager.is_truck_touching_parking_line_debug(truck_bbox) if self.dock_manager.zone_coordinates else (False, None)
                info += f"  T{i+1}: Conf={truck['confidence']:.2f} | InZone={in_zone} | Touch={touching}\n"
        
        if detection_summary['humans']:
            info += f"{'PERSONS':^60}\n"
            for i, human in enumerate(detection_summary['humans']):
                info += f"  P{i+1}: Conf={human['confidence']:.2f}\n"
        
        info += f"{'-'*60}\n"
        
        # System Status in columns
        info += f"{'SYSTEM STATUS':^60}\n"
        info += f"{'-'*60}\n"
        
        # Queue status (if multithreading is enabled)
        if self.enable_multithreading and self.frame_queue is not None and self.result_queue is not None:
            frame_queue_size = self.frame_queue.qsize()
            frame_queue_max = config.MAX_FRAME_QUEUE_SIZE
            result_queue_size = self.result_queue.qsize()
            result_queue_max = config.MAX_RESULT_QUEUE_SIZE
            
            frame_status = f"{frame_queue_size}/{frame_queue_max}"
            if frame_queue_size >= frame_queue_max:
                frame_status += " 🔴"
            elif frame_queue_size >= frame_queue_max * 0.8:
                frame_status += " ⚠️"
            else:
                frame_status += " ✓"
            
            result_status = f"{result_queue_size}/{result_queue_max}"
            if result_queue_size >= result_queue_max:
                result_status += " 🔴"
            elif result_queue_size >= result_queue_max * 0.8:
                result_status += " ⚠️"
            else:
                result_status += " ✓"
            
            info += f"{'Frame Queue':<20}| {frame_status}\n"
            info += f"{'Result Queue':<20}| {result_status}\n"
        
        # Thread status
        if self.enable_multithreading:
            frame_thread_alive = self.frame_reading_thread and self.frame_reading_thread.is_alive()
            detection_thread_alive = self.detection_thread and self.detection_thread.is_alive()
            ui_thread_alive = self.ui_update_thread and self.ui_update_thread.is_alive()
            
            thread_status = f"{'Frame':<10}| {'✓' if frame_thread_alive else '✗'} | "
            thread_status += f"{'Detect':<10}| {'✓' if detection_thread_alive else '✗'} | "
            thread_status += f"{'UI':<10}| {'✓' if ui_thread_alive else '✗'}"
            info += f"{'Threads':<20}| {thread_status}\n"
        
        info += f"{'-'*60}\n"
        
        # Error statistics in compact format
        with self.error_lock:
            error_stats = self.error_stats.copy()
        
        has_errors = (error_stats['frame_queue_full_count'] > 0 or 
                     error_stats['result_queue_full_count'] > 0 or 
                     error_stats['dropped_frames_count'] > 0 or 
                     error_stats['video_read_errors'] > 0 or 
                     len(error_stats['detection_errors']) > 0)
        
        if has_errors:
            info += f"{'ERROR STATS':^60}\n"
            info += f"{'-'*60}\n"
            
            error_line = []
            if error_stats['frame_queue_full_count'] > 0:
                error_line.append(f"FQFull:{error_stats['frame_queue_full_count']}")
            if error_stats['result_queue_full_count'] > 0:
                error_line.append(f"RQFull:{error_stats['result_queue_full_count']}")
            if error_stats['dropped_frames_count'] > 0:
                error_line.append(f"Drop:{error_stats['dropped_frames_count']}")
            if error_stats['video_read_errors'] > 0:
                error_line.append(f"VidErr:{error_stats['video_read_errors']}")
            if len(error_stats['detection_errors']) > 0:
                error_line.append(f"DetErr:{len(error_stats['detection_errors'])}")
            
            if error_line:
                info += f"{'Errors':<20}| {' | '.join(error_line)}\n"
            
            # Last error
            if error_stats['last_error']:
                last_err = error_stats['last_error'][:50]  # Truncate long errors
                if error_stats['last_error_time']:
                    info += f"{'Last Error':<20}| {last_err} ({error_stats['last_error_time']})\n"
                else:
                    info += f"{'Last Error':<20}| {last_err}\n"
            
            # Recent errors (compact)
            if len(error_stats['detection_errors']) > 0:
                recent_errors = error_stats['detection_errors'][-2:]  # Last 2 errors
                for err in recent_errors:
                    err_short = err[:55] if len(err) > 55 else err
                    info += f"{'  →':<20}| {err_short}\n"
        else:
            info += f"{'Errors':<20}| ✓ None\n"
        
        info += f"{'='*60}\n"
        
        self.info_text.insert(1.0, info)
    
    def start_detection(self):
        """Start video detection"""
        try:
            self.cap = cv2.VideoCapture(self.video_source)
            if not self.cap.isOpened():
                messagebox.showerror("Error", "Could not open video source")
                return
            
            # Zones and parking lines are already configured on cropped frames
            # So they're already in the cropped coordinate system - no adjustment needed
            # The zones loaded from config are already relative to the cropped frame size
            
            self.is_running = True
            # Buttons removed, so no need to update button states
            
            if self.enable_multithreading:
                # Multi-threaded mode: separate threads for reading, detection, and UI updates
                self.frame_queue = queue.Queue(maxsize=config.MAX_FRAME_QUEUE_SIZE)
                self.result_queue = queue.Queue(maxsize=config.MAX_RESULT_QUEUE_SIZE)
                
                # Start frame reading thread
                self.frame_reading_thread = threading.Thread(target=self.frame_reading_loop, daemon=True)
                self.frame_reading_thread.start()
                
                # Start detection processing thread
                self.detection_thread = threading.Thread(target=self.detection_processing_loop, daemon=True)
                self.detection_thread.start()
                
                # Start UI update thread
                self.ui_update_thread = threading.Thread(target=self.ui_update_loop, daemon=True)
                self.ui_update_thread.start()
            else:
                # Single-threaded mode: traditional approach
                self.detection_thread = threading.Thread(target=self.detection_loop, daemon=True)
                self.detection_thread.start()
            
        except Exception as e:
            error_msg = f"Failed to start detection: {str(e)}"
            self.track_error('general_error', error_msg)
            messagebox.showerror("Error", error_msg)
    
    def stop_detection(self):
        """Stop video detection"""
        self.is_running = False
        
        # Wait for threads to finish
        if self.enable_multithreading:
            # Clear queues to unblock threads
            if self.frame_queue:
                try:
                    while not self.frame_queue.empty():
                        self.frame_queue.get_nowait()
                except queue.Empty:
                    pass
            
            if self.result_queue:
                try:
                    while not self.result_queue.empty():
                        self.result_queue.get_nowait()
                except queue.Empty:
                    pass
            
            # Wait for threads to finish (with timeout)
            if self.frame_reading_thread and self.frame_reading_thread.is_alive():
                self.frame_reading_thread.join(timeout=1.0)
            if self.detection_thread and self.detection_thread.is_alive():
                self.detection_thread.join(timeout=1.0)
            if self.ui_update_thread and self.ui_update_thread.is_alive():
                self.ui_update_thread.join(timeout=1.0)
        else:
            if self.detection_thread and self.detection_thread.is_alive():
                self.detection_thread.join(timeout=1.0)
        
        if self.cap:
            self.cap.release()
        
        self.update_signal_lights("OFF")
        self.status_label.config(text="Status: Stopped")
        self.fps_label.config(text="FPS: 0.0")
        self.fps_frame_count = 0
        self.current_fps = 0.0
        
        # Reset individual thread FPS label
        if self.enable_multithreading:
            if self.thread_fps_label:
                self.thread_fps_label.config(text="Thread FPS: Read=0.0 | Detect=0.0 | UI=0.0")
            with self.fps_lock:
                self.frame_reading_fps = 0.0
                self.detection_fps = 0.0
                self.ui_update_fps = 0.0
    
    def detection_loop(self):
        """Main detection loop running in separate thread"""
        import time
        frame_skip = config.FRAME_SKIP if config.FRAME_SKIP > 0 else 1
        frame_counter = 0
        
        # Initialize FPS calculation
        self.fps_start_time = time.time()
        self.fps_frame_count = 0
        last_fps_update = time.time()
        
        if self.enable_batch_processing and self.batch_size > 1:
            # Batch processing mode for single-threaded
            batch_frames = []
            batch_counters = []
            
            while self.is_running:
                ret, frame = self.cap.read()
                if not ret:
                    # Process remaining frames in batch before breaking
                    self.track_error('video_read_error', 'Failed to read frame from video source')
                    if len(batch_frames) > 0:
                        # Sync zone coordinates (zones are already in cropped coordinate system)
                        if self.dock_manager.zone_coordinates:
                            self.detector.update_zone(self.dock_manager.zone_coordinates)
                        
                        # Process batch
                        batch_detections = self.detector.detect_batch(batch_frames)
                        
                        # Process each frame in batch
                        for i, (frame, detections) in enumerate(zip(batch_frames, batch_detections)):
                            detection_summary = self.detector.get_detection_summary(detections)
                            state = self.dock_manager.determine_state(detection_summary)
                            
                            if i == len(batch_frames) - 1:
                                self.last_detections = detections
                                self.last_detection_summary = detection_summary
                                self.last_state = state
                            
                            annotated_frame = self.draw_detections(frame.copy(), detections)
                            self.root.after(0, self.update_frame, annotated_frame, detection_summary, state)
                            
                            # Update FPS
                            self.fps_frame_count += 1
                            current_time = time.time()
                            elapsed = current_time - last_fps_update
                            if elapsed >= self.fps_update_interval:
                                self.current_fps = self.fps_frame_count / elapsed
                                self.fps_frame_count = 0
                                last_fps_update = current_time
                                self.root.after(0, lambda: self.fps_label.config(text=f"FPS: {self.current_fps:.1f}"))
                    break
                
                # Crop frame to reduce size immediately after reading
                frame = self._crop_frame(frame)
                
                frame_counter += 1
                self.fps_frame_count += 1  # Count ALL frames for FPS (including skipped ones)
                
                # Calculate FPS (count all frames read, not just processed ones)
                current_time = time.time()
                elapsed = current_time - last_fps_update
                if elapsed >= self.fps_update_interval:
                    self.current_fps = self.fps_frame_count / elapsed
                    self.fps_frame_count = 0
                    last_fps_update = current_time
                    self.root.after(0, lambda: self.fps_label.config(text=f"FPS: {self.current_fps:.1f}"))
                
                # Skip frames based on FRAME_SKIP setting
                if frame_skip > 1 and frame_counter % frame_skip != 0:
                    if self.last_detections is not None:
                        annotated_frame = self.draw_detections(frame.copy(), self.last_detections)
                        self.root.after(0, self.update_frame, annotated_frame, self.last_detection_summary, self.last_state)
                    else:
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        frame_resized = self._resize_frame_for_display(frame_rgb)
                        image = Image.fromarray(frame_resized)
                        photo = ImageTk.PhotoImage(image=image)
                        self.root.after(0, lambda p=photo: self._update_frame_only(p))
                    # Reduced sleep for RTSP streams - queues handle throttling
                    time.sleep(0.001)
                    continue
                
                # Add frame to batch
                batch_frames.append(frame)
                batch_counters.append(frame_counter)
                
                # Process batch when full
                if len(batch_frames) >= self.batch_size:
                    # Sync zone coordinates (already adjusted for crop in start_detection)
                    if self.dock_manager.zone_coordinates:
                        self.detector.update_zone(self.dock_manager.zone_coordinates)
                    
                    # Process batch
                    batch_detections = self.detector.detect_batch(batch_frames)
                    
                    # Process each frame in batch
                    for i, (frame, detections) in enumerate(zip(batch_frames, batch_detections)):
                        detection_summary = self.detector.get_detection_summary(detections)
                        state = self.dock_manager.determine_state(detection_summary)
                        
                        if i == len(batch_frames) - 1:
                            self.last_detections = detections
                            self.last_detection_summary = detection_summary
                            self.last_state = state
                        
                        annotated_frame = self.draw_detections(frame.copy(), detections)
                        self.root.after(0, self.update_frame, annotated_frame, detection_summary, state)
                        
                        # Update FPS
                        self.fps_frame_count += 1
                        current_time = time.time()
                        elapsed = current_time - last_fps_update
                        if elapsed >= self.fps_update_interval:
                            self.current_fps = self.fps_frame_count / elapsed
                            self.fps_frame_count = 0
                            last_fps_update = current_time
                            self.root.after(0, lambda: self.fps_label.config(text=f"FPS: {self.current_fps:.1f}"))
                    
                    # Clear batch
                    batch_frames = []
                    batch_counters = []
                
                time.sleep(0.001)  # Small delay
        else:
            # Single frame processing mode (original logic)
            while self.is_running:
                ret, frame = self.cap.read()
                if not ret:
                    self.track_error('video_read_error', 'Failed to read frame from video source')
                    break
                
                # Crop frame to reduce size
                frame = self._crop_frame(frame)
                
                frame_counter += 1
                self.fps_frame_count += 1  # Count ALL frames for FPS (including skipped ones)
                
                # Calculate FPS (count all frames read, not just processed ones)
                current_time = time.time()
                elapsed = current_time - last_fps_update
                if elapsed >= self.fps_update_interval:
                    self.current_fps = self.fps_frame_count / elapsed
                    self.fps_frame_count = 0
                    last_fps_update = current_time
                    # Update FPS label in main thread
                    self.root.after(0, lambda: self.fps_label.config(text=f"FPS: {self.current_fps:.1f}"))
                
                # Skip frames based on FRAME_SKIP setting (0 means process every frame)
                if frame_skip > 1 and frame_counter % frame_skip != 0:
                    # Use last detection results for smooth UI (prediction/interpolation)
                    if self.last_detections is not None and self.last_detection_summary is not None:
                        # Draw last detections on current frame for smooth display
                        annotated_frame = self.draw_detections(frame.copy(), self.last_detections)
                        # Update UI with last known state and detections
                        self.root.after(0, self.update_frame, annotated_frame, self.last_detection_summary, self.last_state)
                    else:
                        # No previous detections yet, just show frame
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        frame_resized = self._resize_frame_for_display(frame_rgb)
                        image = Image.fromarray(frame_resized)
                        photo = ImageTk.PhotoImage(image=image)
                        self.root.after(0, lambda p=photo: self._update_frame_only(p))
                    
                    # Reduced sleep for RTSP streams - queues handle throttling
                    time.sleep(0.001)
                    continue
                
                # Sync zone coordinates with detector (zones are already in cropped coordinate system)
                if self.dock_manager.zone_coordinates:
                    self.detector.update_zone(self.dock_manager.zone_coordinates)
                
                # Perform detection (only inside zone)
                detections = self.detector.detect(frame)
                detection_summary = self.detector.get_detection_summary(detections)
                
                # Determine state
                state = self.dock_manager.determine_state(detection_summary)
                
                # Store results for use in skipped frames
                self.last_detections = detections
                self.last_detection_summary = detection_summary
                self.last_state = state
                
                # Draw detections on frame
                annotated_frame = self.draw_detections(frame.copy(), detections)
                
                # Update UI in main thread
                self.root.after(0, self.update_frame, annotated_frame, detection_summary, state)
                
                # Minimal delay - queues and UI throttling handle rate limiting
                # Removed 0.03s sleep to prevent lag with RTSP streams
                time.sleep(0.001)
    
    def _crop_frame(self, frame):
        """
        Crop frame to specified region to reduce frame size
        Crop region defined by coordinates: (1987,0), (659,0), (659,1626), (1987,1626)
        This crops to: x from 659 to 1987, y from 0 to 1626
        The cropped frame becomes the final frame used throughout the system.
        Optimized for performance - minimal bounds checking, uses numpy view (no copy).
        """
        if frame is None:
            return frame
        
        # Crop coordinates: x1=659, y1=0, x2=1987, y2=1626
        # Direct slicing - numpy creates a view (very fast, no memory copy)
        # Minimal bounds check for safety
        h, w = frame.shape[:2]
        return frame[0:min(1626, h), 659:min(1987, w)]  # Clip to frame bounds
    
    def _adjust_coordinates_for_crop(self, coordinates):
        """
        Adjust coordinates to account for frame cropping
        Crop offset: x_offset=659, y_offset=0
        Args:
            coordinates: List of (x, y) tuples or list of [x, y] lists
        Returns:
            Adjusted coordinates
        """
        if coordinates is None:
            return None
        
        # Crop offset
        x_offset, y_offset = 659, 0
        
        adjusted = []
        for coord in coordinates:
            if isinstance(coord, (list, tuple)) and len(coord) >= 2:
                # Adjust x and y coordinates
                adj_x = coord[0] - x_offset
                adj_y = coord[1] - y_offset
                # Keep original format (tuple or list)
                if isinstance(coord, tuple):
                    adjusted.append((adj_x, adj_y))
                else:
                    adjusted.append([adj_x, adj_y])
            else:
                adjusted.append(coord)
        
        return adjusted
    
    def frame_reading_loop(self):
        """Thread 1: Continuously read frames from video source and put in queue"""
        frame_skip = config.FRAME_SKIP if config.FRAME_SKIP > 0 else 1
        frame_counter = 0
        
        # FPS calculation for all frames read (including skipped ones)
        last_fps_update = time.time()
        fps_frame_count = 0
        
        # Individual thread FPS tracking
        thread_fps_count = 0
        thread_fps_start = time.time()
        
        while self.is_running:
            if self.cap is None or not self.cap.isOpened():
                self.track_error('video_read_error', 'Video capture is not opened or became invalid')
                break
                
            ret, frame = self.cap.read()
            if not ret:
                # Video ended or error reading frame
                self.track_error('video_read_error', 'Failed to read frame from video source')
                break
            
            # Crop frame to reduce size
            frame = self._crop_frame(frame)
            
            frame_counter += 1
            fps_frame_count += 1  # Count ALL frames for FPS (including skipped ones)
            thread_fps_count += 1  # Count for thread-specific FPS
            
            # Calculate FPS (count all frames read, not just processed ones)
            current_time = time.time()
            elapsed = current_time - last_fps_update
            if elapsed >= self.fps_update_interval:
                self.current_fps = fps_frame_count / elapsed
                fps_frame_count = 0
                last_fps_update = current_time
                # Update FPS label in main thread
                self.root.after(0, lambda: self.fps_label.config(text=f"FPS: {self.current_fps:.1f}"))
            
            # Calculate thread-specific FPS
            thread_elapsed = current_time - thread_fps_start
            if thread_elapsed >= self.fps_update_interval:
                with self.fps_lock:
                    self.frame_reading_fps = thread_fps_count / thread_elapsed
                thread_fps_count = 0
                thread_fps_start = current_time
                # Update thread FPS label (combined)
                with self.fps_lock:
                    read_fps = self.frame_reading_fps
                    detect_fps = self.detection_fps
                    ui_fps = self.ui_update_fps
                self.root.after(0, lambda r=read_fps, d=detect_fps, u=ui_fps: 
                    self.thread_fps_label.config(text=f"Thread FPS: Read={r:.1f} | Detect={d:.1f} | UI={u:.1f}"))
            
            # Skip frames based on FRAME_SKIP setting
            if frame_skip > 1 and frame_counter % frame_skip != 0:
                continue
            
            # Put frame in queue (non-blocking, drop if queue is full)
            try:
                self.frame_queue.put_nowait((frame_counter, frame))
            except queue.Full:
                # Queue is full, drop oldest frame and add new one
                self.track_error('frame_queue_full', f'Frame queue full at frame {frame_counter}')
                try:
                    self.frame_queue.get_nowait()
                    self.track_error('dropped_frame', 'Dropped oldest frame from queue')
                    self.frame_queue.put_nowait((frame_counter, frame))
                except queue.Empty:
                    pass
            except AttributeError:
                # Queue might not be initialized yet
                break
            
            # No sleep needed - queue and processing threads handle rate limiting naturally
            # Removing sleep improves frame reading speed, especially with smaller cropped frames
    
    def detection_processing_loop(self):
        """Thread 2: Process frames from queue, perform detection, put results in result queue"""
        # Note: FPS is calculated in frame_reading_loop to count all frames (including skipped ones)
        
        # Individual thread FPS tracking
        detection_fps_count = 0
        detection_fps_start = time.time()
        
        if self.enable_batch_processing and self.batch_size > 1:
            # Batch processing mode
            while self.is_running:
                try:
                    # Collect frames for batch
                    batch_frames = []
                    batch_counters = []
                    batch_timeout = config.BATCH_TIMEOUT
                    
                    # Try to collect a full batch
                    start_time = time.time()
                    while len(batch_frames) < self.batch_size and (time.time() - start_time) < batch_timeout:
                        try:
                            frame_counter, frame = self.frame_queue.get(timeout=0.01)
                            batch_frames.append(frame)
                            batch_counters.append(frame_counter)
                        except queue.Empty:
                            # If we have at least one frame, process it (don't wait forever)
                            if len(batch_frames) > 0:
                                break
                            continue
                    
                    if len(batch_frames) == 0:
                        continue
                    
                    # Sync zone coordinates with detector (zones are already in cropped coordinate system)
                    if self.dock_manager.zone_coordinates:
                        self.detector.update_zone(self.dock_manager.zone_coordinates)
                    
                    # Perform batch detection
                    batch_detections = self.detector.detect_batch(batch_frames)
                    
                    # Process each frame in the batch
                    for i, (frame, detections) in enumerate(zip(batch_frames, batch_detections)):
                        detection_summary = self.detector.get_detection_summary(detections)
                        state = self.dock_manager.determine_state(detection_summary)
                        
                        # Store results for use in skipped frames (use last frame in batch)
                        if i == len(batch_frames) - 1:
                            self.last_detections = detections
                            self.last_detection_summary = detection_summary
                            self.last_state = state
                        
                        # Draw detections on frame
                        annotated_frame = self.draw_detections(frame.copy(), detections)
                        
                        # Track detection FPS
                        detection_fps_count += 1
                        current_time = time.time()
                        detection_elapsed = current_time - detection_fps_start
                        if detection_elapsed >= self.fps_update_interval:
                            with self.fps_lock:
                                self.detection_fps = detection_fps_count / detection_elapsed
                            detection_fps_count = 0
                            detection_fps_start = current_time
                            # Update thread FPS label (combined)
                            with self.fps_lock:
                                read_fps = self.frame_reading_fps
                                detect_fps = self.detection_fps
                                ui_fps = self.ui_update_fps
                            self.root.after(0, lambda r=read_fps, d=detect_fps, u=ui_fps: 
                                self.thread_fps_label.config(text=f"Thread FPS: Read={r:.1f} | Detect={d:.1f} | UI={u:.1f}"))
                        
                        # Put result in queue (FPS is calculated in frame_reading_loop)
                        result = {
                            'frame': annotated_frame,
                            'detection_summary': detection_summary,
                            'state': state,
                            'fps': self.current_fps
                        }
                        
                        try:
                            self.result_queue.put_nowait(result)
                        except queue.Full:
                            # Queue is full, drop oldest result and add new one
                            self.track_error('result_queue_full', 'Result queue full')
                            try:
                                self.result_queue.get_nowait()
                                self.result_queue.put_nowait(result)
                            except queue.Empty:
                                pass
                
                except Exception as e:
                    error_msg = f"Error in batch detection processing: {e}"
                    print(error_msg)
                    self.track_error('detection_error', error_msg)
                    continue
        else:
            # Single frame processing mode (original logic)
            while self.is_running:
                try:
                    # Get frame from queue (with timeout to allow checking is_running)
                    frame_counter, frame = self.frame_queue.get(timeout=0.1)
                    
                    # Sync zone coordinates with detector (in case zone was updated)
                    if self.dock_manager.zone_coordinates:
                        self.detector.update_zone(self.dock_manager.zone_coordinates)
                    
                    # Perform detection (only inside zone)
                    detections = self.detector.detect(frame)
                    detection_summary = self.detector.get_detection_summary(detections)
                    
                    # Determine state
                    state = self.dock_manager.determine_state(detection_summary)
                    
                    # Store results for use in skipped frames
                    self.last_detections = detections
                    self.last_detection_summary = detection_summary
                    self.last_state = state
                    
                    # Draw detections on frame
                    annotated_frame = self.draw_detections(frame.copy(), detections)
                    
                    # Track detection FPS
                    detection_fps_count += 1
                    current_time = time.time()
                    detection_elapsed = current_time - detection_fps_start
                    if detection_elapsed >= self.fps_update_interval:
                        with self.fps_lock:
                            self.detection_fps = detection_fps_count / detection_elapsed
                        detection_fps_count = 0
                        detection_fps_start = current_time
                        self.root.after(0, lambda fps=self.detection_fps: 
                            self.detection_fps_label.config(text=f"Detection FPS: {fps:.1f}"))
                    
                    # Put result in queue (FPS is calculated in frame_reading_loop)
                    result = {
                        'frame': annotated_frame,
                        'detection_summary': detection_summary,
                        'state': state,
                        'fps': self.current_fps
                    }
                    
                    try:
                        self.result_queue.put_nowait(result)
                    except queue.Full:
                        # Queue is full, drop oldest result and add new one
                        self.track_error('result_queue_full', 'Result queue full')
                        try:
                            self.result_queue.get_nowait()
                            self.result_queue.put_nowait(result)
                        except queue.Empty:
                            pass
                    
                except queue.Empty:
                    # No frame available, continue
                    continue
                except Exception as e:
                    error_msg = f"Error in detection processing: {e}"
                    print(error_msg)
                    self.track_error('detection_error', error_msg)
                    continue
    
    def ui_update_loop(self):
        """Thread 3: Get results from queue and update UI in main thread"""
        last_update_time = time.time()
        min_update_interval = 0.033  # ~30 FPS max UI update rate
        pending_result = None  # Store result if throttled
        
        # Individual thread FPS tracking
        ui_fps_count = 0
        ui_fps_start = time.time()
        
        while self.is_running:
            try:
                # Get result from queue (with timeout to allow checking is_running)
                # If we have a pending result from throttling, use it first
                if pending_result is None:
                    result = self.result_queue.get(timeout=0.1)
                else:
                    result = pending_result
                    pending_result = None
                
                # Throttle UI updates to prevent overwhelming the main thread
                current_time = time.time()
                if current_time - last_update_time < min_update_interval:
                    # Store result for next update instead of discarding it
                    pending_result = result
                    time.sleep(0.001)  # Small sleep to prevent busy waiting
                    continue
                
                # Update UI in main thread (thread-safe)
                self.root.after(0, self.update_frame, 
                              result['frame'], 
                              result['detection_summary'], 
                              result['state'])
                
                # Update FPS label
                self.root.after(0, lambda fps=result['fps']: self.fps_label.config(text=f"FPS: {fps:.1f}"))
                
                # Track UI update FPS
                ui_fps_count += 1
                ui_elapsed = current_time - ui_fps_start
                if ui_elapsed >= self.fps_update_interval:
                    with self.fps_lock:
                        self.ui_update_fps = ui_fps_count / ui_elapsed
                    ui_fps_count = 0
                    ui_fps_start = current_time
                    # Update thread FPS label (combined)
                    with self.fps_lock:
                        read_fps = self.frame_reading_fps
                        detect_fps = self.detection_fps
                        ui_fps = self.ui_update_fps
                    self.root.after(0, lambda r=read_fps, d=detect_fps, u=ui_fps: 
                        self.thread_fps_label.config(text=f"Thread FPS: Read={r:.1f} | Detect={d:.1f} | UI={u:.1f}"))
                
                last_update_time = current_time
                
            except queue.Empty:
                # No result available, show last frame if available (for smooth display)
                if self.last_detections is not None and self.last_detection_summary is not None:
                    # Create a simple frame with last detections (this is a fallback)
                    # The frame reading thread should provide frames continuously
                    pass
                continue
            except Exception as e:
                error_msg = f"Error in UI update: {e}"
                print(error_msg)
                self.track_error('general_error', error_msg)
                continue
    
    def _get_video_display_size(self):
        """Get the proper display size for video frame maintaining aspect ratio"""
        # Update the label first to get its actual size
        self.video_label.update_idletasks()
        video_width = self.video_label.winfo_width()
        video_height = self.video_label.winfo_height()
        
        # Use default size if not yet rendered (fallback)
        if video_width <= 1:
            video_width = 960
        if video_height <= 1:
            video_height = 720
        
        return video_width, video_height
    
    def _resize_frame_for_display(self, frame_rgb):
        """Resize frame to fit display while maintaining aspect ratio"""
        video_width, video_height = self._get_video_display_size()
        
        # Maintain aspect ratio
        frame_height, frame_width = frame_rgb.shape[:2]
        aspect_ratio = frame_width / frame_height
        
        if video_width / video_height > aspect_ratio:
            # Window is wider than video - fit to height
            display_height = video_height
            display_width = int(video_height * aspect_ratio)
        else:
            # Window is taller than video - fit to width
            display_width = video_width
            display_height = int(video_width / aspect_ratio)
        
        return cv2.resize(frame_rgb, (display_width, display_height))
    
    def _update_frame_only(self, photo):
        """Update only the video frame without detection info (for skipped frames)"""
        self.video_label.config(image=photo)
        self.video_label.image = photo  # Keep a reference
    
    def draw_detections(self, frame, detections):
        """Draw detection boxes on frame"""
        import numpy as np
        
        # Draw zone polygon if configured (already adjusted for crop in start_detection)
        if self.dock_manager.zone_coordinates and len(self.dock_manager.zone_coordinates) >= 3:
            zone_pts = np.array(self.dock_manager.zone_coordinates, np.int32)
            zone_pts = zone_pts.reshape((-1, 1, 2))
            # Draw filled polygon with transparency
            overlay = frame.copy()
            cv2.fillPoly(overlay, [zone_pts], (0, 255, 0))
            cv2.addWeighted(overlay, 0.2, frame, 0.8, 0, frame)
            cv2.polylines(frame, [zone_pts], True, (0, 255, 0), 2)
        
        # Draw parking line if configured (already adjusted for crop in start_detection)
        if self.dock_manager.parking_line_points and len(self.dock_manager.parking_line_points) >= 2:
            line_pts = np.array(self.dock_manager.parking_line_points, np.int32)
            cv2.polylines(frame, [line_pts], False, (0, 255, 255), 3)
            # Draw points
            for pt in self.dock_manager.parking_line_points:
                cv2.circle(frame, tuple(pt), 5, (0, 255, 255), -1)
        
        # Draw trucks in blue
        for truck in detections['trucks']:
            x1, y1, x2, y2 = truck['bbox']
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.putText(frame, f"Truck {truck['confidence']:.2f}", 
                       (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
        
        # Draw humans in green
        for human in detections['humans']:
            x1, y1, x2, y2 = human['bbox']
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"Person {human['confidence']:.2f}", 
                       (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return frame
    
    def update_frame(self, frame, detection_summary, state):
        """Update video frame and UI elements"""
        # Convert frame to PhotoImage - use full available space
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_resized = self._resize_frame_for_display(frame_rgb)
        image = Image.fromarray(frame_resized)
        photo = ImageTk.PhotoImage(image=image)
        
        self.video_label.config(image=photo)
        self.video_label.image = photo  # Keep a reference
        
        # Update signal lights
        self.update_signal_lights(state)
        
        # Update status with wait time if applicable
        remaining_wait = self.dock_manager.get_parking_wait_remaining()
        if remaining_wait is not None and state == "YELLOW":
            status_text = f"Status: {state} (Waiting: {remaining_wait}s)"
            self.wait_time_label.config(text=f"Parking line touched. Turning green in {remaining_wait} seconds...")
        else:
            status_text = f"Status: {state}"
            self.wait_time_label.config(text="")
        
        self.status_label.config(text=status_text)
        
        # Update info
        self.update_info(detection_summary, state)
    
    
    def open_settings(self):
        """Open settings dialog with password protection"""
        # Password protection
        SETTINGS_PASSWORD = "123456780"
        
        # Create password dialog
        password_window = tk.Toplevel(self.root)
        password_window.title("Enter Password")
        password_window.geometry("350x150")
        password_window.transient(self.root)
        password_window.grab_set()
        password_window.resizable(False, False)
        
        # Center the window
        password_window.update_idletasks()
        x = (password_window.winfo_screenwidth() // 2) - (password_window.winfo_width() // 2)
        y = (password_window.winfo_screenheight() // 2) - (password_window.winfo_height() // 2)
        password_window.geometry(f"+{x}+{y}")
        
        # Password label and entry
        ttk.Label(password_window, text="Enter Password to Access Settings:", font=("Arial", 10)).pack(pady=20)
        password_var = tk.StringVar()
        password_entry = ttk.Entry(password_window, textvariable=password_var, show="*", width=30, font=("Arial", 10))
        password_entry.pack(pady=10)
        password_entry.focus()
        
        error_label = ttk.Label(password_window, text="", foreground="red", font=("Arial", 9))
        error_label.pack(pady=5)
        
        def check_password():
            """Check if password is correct"""
            entered_password = password_var.get()
            if entered_password == SETTINGS_PASSWORD:
                password_window.destroy()
                self._open_settings_dialog()
            else:
                error_label.config(text="Incorrect password. Please try again.")
                password_var.set("")
                password_entry.focus()
        
        def on_enter(event):
            """Handle Enter key press"""
            check_password()
        
        password_entry.bind("<Return>", on_enter)
        
        # Buttons
        button_frame = ttk.Frame(password_window)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="OK", command=check_password, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=password_window.destroy, width=15).pack(side=tk.LEFT, padx=5)
    
    def _open_settings_dialog(self):
        """Open settings dialog (internal method called after password verification)"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("700x800")
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # Create notebook for tabs
        notebook = ttk.Notebook(settings_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Get current settings
        current_settings = config.get_current_settings()
        
        # Variables to hold settings values
        settings_vars = {}
        
        # ========== VIDEO & MODEL TAB ==========
        video_frame = ttk.Frame(notebook, padding="10")
        notebook.add(video_frame, text="Video & Model")
        
        row = 0
        # Video Source
        ttk.Label(video_frame, text="Video Source (Camera IP/RTSP/File Path):").grid(row=row, column=0, sticky=tk.W, pady=5)
        settings_vars['video_source'] = tk.StringVar(value=current_settings.get('video_source', ''))
        ttk.Entry(video_frame, textvariable=settings_vars['video_source'], width=60).grid(row=row, column=1, pady=5, sticky=(tk.W, tk.E))
        ttk.Label(video_frame, text="Example: rtsp://user:pass@ip:port/path or 0 for webcam", font=("Arial", 8), foreground="gray").grid(row=row+1, column=1, sticky=tk.W)
        row += 2
        
        # Model Path
        ttk.Label(video_frame, text="Model Path:").grid(row=row, column=0, sticky=tk.W, pady=5)
        settings_vars['model_path'] = tk.StringVar(value=current_settings.get('model_path', ''))
        ttk.Entry(video_frame, textvariable=settings_vars['model_path'], width=60).grid(row=row, column=1, pady=5, sticky=(tk.W, tk.E))
        row += 1
        
        # Confidence Threshold
        ttk.Label(video_frame, text="Confidence Threshold:").grid(row=row, column=0, sticky=tk.W, pady=5)
        settings_vars['confidence_threshold'] = tk.StringVar(value=str(current_settings.get('confidence_threshold', 0.5)))
        ttk.Entry(video_frame, textvariable=settings_vars['confidence_threshold'], width=20).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1
        
        # Use GPU
        settings_vars['use_gpu'] = tk.BooleanVar(value=current_settings.get('use_gpu', True))
        ttk.Checkbutton(video_frame, text="Use GPU (CUDA)", variable=settings_vars['use_gpu']).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)
        row += 1
        
        # License Key
        ttk.Label(video_frame, text="License Key:").grid(row=row, column=0, sticky=tk.W, pady=5)
        settings_vars['license_key'] = tk.StringVar(value=current_settings.get('license_key', ''))
        ttk.Entry(video_frame, textvariable=settings_vars['license_key'], width=60).grid(row=row, column=1, pady=5, sticky=(tk.W, tk.E))
        row += 1
        
        # Show License Expiry
        settings_vars['show_license_expiry'] = tk.BooleanVar(value=current_settings.get('show_license_expiry', True))
        ttk.Checkbutton(video_frame, text="Show License Expiry Warning", variable=settings_vars['show_license_expiry']).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)
        row += 1
        
        video_frame.columnconfigure(1, weight=1)
        
        # ========== API SETTINGS TAB ==========
        api_frame = ttk.Frame(notebook, padding="10")
        notebook.add(api_frame, text="API Settings")
        
        row = 0
        # Enable API Calls
        settings_vars['enable_api_calls'] = tk.BooleanVar(value=current_settings.get('enable_api_calls', True))
        ttk.Checkbutton(api_frame, text="Enable API Calls", variable=settings_vars['enable_api_calls']).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)
        row += 1
        
        # Yellow API URL
        ttk.Label(api_frame, text="Yellow API URL:").grid(row=row, column=0, sticky=tk.W, pady=5)
        settings_vars['yellow_api_url'] = tk.StringVar(value=current_settings.get('yellow_api_url', ''))
        ttk.Entry(api_frame, textvariable=settings_vars['yellow_api_url'], width=60).grid(row=row, column=1, pady=5, sticky=(tk.W, tk.E))
        row += 1
        
        # Red API URL
        ttk.Label(api_frame, text="Red API URL:").grid(row=row, column=0, sticky=tk.W, pady=5)
        settings_vars['red_api_url'] = tk.StringVar(value=current_settings.get('red_api_url', ''))
        ttk.Entry(api_frame, textvariable=settings_vars['red_api_url'], width=60).grid(row=row, column=1, pady=5, sticky=(tk.W, tk.E))
        row += 1
        
        # Stop API URL
        ttk.Label(api_frame, text="Stop API URL (Green):").grid(row=row, column=0, sticky=tk.W, pady=5)
        settings_vars['stop_api_url'] = tk.StringVar(value=current_settings.get('stop_api_url', ''))
        ttk.Entry(api_frame, textvariable=settings_vars['stop_api_url'], width=60).grid(row=row, column=1, pady=5, sticky=(tk.W, tk.E))
        row += 1
        
        # Separator
        ttk.Separator(api_frame, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        row += 1
        
        # Dock Status API Section
        ttk.Label(api_frame, text="Dock Status API (JSON POST):", font=("Arial", 9, "bold")).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)
        row += 1
        
        # Enable Dock Status API
        settings_vars['enable_dock_status_api'] = tk.BooleanVar(value=current_settings.get('enable_dock_status_api', True))
        ttk.Checkbutton(api_frame, text="Enable Dock Status API", variable=settings_vars['enable_dock_status_api']).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)
        row += 1
        
        # Dock Status API URL
        ttk.Label(api_frame, text="Dock Status API URL:").grid(row=row, column=0, sticky=tk.W, pady=5)
        settings_vars['dock_status_api_url'] = tk.StringVar(value=current_settings.get('dock_status_api_url', 'http://127.0.0.1:3041/dock1/status'))
        ttk.Entry(api_frame, textvariable=settings_vars['dock_status_api_url'], width=60).grid(row=row, column=1, pady=5, sticky=(tk.W, tk.E))
        ttk.Label(api_frame, text="Sends JSON: {vehicle_status, human_presence, notes}", font=("Arial", 8), foreground="gray").grid(row=row+1, column=1, sticky=tk.W)
        row += 2
        
        api_frame.columnconfigure(1, weight=1)
        
        # ========== PLC SETTINGS TAB ==========
        plc_frame = ttk.Frame(notebook, padding="10")
        notebook.add(plc_frame, text="PLC Settings")
        
        row = 0
        # Enable PLC
        settings_vars['enable_plc'] = tk.BooleanVar(value=current_settings.get('enable_plc', True))
        ttk.Checkbutton(plc_frame, text="Enable PLC", variable=settings_vars['enable_plc']).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)
        row += 1
        
        # PLC Host
        ttk.Label(plc_frame, text="PLC Host:").grid(row=row, column=0, sticky=tk.W, pady=5)
        settings_vars['plc_host'] = tk.StringVar(value=current_settings.get('plc_host', ''))
        ttk.Entry(plc_frame, textvariable=settings_vars['plc_host'], width=30).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1
        
        # PLC Port
        ttk.Label(plc_frame, text="PLC Port:").grid(row=row, column=0, sticky=tk.W, pady=5)
        settings_vars['plc_port'] = tk.StringVar(value=str(current_settings.get('plc_port', 502)))
        ttk.Entry(plc_frame, textvariable=settings_vars['plc_port'], width=20).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1
        
        # PLC Coil Configurations
        ttk.Label(plc_frame, text="PLC Coil Configurations (8 coils - True/False):", font=("Arial", 9, "bold")).grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=(15, 5))
        row += 1
        
        # Green Light Coils
        ttk.Label(plc_frame, text="Green Light Coils:").grid(row=row, column=0, sticky=tk.W, pady=5)
        green_coils_frame = ttk.Frame(plc_frame)
        green_coils_frame.grid(row=row, column=1, sticky=tk.W, pady=5)
        settings_vars['plc_green_coils'] = []
        green_coils = current_settings.get('plc_green_coils', [True, False, False, False, False, False, False, False])
        for i in range(8):
            var = tk.BooleanVar(value=green_coils[i] if i < len(green_coils) else False)
            settings_vars['plc_green_coils'].append(var)
            ttk.Checkbutton(green_coils_frame, text=f"C{i}", variable=var).grid(row=0, column=i, padx=2)
        row += 1
        
        # Red Light Coils
        ttk.Label(plc_frame, text="Red Light Coils:").grid(row=row, column=0, sticky=tk.W, pady=5)
        red_coils_frame = ttk.Frame(plc_frame)
        red_coils_frame.grid(row=row, column=1, sticky=tk.W, pady=5)
        settings_vars['plc_red_coils'] = []
        red_coils = current_settings.get('plc_red_coils', [False, True, False, False, False, False, False, False])
        for i in range(8):
            var = tk.BooleanVar(value=red_coils[i] if i < len(red_coils) else False)
            settings_vars['plc_red_coils'].append(var)
            ttk.Checkbutton(red_coils_frame, text=f"C{i}", variable=var).grid(row=0, column=i, padx=2)
        row += 1
        
        # Yellow Light Coils
        ttk.Label(plc_frame, text="Yellow Light Coils:").grid(row=row, column=0, sticky=tk.W, pady=5)
        yellow_coils_frame = ttk.Frame(plc_frame)
        yellow_coils_frame.grid(row=row, column=1, sticky=tk.W, pady=5)
        settings_vars['plc_yellow_coils'] = []
        yellow_coils = current_settings.get('plc_yellow_coils', [False, False, True, False, False, False, False, False])
        for i in range(8):
            var = tk.BooleanVar(value=yellow_coils[i] if i < len(yellow_coils) else False)
            settings_vars['plc_yellow_coils'].append(var)
            ttk.Checkbutton(yellow_coils_frame, text=f"C{i}", variable=var).grid(row=0, column=i, padx=2)
        row += 1
        
        # ========== TIMING SETTINGS TAB ==========
        timing_frame = ttk.Frame(notebook, padding="10")
        notebook.add(timing_frame, text="Timing Settings")
        
        row = 0
        # Parking Line Wait Time
        ttk.Label(timing_frame, text="Parking Line Wait Time (seconds):").grid(row=row, column=0, sticky=tk.W, pady=5)
        settings_vars['parking_line_wait_time'] = tk.StringVar(value=str(current_settings.get('parking_line_wait_time', 10)))
        ttk.Entry(timing_frame, textvariable=settings_vars['parking_line_wait_time'], width=20).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1
        
        # Parking Line Grace Period
        ttk.Label(timing_frame, text="Parking Line Grace Period (frames):").grid(row=row, column=0, sticky=tk.W, pady=5)
        settings_vars['parking_line_grace_period'] = tk.StringVar(value=str(current_settings.get('parking_line_grace_period', 50)))
        ttk.Entry(timing_frame, textvariable=settings_vars['parking_line_grace_period'], width=20).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1
        
        # ========== PERFORMANCE SETTINGS TAB ==========
        perf_frame = ttk.Frame(notebook, padding="10")
        notebook.add(perf_frame, text="Performance")
        
        row = 0
        # Enable Multithreading
        settings_vars['enable_multithreading'] = tk.BooleanVar(value=current_settings.get('enable_multithreading', True))
        ttk.Checkbutton(perf_frame, text="Enable Multithreading", variable=settings_vars['enable_multithreading']).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)
        row += 1
        
        # Enable Batch Processing
        settings_vars['enable_batch_processing'] = tk.BooleanVar(value=current_settings.get('enable_batch_processing', True))
        ttk.Checkbutton(perf_frame, text="Enable Batch Processing", variable=settings_vars['enable_batch_processing']).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)
        row += 1
        
        # Batch Size
        ttk.Label(perf_frame, text="Batch Size:").grid(row=row, column=0, sticky=tk.W, pady=5)
        settings_vars['batch_size'] = tk.StringVar(value=str(current_settings.get('batch_size', 2)))
        ttk.Entry(perf_frame, textvariable=settings_vars['batch_size'], width=20).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1
        
        # Batch Timeout
        ttk.Label(perf_frame, text="Batch Timeout (seconds):").grid(row=row, column=0, sticky=tk.W, pady=5)
        settings_vars['batch_timeout'] = tk.StringVar(value=str(current_settings.get('batch_timeout', 0.005)))
        ttk.Entry(perf_frame, textvariable=settings_vars['batch_timeout'], width=20).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1
        
        # Frame Skip
        ttk.Label(perf_frame, text="Frame Skip (0 = process all):").grid(row=row, column=0, sticky=tk.W, pady=5)
        settings_vars['frame_skip'] = tk.StringVar(value=str(current_settings.get('frame_skip', 0)))
        ttk.Entry(perf_frame, textvariable=settings_vars['frame_skip'], width=20).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1
        
        # ========== ZONE CONFIGURATION TAB ==========
        zone_frame = ttk.Frame(notebook, padding="10")
        notebook.add(zone_frame, text="Zone Configuration")
        
        # Zone Coordinates
        ttk.Label(zone_frame, text="Zone Coordinates (JSON format):", font=("Arial", 9, "bold")).grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Label(zone_frame, text="Format: [[x1,y1], [x2,y2], [x3,y3], ...]", font=("Arial", 8), foreground="gray").grid(row=1, column=0, sticky=tk.W, pady=2)
        
        zone_coords_text = tk.Text(zone_frame, width=60, height=8, font=("Courier", 9))
        zone_coords_text.grid(row=2, column=0, pady=5, sticky=(tk.W, tk.E))
        zone_coords_value = current_settings.get('zone_coordinates', [])
        zone_coords_text.insert("1.0", json.dumps(zone_coords_value, indent=2))
        settings_vars['zone_coordinates'] = zone_coords_text
        zone_frame.columnconfigure(0, weight=1)
        
        # Parking Line Points
        ttk.Label(zone_frame, text="Parking Line Points (JSON format):", font=("Arial", 9, "bold")).grid(row=3, column=0, sticky=tk.W, pady=(15, 5))
        ttk.Label(zone_frame, text="Format: [[x1,y1], [x2,y2]]", font=("Arial", 8), foreground="gray").grid(row=4, column=0, sticky=tk.W, pady=2)
        
        parking_line_text = tk.Text(zone_frame, width=60, height=4, font=("Courier", 9))
        parking_line_text.grid(row=5, column=0, pady=5, sticky=(tk.W, tk.E))
        parking_line_value = current_settings.get('parking_line_points', [])
        parking_line_text.insert("1.0", json.dumps(parking_line_value, indent=2))
        settings_vars['parking_line_points'] = parking_line_text
        
        ttk.Label(zone_frame, text="Note: Use 'python configure_zones.py' for visual configuration", 
                 font=("Arial", 8), foreground="blue").grid(row=6, column=0, sticky=tk.W, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(settings_window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def save_settings():
            """Save settings from dialog"""
            try:
                new_settings = {}
                new_settings['video_source'] = settings_vars['video_source'].get()
                new_settings['model_path'] = settings_vars['model_path'].get()
                new_settings['confidence_threshold'] = float(settings_vars['confidence_threshold'].get())
                new_settings['use_gpu'] = settings_vars['use_gpu'].get()
                new_settings['license_key'] = settings_vars['license_key'].get()
                new_settings['show_license_expiry'] = settings_vars['show_license_expiry'].get()
                new_settings['yellow_api_url'] = settings_vars['yellow_api_url'].get()
                new_settings['red_api_url'] = settings_vars['red_api_url'].get()
                new_settings['stop_api_url'] = settings_vars['stop_api_url'].get()
                new_settings['enable_api_calls'] = settings_vars['enable_api_calls'].get()
                new_settings['dock_status_api_url'] = settings_vars['dock_status_api_url'].get()
                new_settings['enable_dock_status_api'] = settings_vars['enable_dock_status_api'].get()
                new_settings['enable_plc'] = settings_vars['enable_plc'].get()
                new_settings['plc_host'] = settings_vars['plc_host'].get()
                new_settings['plc_port'] = int(settings_vars['plc_port'].get())
                # PLC Coils
                new_settings['plc_green_coils'] = [var.get() for var in settings_vars['plc_green_coils']]
                new_settings['plc_red_coils'] = [var.get() for var in settings_vars['plc_red_coils']]
                new_settings['plc_yellow_coils'] = [var.get() for var in settings_vars['plc_yellow_coils']]
                new_settings['parking_line_wait_time'] = int(settings_vars['parking_line_wait_time'].get())
                new_settings['parking_line_grace_period'] = int(settings_vars['parking_line_grace_period'].get())
                new_settings['batch_size'] = int(settings_vars['batch_size'].get())
                new_settings['batch_timeout'] = float(settings_vars['batch_timeout'].get())
                new_settings['enable_batch_processing'] = settings_vars['enable_batch_processing'].get()
                new_settings['enable_multithreading'] = settings_vars['enable_multithreading'].get()
                new_settings['frame_skip'] = int(settings_vars['frame_skip'].get())
                # Zone Configuration (parse JSON from text widgets)
                zone_coords_text = settings_vars['zone_coordinates'].get("1.0", tk.END).strip()
                parking_line_text = settings_vars['parking_line_points'].get("1.0", tk.END).strip()
                if zone_coords_text:
                    new_settings['zone_coordinates'] = json.loads(zone_coords_text)
                if parking_line_text:
                    new_settings['parking_line_points'] = json.loads(parking_line_text)
                
                # Save to file
                if config.save_settings_to_file(new_settings):
                    # Update config module
                    config.update_settings_from_dict(new_settings)
                    # Update license expiry display immediately if setting changed
                    self.update_license_expiry_display()
                    messagebox.showinfo("Settings", "Settings saved successfully!\nPlease restart the application for changes to take effect.")
                    settings_window.destroy()
                else:
                    messagebox.showerror("Error", "Failed to save settings.")
            except ValueError as e:
                messagebox.showerror("Error", f"Invalid value: {e}\nPlease check all fields are correct.")
            except Exception as e:
                messagebox.showerror("Error", f"Error saving settings: {e}")
        
        ttk.Button(button_frame, text="Save", command=save_settings).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=settings_window.destroy).pack(side=tk.RIGHT, padx=5)
    
    def on_closing(self):
        """Handle window closing"""
        self.is_running = False
        if self.cap:
            self.cap.release()
        self.root.destroy()
    
    def run(self):
        """Start the UI main loop"""
        self.root.mainloop()
