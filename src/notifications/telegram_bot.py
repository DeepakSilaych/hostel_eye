"""
Telegram bot for notifications and remote control.

Commands:
  /start - Start surveillance
  /stop - Stop surveillance
  /status - Get current status
  /list - List known faces
  /add <name> - Add face (send photo after)
  /remove <name> - Remove a known face
  /record - Start recording
  /stoprecord - Stop recording
  /recordings - List recordings
  /continue - Continue recording (acknowledge reminder)
"""
import os
import time
import requests
import threading
from src.config import config


class TelegramBot:
    """Telegram bot for alerts and remote control."""
    
    def __init__(self):
        self.token = config.notifications.telegram_token
        self.chat_id = config.notifications.telegram_chat_id
        self.enabled = bool(self.token and self.chat_id)
        
        # State
        self.running = False
        self.surveillance_active = True
        self.pending_add_name = None
        self.last_update_id = 0
        
        # Callbacks (set by SecuritySystem)
        self.on_start = None
        self.on_stop = None
        self.on_add_face = None
        self.on_remove_face = None
        self.on_record_start = None
        self.on_record_stop = None
        self.on_record_continue = None  # Acknowledge reminder
        self.on_snap = None  # Capture current frame
        self.get_status = None
        self.get_recordings = None
        
        if not self.enabled:
            print("⚠️  Telegram bot disabled (no token/chat_id)")
        else:
            print("✓ Telegram bot enabled")
    
    def start_polling(self):
        """Start background thread to poll for commands."""
        if not self.enabled:
            return
        
        self.running = True
        thread = threading.Thread(target=self._poll_loop, daemon=True)
        thread.start()
        print("✓ Telegram command listener started")
    
    def stop_polling(self):
        """Stop polling."""
        self.running = False
    
    def _poll_loop(self):
        """Poll for new messages."""
        while self.running:
            try:
                updates = self._get_updates()
                for update in updates:
                    self._handle_update(update)
                    self.last_update_id = update["update_id"] + 1
            except Exception as e:
                print(f"Telegram poll error: {e}")
            time.sleep(1)
    
    def _get_updates(self):
        """Fetch new messages from Telegram."""
        url = f"https://api.telegram.org/bot{self.token}/getUpdates"
        params = {"offset": self.last_update_id, "timeout": 5}
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        return data.get("result", [])
    
    def _handle_update(self, update):
        """Process a single update."""
        msg = update.get("message", {})
        chat_id = str(msg.get("chat", {}).get("id", ""))
        
        # Only respond to authorized chat
        if chat_id != self.chat_id:
            return
        
        text = msg.get("text", "").strip()
        caption = msg.get("caption", "").strip()  # Photo captions
        photo = msg.get("photo")
        
        # Handle photo with /add command in caption (photo + command together)
        if photo and caption.startswith("/add "):
            name = caption.split(maxsplit=1)[1] if len(caption.split()) > 1 else ""
            if name:
                self.pending_add_name = name
                self._handle_add_photo(msg, photo)
                return
        
        # Handle photo (for adding faces after /add command)
        if photo and self.pending_add_name:
            self._handle_add_photo(msg, photo)
            return
        
        # Handle commands
        if text.startswith("/"):
            self._handle_command(text)
        elif caption.startswith("/"):
            self._handle_command(caption)
    
    def _handle_command(self, text):
        """Parse and execute command."""
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower().split("@")[0]  # Handle /cmd@botname
        arg = parts[1] if len(parts) > 1 else ""
        
        if cmd == "/start":
            self.surveillance_active = True
            if self.on_start:
                self.on_start()
            self.send_message("✅ Surveillance STARTED")
        
        elif cmd == "/stop":
            self.surveillance_active = False
            if self.on_stop:
                self.on_stop()
            self.send_message("⏹️ Surveillance STOPPED")
        
        elif cmd == "/status":
            status = "🟢 Active" if self.surveillance_active else "🔴 Stopped"
            extra = ""
            if self.get_status:
                extra = self.get_status()
            self.send_message(f"Status: {status}\n{extra}")
        
        elif cmd == "/list":
            faces = self._list_known_faces()
            if faces:
                self.send_message(f"👥 Known faces:\n" + "\n".join(f"• {f}" for f in faces))
            else:
                self.send_message("No known faces registered")
        
        elif cmd == "/add":
            if not arg:
                self.send_message("Usage: /add <name>\nThen send a photo")
                return
            self.pending_add_name = arg
            self.send_message(f"📸 Send a photo to register '{arg}'")
        
        elif cmd == "/remove":
            if not arg:
                self.send_message("Usage: /remove <name>")
                return
            success = self._remove_face(arg)
            if success:
                self.send_message(f"✅ Removed '{arg}' from known faces")
            else:
                self.send_message(f"❌ '{arg}' not found")
        
        elif cmd == "/record":
            if self.on_record_start:
                result = self.on_record_start()
                if result:
                    self.send_message(
                        f"🔴 Recording started\n"
                        f"File: {result}\n\n"
                        f"⏰ Reminder in 10 min. Reply /continue to keep recording."
                    )
                else:
                    self.send_message("⚠️ Already recording")
            else:
                self.send_message("Recording not available")
        
        elif cmd == "/stoprecord":
            if self.on_record_stop:
                result = self.on_record_stop()
                if result:
                    self.send_message(f"⏹️ Recording stopped\nSaved: {result}")
                else:
                    self.send_message("⚠️ Not recording")
            else:
                self.send_message("Recording not available")
        
        elif cmd == "/continue":
            if self.on_record_continue:
                self.on_record_continue()
                self.send_message("✅ Recording will continue\nNext reminder in 10 min")
            else:
                self.send_message("Not recording")
        
        elif cmd == "/recordings":
            if self.get_recordings:
                recs = self.get_recordings()
                if recs:
                    lines = [f"• {name} ({size:.1f} MB)" for name, size in recs[:10]]
                    self.send_message(f"📹 Recordings:\n" + "\n".join(lines))
                else:
                    self.send_message("No recordings found")
            else:
                self.send_message("Recording not available")
        
        elif cmd == "/snap":
            if self.on_snap:
                result = self.on_snap()
                if result:
                    self.send_alert("📸 Current frame", result)
                else:
                    self.send_message("❌ No frame available")
            else:
                self.send_message("Snap not available")
        
        elif cmd == "/help":
            self.send_message(
                "🤖 Commands:\n\n"
                "📹 Surveillance:\n"
                "/start - Start surveillance\n"
                "/stop - Stop surveillance\n"
                "/status - Get status\n"
                "/snap - Get current frame\n\n"
                "👤 Faces:\n"
                "/list - List known faces\n"
                "/add <name> - Add face\n"
                "/remove <name> - Remove face\n\n"
                "🎬 Recording:\n"
                "/record - Start recording\n"
                "/stoprecord - Stop recording\n"
                "/continue - Keep recording\n"
                "/recordings - List recordings"
            )
        
        else:
            self.send_message("Unknown command. Send /help")
    
    def _handle_add_photo(self, msg, photos):
        """Download photo and add as known face."""
        name = self.pending_add_name
        self.pending_add_name = None
        
        # Get largest photo
        photo = max(photos, key=lambda p: p.get("file_size", 0))
        file_id = photo["file_id"]
        
        # Get file path
        url = f"https://api.telegram.org/bot{self.token}/getFile"
        resp = requests.get(url, params={"file_id": file_id}, timeout=10)
        file_path = resp.json().get("result", {}).get("file_path")
        
        if not file_path:
            self.send_message("❌ Failed to download photo")
            return
        
        # Download file
        download_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
        img_data = requests.get(download_url, timeout=30).content
        
        # Save to known_faces/
        known_dir = config.recognition.known_faces_dir
        os.makedirs(known_dir, exist_ok=True)
        save_path = os.path.join(known_dir, f"{name}.jpg")
        
        with open(save_path, "wb") as f:
            f.write(img_data)
        
        self.send_message(f"✅ Added '{name}' to known faces!")
        
        if self.on_add_face:
            self.on_add_face(name, save_path)
    
    def _list_known_faces(self):
        """List all known face names."""
        known_dir = config.recognition.known_faces_dir
        if not os.path.exists(known_dir):
            return []
        
        faces = []
        for f in os.listdir(known_dir):
            if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                faces.append(os.path.splitext(f)[0])
        return sorted(faces)
    
    def _remove_face(self, name):
        """Remove a known face."""
        known_dir = config.recognition.known_faces_dir
        
        for ext in ['.jpg', '.jpeg', '.png']:
            path = os.path.join(known_dir, f"{name}{ext}")
            if os.path.exists(path):
                os.remove(path)
                return True
        return False
    
    def send_message(self, text):
        """Send text message."""
        if not self.enabled:
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            data = {"chat_id": self.chat_id, "text": text}
            requests.post(url, data=data, timeout=10)
            return True
        except:
            return False
    
    def send_recording_reminder(self, reminder_num, duration_min):
        """Send recording reminder."""
        remaining = 3 - reminder_num
        self.send_message(
            f"⏰ Recording Reminder #{reminder_num}\n\n"
            f"🔴 Recording active for {duration_min:.0f} minutes\n\n"
            f"Reply /continue to keep recording\n"
            f"Reply /stoprecord to stop\n\n"
            f"⚠️ Auto-stop after {remaining} more reminder(s) if no response"
        )
    
    def send_auto_stop_notice(self):
        """Notify that recording was auto-stopped."""
        self.send_message(
            "⚠️ Recording AUTO-STOPPED\n\n"
            "No response to reminders.\n"
            "Use /record to start again."
        )
    
    def send_alert(self, message, image_path=None):
        """Send alert with optional photo."""
        if not self.enabled:
            return False
        
        try:
            if image_path and os.path.exists(image_path):
                return self._send_photo(message, image_path)
            return self.send_message(message)
        except Exception as e:
            print(f"Telegram error: {e}")
            return False
    
    def _send_photo(self, caption, image_path):
        """Send photo with caption."""
        url = f"https://api.telegram.org/bot{self.token}/sendPhoto"
        data = {"chat_id": self.chat_id, "caption": caption}
        
        with open(image_path, 'rb') as photo:
            files = {"photo": photo}
            resp = requests.post(url, data=data, files=files, timeout=30)
        return resp.ok


# Backward compatibility alias
TelegramNotifier = TelegramBot
