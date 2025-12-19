"""
Person tracking with identity caching.
Avoids redundant face recognition when person hasn't moved.
"""
import time
import numpy as np
from src.config import config


class PersonTracker:
    """Tracks persons across frames and caches their identities."""
    
    def __init__(self):
        self.tracked = []  # List of tracked person data
        self.last_person_count = 0
        self.move_threshold = config.tracking.bbox_move_threshold
        self.recheck_interval = config.tracking.recheck_interval
    
    @staticmethod
    def _bbox_distance(box1, box2):
        """Calculate center-to-center distance between bboxes."""
        cx1 = (box1[0] + box1[2]) / 2
        cy1 = (box1[1] + box1[3]) / 2
        cx2 = (box2[0] + box2[2]) / 2
        cy2 = (box2[1] + box2[3]) / 2
        return np.sqrt((cx1 - cx2)**2 + (cy1 - cy2)**2)
    
    def needs_face_check(self, current_boxes):
        """
        Determine if face recognition should run.
        
        Returns True if:
        - Person count changed
        - Any person moved significantly
        - Periodic recheck time elapsed
        """
        now = time.time()
        
        # Person count changed
        if len(current_boxes) != self.last_person_count:
            return True
        
        # No people
        if len(current_boxes) == 0:
            return False
        
        # Check each detected person
        for curr_box in current_boxes:
            matched = False
            for t in self.tracked:
                dist = self._bbox_distance(curr_box, t["bbox"])
                if dist < self.move_threshold:
                    matched = True
                    # Periodic refresh check
                    if now - t["last_check"] > self.recheck_interval:
                        return True
                    break
            
            # New person (no match)
            if not matched:
                return True
        
        return False
    
    def update(self, boxes, faces_per_box):
        """Update tracked persons with new detection results."""
        now = time.time()
        self.last_person_count = len(boxes)
        
        new_tracked = []
        for i, box in enumerate(boxes):
            entry = {
                "bbox": box,
                "name": None,
                "face_loc": None,
                "last_check": now
            }
            
            if i < len(faces_per_box) and faces_per_box[i]:
                name, loc = faces_per_box[i][0]
                entry["name"] = name
                entry["face_loc"] = loc
            
            new_tracked.append(entry)
        
        self.tracked = new_tracked
    
    def get_cached(self):
        """Get cached identities for drawing."""
        return [
            (t["name"], t["face_loc"], t["bbox"]) 
            for t in self.tracked
        ]

