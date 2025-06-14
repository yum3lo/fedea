import cv2
import time
import os
from datetime import datetime

class PetCamera:
    def __init__(self, save_path="/home/orangepi/fedea/photos/"):
        self.save_path = save_path
        self.photo_count = 0
        self.camera = None
        self._setup_camera()
        
    def _setup_camera(self):
        try:
            self.camera = cv2.VideoCapture(1)
            if not self.camera.isOpened():
                raise RuntimeError("Could not open camera")
            time.sleep(2)
            print("Camera initialized successfully")
        except Exception as e:
            print(f"Camera initialization failed: {e}")
            self.camera = None

    def capture_single_photo(self):
        # for immediate recognition
        if not self.camera:
            print("Camera not available")
            return None
        
        self._clear_camera_buffer()

        ret, frame = self.camera.read()
        if not ret:
            print("Failed to capture frame")
            return None

        # temp directory for single photos
        temp_dir = os.path.join(self.save_path, "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = os.path.join(temp_dir, f"detection_{timestamp}.jpg")
        
        # saving original resolution image for better recognition
        cv2.imwrite(filename, frame)
        self.photo_count += 1
        print(f"[PHOTO] Single photo saved: {filename}")
        return filename

    def capture_multiple_photos_for_training(self, cat_id, duration: float = 10.0, interval: float = 0.5):
        # multiple photos for training data when a cat is detected or for background training
        if not self.camera:
            print("Camera not available")
            return None
            
        self._clear_camera_buffer()
        time.sleep(1)

        if cat_id.lower() == "background":
            save_dir = os.path.join(self.save_path, "bg")
            print(f"[TRAINING] Capturing background photos for {duration} seconds...")
        else:
            save_dir = os.path.join(self.save_path, f"cat_{cat_id}")
            print(f"[TRAINING] Capturing photos for cat {cat_id} for {duration} seconds...")
            
        os.makedirs(save_dir, exist_ok=True)
        
        start_time = time.time()
        photos_taken = 0
        
        while time.time() - start_time < duration:
            ret, frame = self.camera.read()
            if not ret:
                print("Failed to capture frame")
                continue

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            
            if cat_id.lower() == "background":
                filename = os.path.join(save_dir, f"bg_{timestamp}.jpg")
            else:
                filename = os.path.join(save_dir, f"training_{timestamp}.jpg")
                
            cv2.imwrite(filename, frame)
            self.photo_count += 1
            photos_taken += 1
            print(f"[TRAINING] Saved: {filename}")
            time.sleep(interval)
            
        if cat_id.lower() == "background":
            print(f"[TRAINING] Captured {photos_taken} background photos")
        else:
            print(f"[TRAINING] Captured {photos_taken} training photos for cat {cat_id}")

    def capture_multiple_photos(self, cat_id, duration: float = 10.0, interval: float = 0.5):
        # legacy method for MQTT compatibility
        return self.capture_multiple_photos_for_training(cat_id, duration, interval)

    def _clear_camera_buffer(self, num_frames=5):
        print("[CAMERA] Clearing buffer...")
        for i in range(num_frames):
            ret, frame = self.camera.read()
            if ret:
                time.sleep(0.1)
        print("[CAMERA] Buffer cleared")

    def cleanup(self):
        if self.camera:
            self.camera.release()
            cv2.destroyAllWindows()
            print("Camera resources released")