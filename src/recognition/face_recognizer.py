"""
Face recognition using DeepFace.
"""
import os
import cv2
from deepface import DeepFace
from src.config import config


class FaceRecognizer:
    """Identifies faces by comparing to known faces database."""
    
    def __init__(self):
        self.known_dir = config.recognition.known_faces_dir
        self.tolerance = config.recognition.face_tolerance
        self.model_name = config.recognition.model_name
        self._validate_known_faces()
    
    def _validate_known_faces(self):
        """Ensure known_faces directory exists."""
        if not os.path.exists(self.known_dir):
            os.makedirs(self.known_dir)
            print(f"⚠️  Created {self.known_dir}/ - add photos of known people")
            return
        
        images = self._get_known_images()
        if images:
            print(f"✓ Found {len(images)} known face(s): {', '.join(images)}")
        else:
            print(f"⚠️  No images in {self.known_dir}/ - add photos")
    
    def _get_known_images(self):
        """Get list of image files in known_faces/."""
        if not os.path.exists(self.known_dir):
            return []
        return [f for f in os.listdir(self.known_dir) 
                if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    def identify(self, frame, person_bbox=None):
        """
        Identify faces in frame.
        
        Args:
            frame: BGR image
            person_bbox: Optional (x1, y1, x2, y2) to crop search area
            
        Returns:
            List of (name, face_location) tuples
        """
        # Crop to person region if provided
        if person_bbox:
            x1, y1, x2, y2 = map(int, person_bbox)
            x1, y1 = max(0, x1), max(0, y1)
            crop = frame[y1:y2, x1:x2]
            offset = (x1, y1)
        else:
            crop = frame
            offset = (0, 0)
        
        # Detect faces
        try:
            faces = DeepFace.extract_faces(
                crop, 
                detector_backend="opencv",
                enforce_detection=False
            )
        except Exception:
            return []
        
        results = []
        for face_data in faces:
            if face_data["confidence"] < 0.5:
                continue
            
            region = face_data["facial_area"]
            face_loc = (
                region["y"] + offset[1],      # top
                region["x"] + region["w"] + offset[0],  # right
                region["y"] + region["h"] + offset[1],  # bottom
                region["x"] + offset[0]       # left
            )
            
            name = self._match_face(crop, region)
            results.append((name, face_loc))
        
        return results
    
    def _match_face(self, img, facial_area):
        """Match detected face against known faces database."""
        known_images = self._get_known_images()
        if not known_images:
            return "Unknown"
        
        # Crop face
        x, y, w, h = facial_area["x"], facial_area["y"], facial_area["w"], facial_area["h"]
        face_crop = img[y:y+h, x:x+w]
        
        if face_crop.size == 0:
            return "Unknown"
        
        # Save temp file for DeepFace
        temp_path = "/tmp/hostel_temp_face.jpg"
        cv2.imwrite(temp_path, face_crop)
        
        best_match = "Unknown"
        best_distance = float('inf')
        
        for known_file in known_images:
            known_path = os.path.join(self.known_dir, known_file)
            try:
                result = DeepFace.verify(
                    temp_path, known_path,
                    enforce_detection=False,
                    model_name=self.model_name
                )
                
                distance = result["distance"]
                if distance < self.tolerance and distance < best_distance:
                    best_distance = distance
                    best_match = os.path.splitext(known_file)[0]
            except Exception:
                continue
        
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        return best_match

