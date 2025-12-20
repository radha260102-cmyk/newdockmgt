"""
Zone and Parking Line Configuration Script
Interactive tool to configure dock zone and parking line coordinates
"""
import cv2
import json
import os
import numpy as np
import config

CONFIG_FILE = config.ZONE_CONFIG_FILE
VIDEO_SOURCE = config.VIDEO_SOURCE


class ZoneConfigurator:
    """Interactive zone and parking line configuration tool"""
    
    def __init__(self, video_source):
        self.video_source = video_source
        self.cap = None
        self.current_frame = None
        self.original_frame = None  # Store original frame for coordinate mapping
        self.zone_points = []
        self.parking_line_points = []
        self.config = {}
        self.mode = "zone"  # "zone" or "parking_line"
        self.window_name = "Zone Configuration - Press 'z' for zone, 'p' for parking line, 's' to save, 'q' to quit"
        self.window_width = config.WINDOW_WIDTH
        self.window_height = config.WINDOW_HEIGHT
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.x_offset = 0
        self.y_offset = 0
    
    def _crop_frame(self, frame):
        """
        Crop frame to specified region to reduce frame size
        Crop region defined by coordinates: (1987,0), (659,0), (659,1626), (1987,1626)
        This crops to: x from 659 to 1987, y from 0 to 1626
        The cropped frame becomes the final frame used throughout the system.
        Zones configured on this cropped frame are already in the correct coordinate system.
        """
        if frame is None:
            return frame
        
        # Crop coordinates: x1=659, y1=0, x2=1987, y2=1626
        # Area to keep: rectangle defined by (1987,0), (659,0), (659,1626), (1987,1626)
        x1, y1 = 659, 0
        x2, y2 = 1987, 1626
        
        # Get frame dimensions
        frame_height, frame_width = frame.shape[:2]
        
        # Ensure crop coordinates are within frame bounds
        x1 = max(0, min(x1, frame_width))
        y1 = max(0, min(y1, frame_height))
        x2 = max(x1, min(x2, frame_width))
        y2 = max(y1, min(y2, frame_height))
        
        # Crop the frame (reduce frame size by keeping only the specified region)
        cropped_frame = frame[y1:y2, x1:x2]
        return cropped_frame
        
    def load_config(self):
        """Load existing configuration from JSON"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self.config = json.load(f)
                    self.zone_points = self.config.get('zone_coordinates', [])
                    self.parking_line_points = self.config.get('parking_line_points', [])
                    print(f"Loaded existing configuration from {CONFIG_FILE}")
                    return True
            except Exception as e:
                print(f"Error loading config: {e}")
        return False
    
    def save_config(self):
        """Save configuration to JSON"""
        self.config = {
            'zone_coordinates': self.zone_points,
            'parking_line_points': self.parking_line_points
        }
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=4)
            print(f"\nConfiguration saved to {CONFIG_FILE}")
            print(f"Zone points: {len(self.zone_points)} points")
            print(f"Parking line points: {len(self.parking_line_points)} points")
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def mouse_callback(self, event, x, y, flags, param):
        """Handle mouse clicks to add points"""
        if event == cv2.EVENT_LBUTTONDOWN:
            # Check if click is within the frame area (accounting for offset)
            if (self.x_offset <= x < self.x_offset + self.current_frame.shape[1] * self.scale_x and
                self.y_offset <= y < self.y_offset + self.current_frame.shape[0] * self.scale_y):
                # Convert display coordinates to original frame coordinates
                orig_x = int((x - self.x_offset) / self.scale_x)
                orig_y = int((y - self.y_offset) / self.scale_y)
                
                if self.mode == "zone":
                    self.zone_points.append([orig_x, orig_y])
                    print(f"Zone point {len(self.zone_points)}: ({orig_x}, {orig_y})")
                elif self.mode == "parking_line":
                    self.parking_line_points.append([orig_x, orig_y])
                    print(f"Parking line point {len(self.parking_line_points)}: ({orig_x}, {orig_y})")
                self.draw_frame()
    
    def draw_frame(self):
        """Draw current frame with zones and lines"""
        frame = self.current_frame.copy()
        
        # Draw zone polygon
        if len(self.zone_points) >= 3:
            pts = np.array(self.zone_points, np.int32)
            pts = pts.reshape((-1, 1, 2))
            cv2.polylines(frame, [pts], True, (0, 255, 0), 2)
            overlay = frame.copy()
            cv2.fillPoly(overlay, [pts], (0, 255, 0))
            cv2.addWeighted(overlay, 0.2, frame, 0.8, 0, frame)
        
        # Draw zone points
        for i, point in enumerate(self.zone_points):
            cv2.circle(frame, tuple(point), 5, (0, 255, 0), -1)
            cv2.putText(frame, f"Z{i+1}", (point[0]+10, point[1]), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Draw parking line
        if len(self.parking_line_points) >= 2:
            pts = np.array(self.parking_line_points, np.int32)
            cv2.polylines(frame, [pts], False, (0, 255, 255), 3)
        
        # Draw parking line points
        for i, point in enumerate(self.parking_line_points):
            cv2.circle(frame, tuple(point), 5, (0, 255, 255), -1)
            cv2.putText(frame, f"P{i+1}", (point[0]+10, point[1]), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
        
        # Resize frame to fit window size while maintaining aspect ratio
        original_height, original_width = frame.shape[:2]
        scale = min(self.window_width / original_width, self.window_height / original_height)
        new_width = int(original_width * scale)
        new_height = int(original_height * scale)
        
        # Store scale factors for coordinate conversion
        self.scale_x = new_width / original_width
        self.scale_y = new_height / original_height
        
        # Resize frame
        frame_resized = cv2.resize(frame, (new_width, new_height))
        
        # Create a black canvas of window size
        display_frame = np.zeros((self.window_height, self.window_width, 3), dtype=np.uint8)
        
        # Center the resized frame on the canvas
        self.y_offset = (self.window_height - new_height) // 2
        self.x_offset = (self.window_width - new_width) // 2
        display_frame[self.y_offset:self.y_offset+new_height, self.x_offset:self.x_offset+new_width] = frame_resized
        
        # Draw instructions on display frame
        mode_text = "ZONE" if self.mode == "zone" else "PARKING LINE"
        cv2.putText(display_frame, f"Mode: {mode_text}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(display_frame, "Z: Zone | P: Parking line | C: Clear | S: Save | Q: Quit", 
                   (10, self.window_height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        cv2.imshow(self.window_name, display_frame)
    
    def clear_current(self):
        """Clear current mode's points"""
        if self.mode == "zone":
            self.zone_points = []
            print("Zone points cleared")
        elif self.mode == "parking_line":
            self.parking_line_points = []
            print("Parking line points cleared")
        self.draw_frame()
    
    def run(self):
        """Run the configuration tool"""
        # Load existing config if available
        self.load_config()
        
        # Open video
        self.cap = cv2.VideoCapture(self.video_source)
        if not self.cap.isOpened():
            print(f"Error: Could not open video source: {self.video_source}")
            return
        
        # Read first frame
        ret, frame = self.cap.read()
        if not ret:
            print("Error: Could not read frame from video")
            return
        
        # Crop frame to reduce size (same crop as in main application)
        frame = self._crop_frame(frame)
        
        self.original_frame = frame.copy()
        self.current_frame = frame
        
        # Create window with specified size and set mouse callback
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, self.window_width, self.window_height)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)
        
        # Draw initial frame
        self.draw_frame()
        
        print("\n" + "="*60)
        print("Zone Configuration Tool")
        print("="*60)
        print("Instructions:")
        print("  - Press 'z' to switch to ZONE mode (green)")
        print("  - Press 'p' to switch to PARKING LINE mode (yellow)")
        print("  - Click on the video to add points")
        print("  - Press 'c' to clear current mode's points")
        print("  - Press 's' to save configuration to JSON")
        print("  - Press 'q' to quit")
        print("="*60)
        
        while True:
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                break
            elif key == ord('z'):
                self.mode = "zone"
                print("Switched to ZONE mode")
                self.draw_frame()
            elif key == ord('p'):
                self.mode = "parking_line"
                print("Switched to PARKING LINE mode")
                self.draw_frame()
            elif key == ord('c'):
                self.clear_current()
            elif key == ord('s'):
                if len(self.zone_points) >= 3:
                    if len(self.parking_line_points) >= 2:
                        self.save_config()
                    else:
                        print("Warning: Parking line needs at least 2 points")
                else:
                    print("Warning: Zone needs at least 3 points to form a polygon")
            elif key == ord('n'):
                # Next frame
                ret, frame = self.cap.read()
                if ret:
                    # Crop frame to reduce size (same crop as in main application)
                    frame = self._crop_frame(frame)
                    self.original_frame = frame.copy()
                    self.current_frame = frame
                    self.draw_frame()
                else:
                    print("End of video")
            elif key == ord('b'):
                # Previous frame (reset to beginning)
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
                if ret:
                    # Crop frame to reduce size (same crop as in main application)
                    frame = self._crop_frame(frame)
                    self.original_frame = frame.copy()
                    self.current_frame = frame
                    self.draw_frame()
        
        # Cleanup
        self.cap.release()
        cv2.destroyAllWindows()
        
        # Ask to save before quitting
        if len(self.zone_points) >= 3 or len(self.parking_line_points) >= 2:
            save = input("\nSave configuration before quitting? (y/n): ")
            if save.lower() == 'y':
                self.save_config()


def main():
    """Main function"""
    import sys
    
    # Get video source from config or command line
    video_source = VIDEO_SOURCE
    if len(sys.argv) > 1:
        video_source = sys.argv[1]
    
    print(f"Using video source: {video_source}")
    
    configurator = ZoneConfigurator(video_source)
    configurator.run()


if __name__ == "__main__":
    main()

