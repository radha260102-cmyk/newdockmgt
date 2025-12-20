"""
Dock Management Logic Module
Implements the business rules for dock state determination
"""
from dock_utils.helpers import is_point_in_zone
import config
import time
import threading
import urllib.request
import urllib.error
import json


class DockManager:
    """Manages dock state based on detection results"""
    
    def __init__(self, zone_coordinates=None, parking_line_points=None, plc_manager=None):
        """
        Initialize Dock Manager
        Args:
            zone_coordinates: List of (x, y) tuples defining the dock zone
            parking_line_points: List of (x, y) tuples defining the parking line (manually configured)
            plc_manager: PLCManager instance (optional, will be created if None and ENABLE_PLC is True)
        """
        self.zone_coordinates = zone_coordinates or config.ZONE_COORDINATES
        self.parking_line_points = parking_line_points or config.PARKING_LINE_POINTS
        self.current_state = "UNKNOWN"
        self.previous_state = "UNKNOWN"  # Track previous state to detect changes
        self.state_history = []
        self.parking_line_touch_start_time = None  # Timestamp when truck first touched parking line
        self.wait_time_seconds = config.PARKING_LINE_WAIT_TIME
        self.not_touching_count = 0  # Count consecutive frames where truck is not touching (for grace period)
        self.grace_period_frames = config.PARKING_LINE_GRACE_PERIOD  # Number of consecutive "not touching" detections before resetting timer
        self.last_detection_summary = None  # Store last detection summary for API notes
        
        # Initialize PLC manager if enabled
        if config.ENABLE_PLC:
            if plc_manager is None:
                from src.plc_manager import PLCManager
                self.plc_manager = PLCManager()
            else:
                self.plc_manager = plc_manager
        else:
            self.plc_manager = None
    
    def update_zone(self, zone_coordinates):
        """Update zone coordinates"""
        self.zone_coordinates = zone_coordinates
    
    def update_parking_line(self, parking_line_points):
        """Update parking line points"""
        self.parking_line_points = parking_line_points
    
    def is_truck_in_zone(self, truck_bbox):
        """
        Check if truck is inside the dock zone
        Args:
            truck_bbox: [x1, y1, x2, y2] bounding box coordinates
        Returns:
            bool: True if truck is in zone
        """
        if self.zone_coordinates is None:
            return False
        
        # Check if truck center or bottom center is in zone
        truck_center = ((truck_bbox[0] + truck_bbox[2]) / 2, (truck_bbox[1] + truck_bbox[3]) / 2)
        truck_bottom = ((truck_bbox[0] + truck_bbox[2]) / 2, truck_bbox[3])
        
        return (is_point_in_zone(truck_center, self.zone_coordinates) or 
                is_point_in_zone(truck_bottom, self.zone_coordinates))
    
    def is_truck_touching_parking_line(self, truck_bbox):
        """
        Check if parking line is inside the truck's bounding box
        Args:
            truck_bbox: [x1, y1, x2, y2] bounding box coordinates
        Returns:
            bool: True if parking line is inside or intersects truck box
        """
        if self.parking_line_points is None or len(self.parking_line_points) < 2:
            return False
        
        from dock_utils.helpers import check_line_inside_box
        return check_line_inside_box(truck_bbox, self.parking_line_points)
    
    def determine_state(self, detection_summary):
        """
        Determine dock state based on detection results
        Rules (priority order):
        1. No truck = GREEN
        2. Truck in zone + Touching parking line + Counter completed = GREEN (regardless of human)
        3. Truck in zone + Touching parking line + Counter running + Human present = RED
        4. Truck in zone + Touching parking line + Counter running + No human = YELLOW
        5. Truck in zone + NOT touching parking line + Human present = RED (violation)
        6. Truck in zone + NOT touching parking line + No human = YELLOW
        
        Args:
            detection_summary: Dictionary with detection results
        Returns:
            str: State ('RED', 'YELLOW', 'GREEN')
        """
        truck_present = detection_summary['truck_present']
        human_present = detection_summary['human_present']
        trucks = detection_summary['trucks']
        current_time = time.time()
        
        # Store detection info for API calls
        self.last_detection_summary = detection_summary
        
        # Rule 1: No truck = GREEN
        if not truck_present:
            self.parking_line_touch_start_time = None  # Reset timer
            self.current_state = "GREEN"
            self._handle_state_change("GREEN")
            return self.current_state
        
        # Check if any truck is in zone
        truck_in_zone = False
        truck_touching_line = False
        
        for truck in trucks:
            truck_bbox = truck['bbox']
            if self.is_truck_in_zone(truck_bbox):
                truck_in_zone = True
                if self.is_truck_touching_parking_line(truck_bbox):
                    truck_touching_line = True
                    break  # If one truck touches, we're good
        
        # Rule 2, 3 & 4: Truck in zone + Touching parking line
        # Counter starts/continues even if human is present (RED state can continue with counter)
        # Scenario: If already RED (human present, truck not touching line), and truck touches line:
        #   - Counter starts immediately
        #   - Light stays RED during countdown (because human is present)
        #   - When counter completes, switches to GREEN (regardless of human)
        if truck_in_zone and truck_touching_line:
            # Reset not touching counter since truck is touching
            self.not_touching_count = 0
            
            # Start or continue timer (counter always starts when truck touches line)
            # This works even if we transitioned from RED state (human present, not touching)
            if self.parking_line_touch_start_time is None:
                self.parking_line_touch_start_time = current_time
            
            # Check if wait time has elapsed
            elapsed_time = current_time - self.parking_line_touch_start_time
            if elapsed_time >= self.wait_time_seconds:
                # Wait time elapsed = turn GREEN (regardless of human presence)
                self.current_state = "GREEN"
                self._handle_state_change("GREEN")
                return self.current_state
            else:
                # Counter still running - show RED if human present, YELLOW if no human
                # Note: RED can continue from previous state (human + not touching) into this state
                if human_present:
                    # Human present during countdown = show RED (violation)
                    # Counter continues running in background, will switch to GREEN when complete
                    self.current_state = "RED"
                    self._handle_state_change("RED")
                else:
                    # No human during countdown = show YELLOW (counter running)
                    remaining_time = int(self.wait_time_seconds - elapsed_time)
                    self.current_state = "YELLOW"  # Will show countdown in UI
                    self._handle_state_change("YELLOW")
                return self.current_state
        
        # Rule 5: Truck in zone + NOT touching parking line + Human present = RED
        # This is a violation - truck not properly parked and human in zone
        if truck_in_zone and human_present:
            # Human in zone + truck not touching line = violation, show RED
            self.current_state = "RED"
            self._handle_state_change("RED")
            return self.current_state
        
        # Truck not touching line - use grace period before resetting timer
        if not truck_touching_line:
            self.not_touching_count += 1
            # Only reset timer after grace period (multiple consecutive "not touching" detections)
            if self.not_touching_count >= self.grace_period_frames:
                self.parking_line_touch_start_time = None
                self.not_touching_count = 0
        
        # Rule 6: Truck in zone + NOT touching parking line + NO human
        if truck_in_zone and not truck_touching_line:
            # Warning - truck not properly parked
            self.current_state = "YELLOW"
            self._handle_state_change("YELLOW")
            return self.current_state
        
        # Default: If truck exists but not in zone, consider it GREEN
        self.current_state = "GREEN"
        self._handle_state_change("GREEN")
        return self.current_state
    
    def get_parking_wait_remaining(self):
        """Get remaining wait time in seconds if truck is touching parking line"""
        if self.parking_line_touch_start_time is None:
            return None
        elapsed = time.time() - self.parking_line_touch_start_time
        remaining = max(0, self.wait_time_seconds - elapsed)
        return int(remaining) if remaining > 0 else None
    
    def is_truck_touching_parking_line_debug(self, truck_bbox):
        """Debug version that returns line position info"""
        if self.parking_line_points is None or len(self.parking_line_points) < 2:
            return False, "No parking line configured"
        
        from dock_utils.helpers import check_line_inside_box
        is_inside = check_line_inside_box(truck_bbox, self.parking_line_points)
        
        # Count how many line points are inside the box
        x1, y1, x2, y2 = truck_bbox
        box_left = min(x1, x2)
        box_right = max(x1, x2)
        box_top = min(y1, y2)
        box_bottom = max(y1, y2)
        
        points_inside = 0
        for point in self.parking_line_points:
            px, py = point
            if box_left <= px <= box_right and box_top <= py <= box_bottom:
                points_inside += 1
        
        return is_inside, f"Line points inside box: {points_inside}/{len(self.parking_line_points)}"
    
    def get_state(self):
        """Get current dock state"""
        return self.current_state
    
    def get_state_info(self):
        """Get detailed state information"""
        return {
            'state': self.current_state,
            'zone_configured': self.zone_coordinates is not None,
            'parking_line_configured': self.parking_line_points is not None
        }
    
    def _call_api(self, url):
        """
        Call API endpoint in a separate thread (non-blocking)
        Args:
            url: API URL to call
        """
        def make_request():
            try:
                request = urllib.request.Request(url)
                with urllib.request.urlopen(request, timeout=2) as response:
                    status_code = response.getcode()
                    if status_code == 200:
                        print(f"✓ API call successful: {url}")
                    else:
                        print(f"⚠ API call returned status {status_code}: {url}")
            except urllib.error.URLError as e:
                print(f"✗ API call failed: {url} - Error: {e}")
            except Exception as e:
                print(f"✗ API call error: {url} - Error: {e}")
        
        # Call API in background thread to avoid blocking
        thread = threading.Thread(target=make_request, daemon=True)
        thread.start()
    
    def _call_dock_status_api(self, vehicle_status, human_presence, notes):
        """
        Call dock status API endpoint with JSON payload in a separate thread (non-blocking)
        Args:
            vehicle_status: "placed" or "not_placed"
            human_presence: "present" or "not_present"
            notes: Descriptive notes string
        """
        def make_request():
            try:
                payload = {
                    "vehicle_status": vehicle_status,
                    "human_presence": human_presence,
                    "notes": notes
                }
                data = json.dumps(payload).encode('utf-8')
                
                request = urllib.request.Request(
                    config.DOCK_STATUS_API_URL,
                    data=data,
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
                
                with urllib.request.urlopen(request, timeout=3) as response:
                    status_code = response.getcode()
                    if status_code == 200:
                        print(f"✓ Dock status API call successful: {vehicle_status}, {human_presence}")
                    else:
                        print(f"⚠ Dock status API returned status {status_code}")
            except urllib.error.URLError as e:
                print(f"✗ Dock status API call failed: {e}")
            except Exception as e:
                print(f"✗ Dock status API error: {e}")
        
        # Call API in background thread to avoid blocking
        thread = threading.Thread(target=make_request, daemon=True)
        thread.start()
    
    def _handle_state_change(self, new_state):
        """
        Handle state changes and call appropriate APIs and update PLC
        Args:
            new_state: New state ('RED', 'YELLOW', 'GREEN')
        """
        # Only process if state actually changed
        if new_state == self.previous_state:
            return
        
        print(f"State changed: {self.previous_state} -> {new_state}")
        
        # Get detection info for generating notes
        truck_present = False
        human_present = False
        truck_in_zone = False
        truck_touching_line = False
        
        if self.last_detection_summary:
            truck_present = self.last_detection_summary.get('truck_present', False)
            human_present = self.last_detection_summary.get('human_present', False)
            trucks = self.last_detection_summary.get('trucks', [])
            
            # Check truck position
            for truck in trucks:
                truck_bbox = truck['bbox']
                if self.is_truck_in_zone(truck_bbox):
                    truck_in_zone = True
                    if self.is_truck_touching_parking_line(truck_bbox):
                        truck_touching_line = True
                        break
        
        # Generate notes based on state
        notes = self._generate_notes(new_state, truck_present, human_present, truck_in_zone, truck_touching_line)
        
        # Determine vehicle_status and human_presence for dock status API
        vehicle_status = "placed" if (truck_present and truck_in_zone) else "not_placed"
        human_presence_str = "present" if human_present else "not_present"
        
        # Call speaker APIs if enabled (existing functionality)
        if config.ENABLE_API_CALLS:
            if new_state == "RED":
                # Call RED API when red light glows
                self._call_api(config.RED_API_URL)
            elif new_state == "YELLOW":
                # Call YELLOW API when yellow light glows
                self._call_api(config.YELLOW_API_URL)
            elif new_state == "GREEN":
                # Call STOP API when green light glows
                self._call_api(config.STOP_API_URL)
        
        # Call dock status API if enabled (new functionality)
        if config.ENABLE_DOCK_STATUS_API:
            self._call_dock_status_api(vehicle_status, human_presence_str, notes)
        
        # Update PLC coils (works independently of API calls, runs in separate thread)
        if self.plc_manager:
            self.plc_manager.update_state(new_state)
        
        # Update previous state
        self.previous_state = new_state
    
    def _generate_notes(self, state, truck_present, human_present, truck_in_zone, truck_touching_line):
        """
        Generate descriptive notes based on current state and detection results
        Args:
            state: Current state ('RED', 'YELLOW', 'GREEN')
            truck_present: Whether truck is detected
            human_present: Whether human is detected
            truck_in_zone: Whether truck is in dock zone
            truck_touching_line: Whether truck is touching parking line
        Returns:
            str: Descriptive notes
        """
        if state == "GREEN":
            if not truck_present:
                return "Dock cleared and ready for next vehicle"
            elif truck_in_zone and truck_touching_line:
                if human_present:
                    return "Truck properly placed at parking line. Wait time completed. Human present in zone"
                else:
                    return "Truck properly placed at parking line. Wait time completed. Dock ready"
            else:
                return "Dock status: Green - Ready"
        
        elif state == "RED":
            if truck_in_zone and not truck_touching_line and human_present:
                return "Violation: Truck in zone but not at parking line. Human present in dock area"
            elif truck_in_zone and truck_touching_line and human_present:
                wait_remaining = self.get_parking_wait_remaining()
                if wait_remaining:
                    return f"Truck at parking line. Wait time in progress ({wait_remaining}s remaining). Human present - violation"
                else:
                    return "Truck at parking line. Human present in dock area"
            else:
                return "Dock status: Red - Violation detected"
        
        elif state == "YELLOW":
            if truck_in_zone and not truck_touching_line:
                if human_present:
                    return "Warning: Truck in zone but not at parking line. Human present"
                else:
                    return "Warning: Truck in zone but not properly positioned at parking line"
            elif truck_in_zone and truck_touching_line:
                wait_remaining = self.get_parking_wait_remaining()
                if wait_remaining:
                    return f"Truck at parking line. Wait time in progress ({wait_remaining}s remaining). No human detected"
                else:
                    return "Truck at parking line. Positioning in progress"
            else:
                return "Dock status: Yellow - Warning"
        
        return f"Dock status: {state}"
    
    def cleanup(self):
        """Cleanup resources, stop PLC manager"""
        if self.plc_manager:
            self.plc_manager.stop()
