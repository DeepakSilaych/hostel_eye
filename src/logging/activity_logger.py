"""
Activity logging with cooldown, intruder snapshots, and Telegram alerts.
"""
import os
import csv
import cv2
from datetime import datetime
from src.config import config


class ActivityLogger:
    """Logs detections to CSV and sends intruder alerts."""
    
    def __init__(self):
        self.last_seen = {}  # name -> timestamp
        self.intruders_dir = config.logging.intruders_dir
        self.log_file = config.logging.log_file
        self.known_cooldown = config.logging.known_cooldown
        self.unknown_cooldown = config.logging.unknown_cooldown
        self.notifier = None  # Set by SecuritySystem
        self._init_log_file()
    
    def _init_log_file(self):
        """Create CSV with headers if doesn't exist."""
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'name', 'image_path'])
    
    def _get_cooldown(self, name):
        """Get cooldown based on known/unknown status."""
        return self.known_cooldown if name != "Unknown" else self.unknown_cooldown
    
    def _should_log(self, name):
        """Check if cooldown has elapsed."""
        now = datetime.now()
        
        if name not in self.last_seen:
            return True
        
        elapsed = (now - self.last_seen[name]).total_seconds()
        return elapsed > self._get_cooldown(name)
    
    def log_detection(self, name, frame):
        """
        Log a detection if cooldown allows.
        
        Returns:
            True if logged, False if skipped
        """
        if not self._should_log(name):
            return False
        
        now = datetime.now()
        self.last_seen[name] = now
        
        image_path = ""
        
        if name == "Unknown":
            image_path = self._save_intruder(frame, now)
            print(f"🚨 INTRUDER DETECTED! Saved to {image_path}")
            
            # Send Telegram alert with photo
            if self.notifier:
                self.notifier.send_alert(
                    f"🚨 INTRUDER ALERT!\n"
                    f"Time: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"Unknown person detected!",
                    image_path
                )
        else:
            print(f"✓ {name} detected")
        
        # Append to CSV
        with open(self.log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                now.strftime("%Y-%m-%d %H:%M:%S"),
                name,
                image_path
            ])
        
        return True
    
    def _save_intruder(self, frame, timestamp):
        """Save intruder snapshot."""
        date_dir = os.path.join(self.intruders_dir, timestamp.strftime("%Y-%m-%d"))
        os.makedirs(date_dir, exist_ok=True)
        
        filename = timestamp.strftime("%H-%M-%S") + ".jpg"
        filepath = os.path.join(date_dir, filename)
        
        cv2.imwrite(filepath, frame)
        return filepath
