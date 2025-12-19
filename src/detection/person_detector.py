"""
Person detection using YOLOv8.
"""
import cv2
import numpy as np
from ultralytics import YOLO
from src.config import config


class PersonDetector:
    """Detects humans in frames using YOLO."""
    
    def __init__(self):
        print("Loading YOLOv8 model...")
        self.model = YOLO(config.detection.model_path)
        self.conf_threshold = config.detection.person_confidence
    
    def detect(self, frame):
        """
        Detect persons in frame.
        
        Args:
            frame: BGR image (OpenCV format)
            
        Returns:
            List of bounding boxes as (x1, y1, x2, y2) tuples
        """
        results = self.model.predict(
            source=frame, 
            classes=[0],  # person class
            conf=self.conf_threshold, 
            verbose=False
        )
        
        boxes = []
        for box in results[0].boxes:
            coords = tuple(box.xyxy[0].cpu().numpy())
            boxes.append(coords)
        
        return boxes
    
    @staticmethod
    def check_brightness(frame):
        """Check if frame is too dark."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return np.mean(gray) >= config.detection.min_brightness

