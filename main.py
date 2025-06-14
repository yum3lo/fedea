import serial
import time
import cv2
from threading import Thread
from datetime import datetime
from camera import PetCamera
from recognition import CatRecognizer
from mqtt import MQTTFeeder

class PetFeederSystem:
    def __init__(self):
        self.arduino = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
        self.camera = PetCamera()
        self.recognizer = CatRecognizer()
        self.mqtt_client = MQTTFeeder()
        self.mqtt_client.set_system(self)

        self.running = True
        self.motion_detected = False
        self.last_weight = None

        self.last_motion_time = 0
        self.motion_cooldown = 10
        self.processing_motion = False
    
        Thread(target=self._monitor_sensors, daemon=True).start()
        Thread(target=self._monitor_commands, daemon=True).start()

    def _monitor_sensors(self):
        while self.running:
            try:
                if self.arduino.in_waiting:
                    line = self.arduino.readline().decode().strip()
                    
                    if line == "MOTION_DETECTED":
                        current_time = time.time()
                        if current_time - self.last_motion_time < self.motion_cooldown:
                            print(f"[DEBOUNCE] Motion ignored - cooldown active ({self.motion_cooldown - (current_time - self.last_motion_time):.1f}s remaining)")
                            continue
                        
                        if self.processing_motion:
                            print("[DEBOUNCE] Motion ignored - already processing")
                            continue
                        
                        print("\n[!] Motion detected near feeder!")
                        self.last_motion_time = current_time
                        self._handle_motion()
                    elif line.startswith("WEIGHT:"):
                        weight = float(line.split(":")[1])
                        if weight >= 0:
                            if self.last_weight is None or abs(weight - self.last_weight) >= 1.0:
                                self.last_weight = weight
                                self.mqtt_client.send_weight(weight)
                    elif line:
                        print(line)
                        
                time.sleep(0.1)
            except Exception as e:
                print(f"[ERROR] Sensor monitoring error: {e}")
                time.sleep(1)

    def _handle_motion(self):
        self.processing_motion = True
        self.motion_detected = True

        try:
            single_photo = self.camera.capture_single_photo()
            if single_photo:
                frame = cv2.imread(single_photo)
                cat_name, confidence = self.recognizer.predict(frame)
                if cat_name == "background":
                    print(f"[RECOGNITION] Background detected (confidence: {confidence*100:.1f}%), ignoring")
                    return
                    
                print(f"[RECOGNITION] Identified: {cat_name} ({confidence*100:.1f}%)")
                if confidence > 0.9:
                    cat_id = cat_name.replace("cat_", "")
                    self._send_cat_detection(cat_id)
                else:
                    print(f"[WARNING] Low confidence ({confidence*100:.1f}%), not sending detection")
        
        except Exception as e:
            print(f"[ERROR] Motion handling failed: {e}")
        finally:
            self.processing_motion = False
            print(f"[SYSTEM] Motion processing complete. Next detection allowed in {self.motion_cooldown}s")

    def _send_cat_detection(self, cat_id):
        message = {
            "action": "sendCat",
            "catId": cat_id,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        topic = "pet-feeder/bc:f6:c1:98:4a:3a/info"
        self.mqtt_client.publish_message(topic, message)
        print(f"[MQTT] Sent cat detection: {message}")

    def _monitor_commands(self):
        while self.running:
            self._print_menu()
            cmd = input("Enter command: ").lower().strip()
            
            if cmd == 'exit':
                print("Shutting down system...")
                self.running = False
            else:
                self.arduino.write(f"{cmd}\n".encode())

    def _print_menu(self):
        print("\n=== Smart Pet Feeder ===")
        print(f"Camera photos: {self.camera.photo_count}")
        cooldown_remaining = max(0, self.motion_cooldown - (time.time() - self.last_motion_time))
        if cooldown_remaining > 0:
            print(f"Motion detection: Cooldown ({cooldown_remaining:.1f}s remaining)")
        else:
            print("Motion detection: Ready")
        print("1. dispense  - Dispense food")
        print("2. status    - Check weight")
        print("3. tare      - Tare weights")
        print("4. train     - Train recognition model (for testing)")
        print("5. exit      - Quit program")

    def cleanup(self):
        self.arduino.close()
        self.camera.cleanup()
        self.mqtt_client.disconnect()

if __name__ == "__main__":
    system = PetFeederSystem()
    try:
        while system.running:
            time.sleep(1)
    finally:
        system.cleanup()