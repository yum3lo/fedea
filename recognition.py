import cv2
import numpy as np
from tensorflow.keras.models import load_model
import os

np.set_printoptions(suppress=True)

class CatRecognizer:
    def __init__(self, model_path="keras_Model.h5", labels_path="labels.txt", bg_threshold=0.9):
        self.model_path = model_path
        self.labels_path = labels_path
        self.model = None
        self.class_names = []
        self.image_size = (224, 224)
        self.bg_threshold = bg_threshold
        self._load_model()
        
    def _load_model(self):
        # using the OpenCV Keras model from Teachable Machine
        try:
            if os.path.exists(self.model_path) and os.path.exists(self.labels_path):
                self.model = load_model(self.model_path, compile=False)
                
                with open(self.labels_path, "r") as f:
                    self.class_names = [line.strip() for line in f.readlines()]
                
                print(f"[RECOGNITION] Model loaded with {len(self.class_names)} classes")
                for i, name in enumerate(self.class_names):
                    print(f"  Class {i}: {name}")
            else:
                print("[RECOGNITION] Model or labels not found. Please ensure keras_Model.h5 and labels.txt exist.")
        except Exception as e:
            print(f"[RECOGNITION] Error loading model: {e}")
            
    def preprocess_image(self, image):
        if image is None:
            return None
            
        resized = cv2.resize(image, self.image_size, interpolation=cv2.INTER_AREA)
        image_array = np.asarray(resized, dtype=np.float32).reshape(1, 224, 224, 3)
        normalized = (image_array / 127.5) - 1
        
        return normalized
        
    def predict(self, image):
        if self.model is None or not self.class_names:
            print("[RECOGNITION] Model not loaded")
            return "unknown", 0.0
            
        processed_image = self.preprocess_image(image)
        if processed_image is None:
            return "unknown", 0.0
            
        try:
            predictions = self.model.predict(processed_image, verbose=0)
            
            # getting the class with highest confidence
            predicted_class_idx = np.argmax(predictions)
            confidence = predictions[0][predicted_class_idx]
            
            if confidence < self.bg_threshold:
                return "background", confidence

            if predicted_class_idx < len(self.class_names):
                # removing the class number prefix ("0 cat_1" -> "cat_1")
                class_name = self.class_names[predicted_class_idx]
                if " " in class_name:
                    cat_name = class_name.split(" ", 1)[1]
                else:
                    cat_name = class_name
                
                print(f"[RECOGNITION] Raw prediction: {class_name}")
                print(f"[RECOGNITION] Extracted name: {cat_name}")
                print(f"[RECOGNITION] Confidence: {confidence*100:.1f}%")
                
                if "background" in cat_name.lower():
                    return "background", confidence

                return cat_name, float(confidence)
            else:
                return "unknown", 0.0
                
        except Exception as e:
            print(f"[RECOGNITION] Prediction error: {e}")
            return "unknown", 0.0
            
    def reload_model(self):
        self._load_model()
        
    def test_camera_recognition(self):
        camera = cv2.VideoCapture(0)
        
        while True:
            ret, image = camera.read()
            if not ret:
                print("Failed to capture image")
                break
                
            cat_name, confidence = self.predict(image)
            
            display_text = f"{cat_name}: {confidence*100:.1f}%"
            cv2.putText(image, display_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            cv2.imshow("Cat Recognition Test", image)
            
            print(f"Detected: {cat_name} (Confidence: {confidence*100:.1f}%)")
            
            if cv2.waitKey(1) == 27:
                break
                
        camera.release()
        cv2.destroyAllWindows()