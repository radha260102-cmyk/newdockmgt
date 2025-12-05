"""
Dock Management Logic Module
Implements the business rules for dock state determination
"""
from dock_utils.helpers import is_point_in_zone
import config
import time


class DockManager:
    """Manages dock state based on detection results"""
    
    def __init__(self, zone_coordinates=None, parking_line_points=None):
        """
        Initialize Dock Manager
        Args:
            zone_coordinates: List of (x, y) tuples defining the dock zone
            parking_line_points: List of (x, y) tuples defining the parking line (manually configured)
        """
        self.zone_coordinates = zone_coordinates or config.ZONE_COORDINATES
        self.parking_line_points = parking_line_points or config.PARKING_LINE_POINTS
        self.current_state = "UNKNOWN"
        self.state_history = []
        self.parking_line_touch_start_time = None  # Timestamp when truck first touched parking line
        self.wait_time_seconds = config.PARKING_LINE_WAIT_TIME
        self.not_touching_count = 0  # Count consecutive frames where truck is not touching (for grace period)
        self.grace_period_frames = config.PARKING_LINE_GRACE_PERIOD  # Number of consecutive "not touching" detections before resetting timer
    
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
        Rules:
        1. Truck in zone + NOT touching parking line + Human present = VIOLATION (RED)
        2. Truck in zone + NOT touching parking line + No human = YELLOW
        3. Truck in zone + Touching parking line + Wait time elapsed = GREEN
        4. No truck + (Human or No human) = GREEN
        
        Args:
            detection_summary: Dictionary with detection results
        Returns:
            str: State ('RED', 'YELLOW', 'GREEN')
        """
        truck_present = detection_summary['truck_present']
        human_present = detection_summary['human_present']
        trucks = detection_summary['trucks']
        current_time = time.time()
        
        # Rule 4: No truck = GREEN
        if not truck_present:
            self.parking_line_touch_start_time = None  # Reset timer
            self.current_state = "GREEN"
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
        
        # Rule 3: Truck in zone + Touching parking line
        if truck_in_zone and truck_touching_line:
            # Reset not touching counter since truck is touching
            self.not_touching_count = 0
            
            # Start or continue timer
            if self.parking_line_touch_start_time is None:
                self.parking_line_touch_start_time = current_time
                # Show YELLOW while waiting
                self.current_state = "YELLOW"
                return self.current_state
            
            # Check if wait time has elapsed
            elapsed_time = current_time - self.parking_line_touch_start_time
            if elapsed_time >= self.wait_time_seconds:
                # Wait time elapsed, turn GREEN
                self.current_state = "GREEN"
                return self.current_state
            else:
                # Still waiting, show YELLOW with countdown
                remaining_time = int(self.wait_time_seconds - elapsed_time)
                self.current_state = "YELLOW"  # Will show countdown in UI
                return self.current_state
        
        # Truck not touching line - use grace period before resetting timer
        if not truck_touching_line:
            self.not_touching_count += 1
            # Only reset timer after grace period (multiple consecutive "not touching" detections)
            if self.not_touching_count >= self.grace_period_frames:
                self.parking_line_touch_start_time = None
                self.not_touching_count = 0
        
        # Rule 1 & 2: Truck in zone + NOT touching parking line
        if truck_in_zone and not truck_touching_line:
            if human_present:
                # Rule 1: Violation
                self.current_state = "RED"
            else:
                # Rule 2: Warning
                self.current_state = "YELLOW"
            return self.current_state
        
        # Default: If truck exists but not in zone, consider it GREEN
        self.current_state = "GREEN"
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
