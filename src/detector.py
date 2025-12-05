"""
YOLO Detection Module
Handles object detection using YOLOv5 model
"""
import cv2
import numpy as np
import torch
import warnings
import config
from dock_utils.helpers import is_bbox_in_zone

# Suppress YOLOv5 deprecation warnings
warnings.filterwarnings('ignore', category=FutureWarning, message='.*torch.cuda.amp.autocast.*')


class YOLODetector:
    """YOLOv5-based object detector"""
    
    def __init__(self, model_path=None, zone_coordinates=None):
        """
        Initialize YOLOv5 detector
        Args:
            model_path: Path to YOLOv5 model file (.pt)
            zone_coordinates: Zone coordinates to filter detections (optional)
        """
        self.model_path = model_path or config.MODEL_PATH
        self.model = None
        self.zone_coordinates = zone_coordinates or config.ZONE_COORDINATES
        self.load_model()
    
    def update_zone(self, zone_coordinates):
        """Update zone coordinates for filtering"""
        self.zone_coordinates = zone_coordinates
    
    def load_model(self):
        """Load YOLOv5 model using torch.hub with GPU support"""
        # Determine device (GPU or CPU)
        if config.USE_GPU and torch.cuda.is_available():
            device = 'cuda'
            device_name = torch.cuda.get_device_name(0)
            print(f"GPU detected: {device_name}")
        else:
            device = 'cpu'
            if config.USE_GPU:
                print("GPU requested but not available. Using CPU.")
            else:
                print("Using CPU (GPU disabled in config).")
        
        # Override with explicit device if specified
        if config.DEVICE:
            device = config.DEVICE
            print(f"Using explicit device: {device}")
        
        try:
            # Load YOLOv5 model using torch.hub
            # This loads the custom model from local path
            self.model = torch.hub.load('ultralytics/yolov5', 'custom', path=self.model_path, trust_repo=True)
            self.model.conf = config.CONFIDENCE_THRESHOLD  # Set confidence threshold
            
            # YOLOv5 models from torch.hub automatically use GPU if available
            # But we can explicitly set device for batch processing
            if hasattr(self.model, 'device'):
                # Some YOLOv5 versions support explicit device setting
                try:
                    if device == 'cuda' and torch.cuda.is_available():
                        # Ensure model is on GPU
                        if next(self.model.model.parameters()).device.type != 'cuda':
                            self.model.model = self.model.model.cuda()
                        print(f"Model on GPU: {device_name}")
                    else:
                        if next(self.model.model.parameters()).device.type == 'cuda':
                            self.model.model = self.model.model.cpu()
                        print(f"Model on CPU")
                except:
                    # If device setting fails, model will use default (usually auto-detects GPU)
                    pass
            
            print(f"YOLOv5 model loaded successfully from {self.model_path}")
        except Exception as e:
            print(f"Error loading YOLOv5 model: {e}")
            print("\nTrying alternative loading method...")
            try:
                # Alternative: Try loading directly if yolov5 is installed as package
                import yolov5
                self.model = yolov5.load(self.model_path, device=device)
                self.model.conf = config.CONFIDENCE_THRESHOLD
                print(f"YOLOv5 model loaded successfully (alternative method) from {self.model_path} on {device.upper()}")
            except ImportError:
                print("\nYOLOv5 package not found. Installing...")
                print("Please run: pip install yolov5")
                raise
            except Exception as e2:
                print(f"Alternative loading also failed: {e2}")
                print("Please ensure the model file exists at the specified path")
                raise
    
    def detect(self, frame):
        """
        Perform detection on a frame
        Args:
            frame: Input image frame (numpy array)
        Returns:
            dict: Detection results with class names as keys
        """
        if self.model is None:
            return {}
        
        # YOLOv5 inference
        results = self.model(frame)
        
        detections = {
            'trucks': [],
            'humans': []
        }
        
        # YOLOv5 returns results in pandas DataFrame format
        # Access detections via results.pandas().xyxy[0]
        try:
            detections_df = results.pandas().xyxy[0]  # Get detections as DataFrame
            
            for idx, row in detections_df.iterrows():
                # Get class ID and confidence
                cls_id = int(row['class'])
                conf = float(row['confidence'])
                
                # Ignore forklifts (class 1)
                if cls_id == config.CLASS_IDS['forklift']:
                    continue
                
                # Get bounding box coordinates
                x1, y1, x2, y2 = int(row['xmin']), int(row['ymin']), int(row['xmax']), int(row['ymax'])
                
                # Get class name
                class_name = row['name']
                
                bbox = {
                    'bbox': [x1, y1, x2, y2],
                    'confidence': conf,
                    'class_id': cls_id,
                    'class_name': class_name
                }
                
                # Filter: Only include detections inside the zone
                if self.zone_coordinates and len(self.zone_coordinates) >= 3:
                    if not is_bbox_in_zone([x1, y1, x2, y2], self.zone_coordinates):
                        continue  # Skip detections outside the zone
                
                # Categorize detections by class ID
                if cls_id == config.CLASS_IDS['truck']:  # Class 2 is truck
                    detections['trucks'].append(bbox)
                elif cls_id == config.CLASS_IDS['person']:  # Class 0 is person
                    detections['humans'].append(bbox)
                # Forklifts (class 1) are ignored - already skipped above
        except Exception as e:
            # Fallback: try accessing results directly if pandas format not available
            print(f"Warning: Could not parse results as DataFrame: {e}")
            # Try alternative format
            if hasattr(results, 'xyxy') and len(results.xyxy) > 0:
                # Results in tensor format
                for detection in results.xyxy[0]:
                    if len(detection) >= 6:  # [x1, y1, x2, y2, conf, cls]
                        x1, y1, x2, y2, conf, cls_id = detection[:6]
                        cls_id = int(cls_id)
                        conf = float(conf)
                        
                        # Ignore forklifts (class 1)
                        if cls_id == config.CLASS_IDS['forklift']:
                            continue
                        
                        bbox = {
                            'bbox': [int(x1), int(y1), int(x2), int(y2)],
                            'confidence': conf,
                            'class_id': cls_id,
                            'class_name': f'class_{cls_id}'
                        }
                        
                        # Filter: Only include detections inside the zone
                        if self.zone_coordinates and len(self.zone_coordinates) >= 3:
                            if not is_bbox_in_zone([int(x1), int(y1), int(x2), int(y2)], self.zone_coordinates):
                                continue  # Skip detections outside the zone
                        
                        if cls_id == config.CLASS_IDS['truck']:
                            detections['trucks'].append(bbox)
                        elif cls_id == config.CLASS_IDS['person']:
                            detections['humans'].append(bbox)
        
        return detections
    
    def detect_batch(self, frames):
        """
        Perform batch detection on multiple frames
        Args:
            frames: List of input image frames (numpy arrays)
        Returns:
            list: List of detection results, one per frame
        """
        if self.model is None or len(frames) == 0:
            return [{'trucks': [], 'humans': []} for _ in frames]
        
        # YOLOv5 batch inference - pass list of frames
        results = self.model(frames)
        
        batch_detections = []
        
        # YOLOv5 returns results for each frame in the batch
        # results.pandas().xyxy is a list where each element corresponds to a frame
        try:
            results_list = results.pandas().xyxy  # List of DataFrames, one per frame
            
            for frame_idx, detections_df in enumerate(results_list):
                detections = {
                    'trucks': [],
                    'humans': []
                }
                
                for idx, row in detections_df.iterrows():
                    # Get class ID and confidence
                    cls_id = int(row['class'])
                    conf = float(row['confidence'])
                    
                    # Ignore forklifts (class 1)
                    if cls_id == config.CLASS_IDS['forklift']:
                        continue
                    
                    # Get bounding box coordinates
                    x1, y1, x2, y2 = int(row['xmin']), int(row['ymin']), int(row['xmax']), int(row['ymax'])
                    
                    # Get class name
                    class_name = row['name']
                    
                    bbox = {
                        'bbox': [x1, y1, x2, y2],
                        'confidence': conf,
                        'class_id': cls_id,
                        'class_name': class_name
                    }
                    
                    # Filter: Only include detections inside the zone
                    if self.zone_coordinates and len(self.zone_coordinates) >= 3:
                        if not is_bbox_in_zone([x1, y1, x2, y2], self.zone_coordinates):
                            continue  # Skip detections outside the zone
                    
                    # Categorize detections by class ID
                    if cls_id == config.CLASS_IDS['truck']:  # Class 2 is truck
                        detections['trucks'].append(bbox)
                    elif cls_id == config.CLASS_IDS['person']:  # Class 0 is person
                        detections['humans'].append(bbox)
                
                batch_detections.append(detections)
                
        except Exception as e:
            # Fallback: try accessing results directly if pandas format not available
            print(f"Warning: Could not parse batch results as DataFrame: {e}")
            # Try alternative format - process each frame result
            if hasattr(results, 'xyxy') and len(results.xyxy) > 0:
                for frame_idx, frame_results in enumerate(results.xyxy):
                    detections = {
                        'trucks': [],
                        'humans': []
                    }
                    
                    if len(frame_results) > 0:
                        for detection in frame_results:
                            if len(detection) >= 6:  # [x1, y1, x2, y2, conf, cls]
                                x1, y1, x2, y2, conf, cls_id = detection[:6]
                                cls_id = int(cls_id)
                                conf = float(conf)
                                
                                # Ignore forklifts (class 1)
                                if cls_id == config.CLASS_IDS['forklift']:
                                    continue
                                
                                bbox = {
                                    'bbox': [int(x1), int(y1), int(x2), int(y2)],
                                    'confidence': conf,
                                    'class_id': cls_id,
                                    'class_name': f'class_{cls_id}'
                                }
                                
                                # Filter: Only include detections inside the zone
                                if self.zone_coordinates and len(self.zone_coordinates) >= 3:
                                    if not is_bbox_in_zone([int(x1), int(y1), int(x2), int(y2)], self.zone_coordinates):
                                        continue  # Skip detections outside the zone
                                
                                if cls_id == config.CLASS_IDS['truck']:
                                    detections['trucks'].append(bbox)
                                elif cls_id == config.CLASS_IDS['person']:
                                    detections['humans'].append(bbox)
                    
                    batch_detections.append(detections)
            else:
                # If we can't parse results, return empty detections for all frames
                batch_detections = [{'trucks': [], 'humans': []} for _ in frames]
        
        # Ensure we return the same number of results as input frames
        while len(batch_detections) < len(frames):
            batch_detections.append({'trucks': [], 'humans': []})
        
        return batch_detections[:len(frames)]
    
    def get_detection_summary(self, detections):
        """
        Get summary of detections
        Args:
            detections: Detection results dictionary
        Returns:
            dict: Summary with counts and presence flags
        """
        return {
            'truck_present': len(detections['trucks']) > 0,
            'human_present': len(detections['humans']) > 0,
            'truck_count': len(detections['trucks']),
            'human_count': len(detections['humans']),
            'trucks': detections['trucks'],
            'humans': detections['humans']
        }
