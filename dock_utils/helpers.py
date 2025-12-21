"""
Helper utility functions
"""
import cv2
import numpy as np


def is_point_in_zone(point, zone_coordinates):
    """
    Check if a point is inside a zone polygon
    Args:
        point: (x, y) tuple
        zone_coordinates: List of (x, y) tuples defining polygon vertices
    Returns:
        bool: True if point is inside zone
    """
    if zone_coordinates is None or len(zone_coordinates) < 3:
        return False
    
    x, y = point
    n = len(zone_coordinates)
    inside = False
    
    p1x, p1y = zone_coordinates[0]
    for i in range(1, n + 1):
        p2x, p2y = zone_coordinates[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    
    return inside


def check_line_inside_box(box, line_points):
    """
    Check if parking line is inside or intersects with the truck's bounding box
    Args:
        box: Bounding box coordinates (x1, y1, x2, y2)
        line_points: List of points defining the line [(x1, y1), (x2, y2)]
    Returns:
        bool: True if line is inside or intersects the box
    """
    if len(line_points) < 2:
        return False
    
    x1, y1, x2, y2 = box
    box_left = min(x1, x2)
    box_right = max(x1, x2)
    box_top = min(y1, y2)
    box_bottom = max(y1, y2)
    
    # Check if any point of the line is inside the box
    for point in line_points:
        px, py = point
        if box_left <= px <= box_right and box_top <= py <= box_bottom:
            return True
    
    # Check if line segment intersects with box edges
    # Check each line segment
    for i in range(len(line_points) - 1):
        p1 = line_points[i]
        p2 = line_points[i + 1]
        
        # Check if line segment intersects any edge of the box
        # Top edge
        if line_segment_intersects((box_left, box_top), (box_right, box_top), p1, p2):
            return True
        # Bottom edge
        if line_segment_intersects((box_left, box_bottom), (box_right, box_bottom), p1, p2):
            return True
        # Left edge
        if line_segment_intersects((box_left, box_top), (box_left, box_bottom), p1, p2):
            return True
        # Right edge
        if line_segment_intersects((box_right, box_top), (box_right, box_bottom), p1, p2):
            return True
    
    return False


def line_segment_intersects(line1_start, line1_end, line2_start, line2_end):
    """
    Check if two line segments intersect
    Uses the cross product method
    """
    def ccw(A, B, C):
        """Check if three points are in counter-clockwise order"""
        return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])
    
    A, B = line1_start, line1_end
    C, D = line2_start, line2_end
    
    # Check if line segments AB and CD intersect
    return ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)


def is_bbox_in_zone(bbox, zone_coordinates):
    """
    Check if a bounding box is inside or intersects with the zone
    Args:
        bbox: [x1, y1, x2, y2] bounding box coordinates
        zone_coordinates: List of (x, y) tuples defining polygon vertices
    Returns:
        bool: True if bbox is at least partially inside zone
    """
    if zone_coordinates is None or len(zone_coordinates) < 3:
        return True  # If no zone configured, allow all detections
    
    x1, y1, x2, y2 = bbox
    
    # Check if any corner of the bounding box is inside the zone
    corners = [
        (x1, y1),  # Top-left
        (x2, y1),  # Top-right
        (x2, y2),  # Bottom-right
        (x1, y2)   # Bottom-left
    ]
    
    # Check center point
    center = ((x1 + x2) / 2, (y1 + y2) / 2)
    corners.append(center)
    
    # If any corner or center is inside the zone, consider it inside
    for point in corners:
        if is_point_in_zone(point, zone_coordinates):
            return True
    
    return False


def is_human_bbox_in_zone(bbox, zone_coordinates, check_points_config):
    """
    Check if a human bounding box is inside the zone based on configurable check points
    Args:
        bbox: [x1, y1, x2, y2] bounding box coordinates
        zone_coordinates: List of (x, y) tuples defining polygon vertices
        check_points_config: Dictionary with keys:
            - 'top_left': bool - Check top-left corner (x1, y1)
            - 'top_right': bool - Check top-right corner (x2, y1)
            - 'bottom_right': bool - Check bottom-right corner (x2, y2)
            - 'bottom_left': bool - Check bottom-left corner (x1, y2)
            - 'center': bool - Check center point ((x1+x2)/2, (y1+y2)/2)
    Returns:
        bool: True if any enabled check point is inside the zone
    """
    if zone_coordinates is None or len(zone_coordinates) < 3:
        return True  # If no zone configured, allow all detections
    
    # Default: if no config provided, use all points (backward compatibility)
    if check_points_config is None:
        check_points_config = {
            'top_left': True,
            'top_right': True,
            'bottom_right': True,
            'bottom_left': True,
            'center': True
        }
    
    x1, y1, x2, y2 = bbox
    
    # Build list of points to check based on configuration
    points_to_check = []
    
    if check_points_config.get('top_left', False):
        points_to_check.append((x1, y1))  # Top-left corner
    
    if check_points_config.get('top_right', False):
        points_to_check.append((x2, y1))  # Top-right corner
    
    if check_points_config.get('bottom_right', False):
        points_to_check.append((x2, y2))  # Bottom-right corner
    
    if check_points_config.get('bottom_left', False):
        points_to_check.append((x1, y2))  # Bottom-left corner
    
    if check_points_config.get('center', False):
        points_to_check.append(((x1 + x2) / 2, (y1 + y2) / 2))  # Center point
    
    # If no points are enabled, default to checking all (safety fallback)
    if len(points_to_check) == 0:
        points_to_check = [
            (x1, y1),  # Top-left
            (x2, y1),  # Top-right
            (x2, y2),  # Bottom-right
            (x1, y2),  # Bottom-left
            ((x1 + x2) / 2, (y1 + y2) / 2)  # Center
        ]
    
    # Check if any enabled point is inside the zone
    for point in points_to_check:
        if is_point_in_zone(point, zone_coordinates):
            return True
    
    return False