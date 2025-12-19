"""
Video recording module with auto-stop reminder.
"""
import os
import cv2
import time
import threading
from datetime import datetime
from src.config import config


class VideoRecorder:
    """Records video to files with reminder system."""
    
    def __init__(self):
        self.output_dir = config.recording.output_dir
        self.fps = config.recording.fps
        self.codec = config.recording.codec
        
        self.writer = None
        self.recording = False
        self.current_file = None
        self.frame_count = 0
        self.start_time = None
        
        # Reminder system
        self.reminder_thread = None
        self.reminder_acknowledged = False
        self.last_reminder_time = None
        self.reminder_count = 0
        self.on_reminder = None      # Callback to send reminder
        self.on_auto_stop = None     # Callback when auto-stopped
        
        os.makedirs(self.output_dir, exist_ok=True)
    
    def start(self, frame_size):
        """Start recording."""
        if self.recording:
            return self.current_file
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.current_file = os.path.join(self.output_dir, f"{timestamp}.mp4")
        
        fourcc = cv2.VideoWriter_fourcc(*self.codec)
        self.writer = cv2.VideoWriter(
            self.current_file, fourcc, self.fps, frame_size
        )
        
        self.recording = True
        self.frame_count = 0
        self.start_time = time.time()
        self.reminder_acknowledged = False
        self.last_reminder_time = time.time()
        self.reminder_count = 0
        
        # Start reminder thread
        self._start_reminder_thread()
        
        print(f"🔴 Recording started: {self.current_file}")
        return self.current_file
    
    def stop(self):
        """Stop recording and finalize file."""
        if not self.recording:
            return None
        
        self.recording = False
        if self.writer:
            self.writer.release()
            self.writer = None
        
        result = self.current_file
        duration = time.time() - self.start_time if self.start_time else 0
        print(f"⏹️ Recording stopped: {result} ({self.frame_count} frames, {duration:.0f}s)")
        
        self.current_file = None
        self.frame_count = 0
        self.start_time = None
        return result
    
    def write_frame(self, frame):
        """Write a frame to the recording."""
        if self.recording and self.writer:
            self.writer.write(frame)
            self.frame_count += 1
    
    def is_recording(self):
        """Check if currently recording."""
        return self.recording
    
    def get_duration(self):
        """Get current recording duration in seconds."""
        if not self.recording or not self.start_time:
            return 0
        return time.time() - self.start_time
    
    def acknowledge_reminder(self):
        """User acknowledged the reminder - reset timer."""
        self.reminder_acknowledged = True
        self.last_reminder_time = time.time()
        self.reminder_count = 0
        print("✓ Recording reminder acknowledged")
    
    def _start_reminder_thread(self):
        """Start background thread for reminders."""
        self.reminder_thread = threading.Thread(target=self._reminder_loop, daemon=True)
        self.reminder_thread.start()
    
    def _reminder_loop(self):
        """Check and send reminders."""
        # First reminder after 10 minutes
        first_interval = 10 * 60  # 10 minutes
        followup_interval = 30 * 60  # 30 minutes
        max_reminders = 3  # Stop after 3 unanswered reminders
        
        while self.recording:
            time.sleep(30)  # Check every 30 seconds
            
            if not self.recording:
                break
            
            elapsed = time.time() - self.last_reminder_time
            
            # Determine interval based on reminder count
            if self.reminder_count == 0:
                interval = first_interval
            else:
                interval = followup_interval
            
            if elapsed >= interval:
                self.reminder_count += 1
                self.last_reminder_time = time.time()
                self.reminder_acknowledged = False
                
                duration = self.get_duration()
                duration_min = duration / 60
                
                if self.reminder_count >= max_reminders:
                    # Auto-stop after max reminders
                    print(f"⚠️ Recording auto-stopped (no response after {self.reminder_count} reminders)")
                    if self.on_auto_stop:
                        self.on_auto_stop()
                    self.stop()
                    break
                else:
                    # Send reminder
                    print(f"📢 Recording reminder #{self.reminder_count} ({duration_min:.0f} min)")
                    if self.on_reminder:
                        self.on_reminder(self.reminder_count, duration_min)
    
    def list_recordings(self):
        """List all recording files."""
        if not os.path.exists(self.output_dir):
            return []
        
        files = []
        for f in sorted(os.listdir(self.output_dir), reverse=True):
            if f.endswith('.mp4'):
                path = os.path.join(self.output_dir, f)
                size_mb = os.path.getsize(path) / (1024 * 1024)
                files.append((f, size_mb))
        return files
