"""
Central configuration for the Hostel Security System.
All settings in one place.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CameraConfig:
    index: int = 0           # 0 = built-in, 1 = external USB
    width: int = 640
    height: int = 480
    process_rate: float = 0.1  
    show_display: bool = False   # show display window on server side


@dataclass
class DetectionConfig:
    model_path: str = "yolov8n.pt"
    person_confidence: float = 0.5
    min_brightness: int = 10


@dataclass
class RecognitionConfig:
    known_faces_dir: str = "known_faces"
    face_tolerance: float = 0.6  # lower = stricter matching
    model_name: str = "VGG-Face"


@dataclass
class TrackingConfig:
    bbox_move_threshold: int = 50    # pixels to trigger re-detect
    recheck_interval: float = 5.0    # seconds for forced refresh


@dataclass 
class LoggingConfig:
    intruders_dir: str = "intruders"
    log_file: str = "activity_log.csv"
    known_cooldown: int = 300    # 5 minutes
    unknown_cooldown: int = 30   # 30 seconds


@dataclass
class NotificationConfig:
    telegram_token: str = "8397289887:AAEYwqW8lNbCMlwOgkiflsXeSsLcCoaplaU"
    telegram_chat_id: str = "1527878179"


@dataclass
class RecordingConfig:
    output_dir: str = "recordings"
    fps: int = 30           # frames per second (camera FPS)
    codec: str = "mp4v"     # codec for mp4


@dataclass
class Config:
    """Main configuration container."""
    camera: CameraConfig = field(default_factory=CameraConfig)
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    recognition: RecognitionConfig = field(default_factory=RecognitionConfig)
    tracking: TrackingConfig = field(default_factory=TrackingConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    recording: RecordingConfig = field(default_factory=RecordingConfig)


# Global config instance
config = Config()

