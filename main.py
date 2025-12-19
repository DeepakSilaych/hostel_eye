"""
Hostel Security System - Main Entry Point

Modular pipeline:
  Camera -> PersonDetector -> FaceRecognizer -> ActivityLogger

Telegram commands:
  /start, /stop, /status, /list, /add, /remove
  /record, /stoprecord, /recordings
"""
import cv2

from src.config import config
from src.detection import PersonDetector
from src.recognition import FaceRecognizer
from src.tracking import PersonTracker
from src.logging import ActivityLogger
from src.notifications import TelegramBot
from src.recording import VideoRecorder
from src.utils import draw_detection, draw_stats
from src.utils.drawing import draw_dark_warning


class SecuritySystem:
    """Main surveillance system with Telegram control."""
    
    def __init__(self):
        self.detector = PersonDetector()
        self.recognizer = FaceRecognizer()
        self.tracker = PersonTracker()
        self.logger = ActivityLogger()
        self.recorder = VideoRecorder()
        
        # Telegram bot
        self.bot = TelegramBot()
        self._setup_bot_callbacks()
        
        # Stats
        self.frames_processed = 0
        self.face_checks = 0
        
        # Control
        self.paused = False
        self.frame_size = None
        self.latest_frame = None  # For /snap command
    
    def _setup_bot_callbacks(self):
        """Wire up telegram commands to system actions."""
        self.bot.on_start = self._on_start
        self.bot.on_stop = self._on_stop
        self.bot.on_add_face = self._on_add_face
        self.bot.on_record_start = self._on_record_start
        self.bot.on_record_stop = self._on_record_stop
        self.bot.on_record_continue = self._on_record_continue
        self.bot.on_snap = self._on_snap
        self.bot.get_status = self._get_status
        self.bot.get_recordings = self._get_recordings
        
        # Wire up recorder reminders to bot
        self.recorder.on_reminder = self.bot.send_recording_reminder
        self.recorder.on_auto_stop = self.bot.send_auto_stop_notice
        
        # Replace logger's notifier with our bot
        self.logger.notifier = self.bot
    
    def _on_start(self):
        """Resume surveillance."""
        self.paused = False
        print("▶️  Surveillance resumed via Telegram")
    
    def _on_stop(self):
        """Pause surveillance."""
        self.paused = True
        print("⏸️  Surveillance paused via Telegram")
    
    def _on_add_face(self, name, path):
        """Reload recognizer when face added."""
        print(f"📸 Face added: {name}")
        self.recognizer = FaceRecognizer()
    
    def _on_record_start(self):
        """Start recording."""
        if self.recorder.is_recording():
            return None
        if self.frame_size:
            return self.recorder.start(self.frame_size)
        return None
    
    def _on_record_stop(self):
        """Stop recording."""
        return self.recorder.stop()
    
    def _on_record_continue(self):
        """Acknowledge reminder - continue recording."""
        self.recorder.acknowledge_reminder()
    
    def _on_snap(self):
        """Capture and return current frame."""
        if self.latest_frame is None:
            return None
        
        import os
        from datetime import datetime
        
        # Save to temp file
        snap_dir = "snaps"
        os.makedirs(snap_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path = os.path.join(snap_dir, f"{timestamp}.jpg")
        
        cv2.imwrite(path, self.latest_frame)
        return path
    
    def _get_status(self):
        """Return status string for /status command."""
        known = len(self.recognizer._get_known_images())
        rec_status = "🔴 Recording" if self.recorder.is_recording() else "⚪ Not recording"
        rec_duration = ""
        if self.recorder.is_recording():
            dur = self.recorder.get_duration()
            rec_duration = f" ({dur:.0f}s)"
        
        return (
            f"Frames: {self.frames_processed}\n"
            f"Face checks: {self.face_checks}\n"
            f"Known faces: {known}\n"
            f"Recording: {rec_status}{rec_duration}"
        )
    
    def _get_recordings(self):
        """Get list of recordings."""
        return self.recorder.list_recordings()
    
    def start(self):
        """Start the bot command listener."""
        self.bot.start_polling()
    
    def stop(self):
        """Stop the bot and recorder."""
        self.bot.stop_polling()
        if self.recorder.is_recording():
            self.recorder.stop()
    
    def is_active(self):
        """Check if surveillance should run."""
        return self.bot.surveillance_active and not self.paused
    
    def record_frame(self, frame):
        """Record raw frame (all frames, no graphics)."""
        if self.frame_size is None:
            h, w = frame.shape[:2]
            self.frame_size = (w, h)
        
        # Store latest frame for /snap
        self.latest_frame = frame.copy()
        
        if self.recorder.is_recording():
            self.recorder.write_frame(frame)
    
    def process_frame(self, frame):
        """Process a single frame through the pipeline."""
        self.frames_processed += 1
        
        # Store frame size for recorder
        if self.frame_size is None:
            h, w = frame.shape[:2]
            self.frame_size = (w, h)
        
        display_frame = frame.copy()
        
        # Check if paused
        if self.paused:
            cv2.putText(display_frame, "PAUSED (Telegram /start to resume)", 
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
            return display_frame
        
        # Check brightness
        if not self.detector.check_brightness(frame):
            draw_dark_warning(display_frame)
            return display_frame
        
        # Detect persons
        boxes = self.detector.detect(frame)
        
        # Face recognition (only if needed)
        if self.tracker.needs_face_check(boxes):
            self.face_checks += 1
            faces_per_box = []
            
            for box in boxes:
                faces = self.recognizer.identify(frame, box)
                faces_per_box.append(faces)
                
                # Log detections
                for name, _ in faces:
                    self.logger.log_detection(name, frame)
            
            self.tracker.update(boxes, faces_per_box)
        
        # Draw cached detections
        for name, face_loc, bbox in self.tracker.get_cached():
            draw_detection(display_frame, name, face_loc, bbox)
        
        # Draw stats
        draw_stats(display_frame, self.face_checks, self.frames_processed)
        
        # Draw recording indicator (display only, not in recording)
        if self.recorder.is_recording():
            dur = self.recorder.get_duration()
            cv2.circle(display_frame, (620, 20), 8, (0, 0, 255), -1)
            cv2.putText(display_frame, f"REC {dur:.0f}s", (560, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        return display_frame
    
    def print_stats(self):
        """Print final statistics."""
        print(f"\n👋 Surveillance stopped.")
        print(f"   Frames processed: {self.frames_processed}")
        if self.frames_processed > 0:
            ratio = self.face_checks / self.frames_processed * 100
            print(f"   Face checks: {self.face_checks} ({ratio:.1f}%)")


def main():
    # Init system
    system = SecuritySystem()
    system.start()  # Start Telegram listener
    
    # Init camera
    cam = config.camera
    cap = cv2.VideoCapture(cam.index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam.height)
    
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return
    
    process_interval = max(1, int(1 / cam.process_rate))
    frame_count = 0
    show_display = cam.show_display
    
    print(f"\n🎥 Surveillance active (processing every {process_interval} frames)")
    if show_display:
        print("Press 'q' to quit.\n")
    else:
        print("Running headless (no display). Ctrl+C to quit.\n")
    print("📱 Telegram: /help for commands\n")
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # Record ALL frames (raw, no graphics)
            system.record_frame(frame)
            
            # Only process every Nth frame
            if frame_count % process_interval == 0:
                display_frame = system.process_frame(frame)
                
                # Show display window if enabled
                if show_display:
                    cv2.imshow("Hostel Security", display_frame)
            
            # Check for quit (only if display is shown)
            if show_display:
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                # Small delay for headless mode
                cv2.waitKey(1)
    finally:
        system.stop()
        cap.release()
        if show_display:
            cv2.destroyAllWindows()
        system.print_stats()


if __name__ == "__main__":
    main()
