"""
Drawing utilities for visualization.
"""
import cv2


def draw_detection(frame, name, face_loc, person_bbox):
    """
    Draw detection boxes and labels on frame.
    
    Args:
        frame: Image to draw on (modified in place)
        name: Person's name or None
        face_loc: (top, right, bottom, left) or None
        person_bbox: (x1, y1, x2, y2)
    """
    x1, y1, x2, y2 = map(int, person_bbox)
    
    # Draw person bbox (cyan)
    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 0), 1)
    
    if name and face_loc:
        # Draw face bbox with label
        top, right, bottom, left = face_loc
        color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
        
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        cv2.rectangle(frame, (left, bottom - 25), (right, bottom), color, cv2.FILLED)
        cv2.putText(frame, name, (left + 6, bottom - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    else:
        # No face detected
        cv2.putText(frame, "Person (no face)", (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)


def draw_stats(frame, face_checks, frames_processed):
    """Draw optimization stats on frame."""
    if frames_processed > 0:
        ratio = face_checks / frames_processed * 100
        cv2.putText(frame, f"Face checks: {ratio:.0f}%", 
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)


def draw_dark_warning(frame):
    """Draw 'Too dark' warning."""
    cv2.putText(frame, "Too dark", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

