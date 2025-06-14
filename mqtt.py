import paho.mqtt.client as mqtt
import json
import time
import os
from datetime import datetime
from threading import Thread
from dotenv import load_dotenv
from camera import PetCamera
from train_model import train_and_save

load_dotenv()

BROKER = os.getenv('BROKER')
PORT = 8883
CLIENT_ID = os.getenv('CLIENT_ID')
TOPIC = os.getenv('TOPIC')
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')

class MQTTFeeder:
    def __init__(self):
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=CLIENT_ID)
        self.camera = PetCamera()
        self.system = None
        self._connection_monitor_active = True
        self._training_in_progress = False

        self.setup_callbacks()
        self.connect()
        Thread(target=self._connection_monitor, daemon=True).start()

    def setup_callbacks(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
    def connect(self):
        try:
            self.client.username_pw_set(USERNAME, PASSWORD)
            self.client.tls_set()
            self.client.will_set(
                "pet-feeder/bc:f6:c1:98:4a:3a/status",
                payload=json.dumps({"online": False, "timestamp": datetime.utcnow().isoformat() + "Z"}),
                qos=1,
                retain=True
            )

            self.client.connect(BROKER, PORT, keepalive=60)
            self.client.loop_start()
            time.sleep(2)
        except Exception as e:
            print(f"[MQTT] Initial connection error: {e}")
            self._ensure_connection()
        
    def set_system(self, system):
        # reference to main system
        self.system = system

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print("Connected to MQTT Broker!")
            client.subscribe(TOPIC, qos=0)
            self._publish_status_message({"online": True, "timestamp": datetime.utcnow().isoformat() + "Z"})
        else:
            print(f"Connection failed: {reason_code}")
            
    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            print(f"Received command: {payload}")
            
            action = payload.get("action")

            if action == "dispense":
                self.handle_dispense(
                    cat_id=payload["catId"],
                    amount=payload["amount"],
                    timestamp=payload["timestamp"]
                )
            elif action == "sendImage":
                self.handle_capture_image(
                    cat_id=payload["catId"],
                    timestamp=payload["timestamp"]
                )
            elif action == "trainModel":
                self.handle_train_model()
                
        except Exception as e:
            print(f"Error processing message: {e}")
            
    def handle_dispense(self, cat_id, amount, timestamp):
        print(f"Dispensing {amount}g for cat {cat_id}")
        if self.system and self.system.arduino:
            self.system.arduino.write(f"dispense:{amount}\n".encode())

    def send_weight(self, weight):
        message = {
            "action": "sendWeight",
            "weight": round(weight, 1),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        topic = "pet-feeder/bc:f6:c1:98:4a:3a/info"
        self.publish_message(topic, message)
        print(f"[MQTT] Sent weight: {weight}g")

    def handle_capture_image(self, cat_id, timestamp):
        print(f"[MQTT] Capturing images for cat {cat_id} at {timestamp}")
        self.system.camera.capture_multiple_photos_for_training(cat_id=cat_id)

    def handle_train_model(self):
        print("[MQTT] Training model from saved cat images...")
        self._training_in_progress = True
        
        try:
            self._publish_status_message({
                "online": True, 
                "training": True,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
            
            self.client.loop_stop()
            self.client.disconnect()
            time.sleep(2)
            
            print("[MQTT] Starting model training...")
            train_success = train_and_save()
            
            if train_success:
                print("[MQTT] Training completed successfully")
            else:
                print("[MQTT] Training failed")
            
            print("[MQTT] Reconnecting after training...")
            self._training_in_progress = False
            self._full_reconnect()
            
            if self.system and hasattr(self.system, 'recognizer'):
                self.system.recognizer.reload_model()
                print("[MQTT] Model reloaded in recognition system")
            
            self._publish_status_message({
                "online": True, 
                "training": False,
                "training_success": train_success,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
            
        except Exception as e:
            print(f"[MQTT] Training error: {e}")
            self._training_in_progress = False
            self._full_reconnect()
        
    def on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        if self._training_in_progress:
            print("[MQTT] Disconnected for training - not attempting reconnection")
            return
            
        print(f"[MQTT] Disconnected (reason: {reason_code}), attempting to reconnect...")
        time.sleep(5)
        self._ensure_connection()

    def _connection_monitor(self):
        while self._connection_monitor_active:
            if not self._training_in_progress and not self.client.is_connected():
                print("[MQTT] Connection monitor detected disconnection")
                self._ensure_connection()
            time.sleep(15)

    def _ensure_connection(self, max_retries=3, retry_delay=5):
        if self._training_in_progress:
            return False
            
        for attempt in range(max_retries):
            try:
                if self.client.is_connected():
                    return True
                    
                print(f"[MQTT] Reconnection attempt {attempt + 1}/{max_retries}")
                self.client.reconnect()
                time.sleep(retry_delay)
                
                if self.client.is_connected():
                    print("[MQTT] Reconnected successfully")
                    return True
                    
            except Exception as e:
                print(f"[MQTT] Reconnection error: {e}")
                time.sleep(retry_delay)
        
        print("[MQTT] Failed to reconnect, performing full reset...")
        return self._full_reconnect()
    
    def _full_reconnect(self):
        try:
            print("[MQTT] Performing full connection reset...")
            self.client.loop_stop()
            self.client.disconnect()
            time.sleep(2)
            
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=CLIENT_ID)
            self.setup_callbacks()
            self.connect()
            return True
        except Exception as e:
            print(f"[MQTT] Full reconnect failed: {e}")
            return False

    def cleanup(self):
        self._connection_monitor_active = False
        self._training_in_progress = False
        self.client.loop_stop()
        self.client.disconnect()
        
    def publish_message(self, topic, message):
        try:
            result = self.client.publish(topic, json.dumps(message))
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                print(f"[MQTT] Failed to publish message: {result.rc}")
        except Exception as e:
            print(f"[MQTT] Publish error: {e}")
        
    def _publish_status_message(self, status_dict):
        topic = "pet-feeder/bc:f6:c1:98:4a:3a/status"
        self.publish_message(topic, status_dict)
        
    def publish_status(self, online_status):
        status_dict = {
            "online": online_status, 
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        self._publish_status_message(status_dict)

    def run(self):
        try:
            while True:
                if not self._training_in_progress:
                    self._publish_status_message({
                        "online": True,
                        "last_heartbeat": datetime.utcnow().isoformat() + "Z"
                    })
                time.sleep(30)
                
        except KeyboardInterrupt:
            self.cleanup()

if __name__ == "__main__":
    feeder = MQTTFeeder()
    feeder.run()