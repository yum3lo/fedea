import os
import cv2
import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout
from tensorflow.keras.utils import to_categorical
from sklearn.model_selection import train_test_split

IMAGE_SIZE = (224, 224)
DATA_DIR = "/home/orangepi/fedea/photos/"
MODEL_SAVE_PATH = "keras_Model.h5"
LABELS_SAVE_PATH = "labels.txt"

def load_dataset(data_dir):
    X, y, class_names = [], [], []
    class_map = {}

    background_found = False
    for class_folder in os.listdir(data_dir):
        if class_folder.lower() == "bg":
            background_found = True

    if not background_found:
        print("[WARNING] No 'bg' folder found for background training")

    for idx, class_folder in enumerate(sorted(os.listdir(data_dir))):
        class_path = os.path.join(data_dir, class_folder)
        if not os.path.isdir(class_path) or class_folder == "temp":
            continue

        class_map[idx] = class_folder
        class_names.append(class_folder)

        for img_file in os.listdir(class_path):
            img_path = os.path.join(class_path, img_file)
            img = cv2.imread(img_path)
            if img is None:
                continue

            img = cv2.resize(img, IMAGE_SIZE, interpolation=cv2.INTER_AREA)
            X.append(img)
            y.append(idx)

    return np.array(X), np.array(y), class_names

def preprocess_data(X, y):
    X = X.astype("float32") / 127.5 - 1  # normalize to [-1, 1]
    y = to_categorical(y)
    return train_test_split(X, y, test_size=0.2, random_state=42)

def build_model(input_shape, num_classes):
    model = Sequential([
        # convolutional blocks
        Conv2D(16, (3, 3), activation='relu', input_shape=input_shape),
        MaxPooling2D(2, 2),
        
        Conv2D(32, (3, 3), activation='relu'),
        MaxPooling2D(2, 2),
        
        Conv2D(64, (3, 3), activation='relu'),
        MaxPooling2D(2, 2),
        
        Conv2D(64, (3, 3), activation='relu'),
        MaxPooling2D(2, 2),
        
        Flatten(),
        Dropout(0.2),
        Dense(512, activation='relu'),
        Dropout(0.2),
        Dense(num_classes, activation='softmax')
    ])
    
    model.compile(
        optimizer='adam',
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
    return model

def save_labels(class_names, path):
    with open(path, "w") as f:
        for idx, name in enumerate(class_names):
            f.write(f"{idx} {name}\n")

def train_and_save():
    print("[TRAINING] Loading dataset...")

    try:
        X, y, class_names = load_dataset(DATA_DIR)

        if len(class_names) < 2:
            print("[ERROR] Not enough classes to train. Need at least 2 classes.")
            return False

        if len(X) < 10:
            print(f"[ERROR] Not enough images to train. Found {len(X)} images, need at least 10.")
            return False

        for i, name in enumerate(class_names):
            class_count = np.sum(y == i)
            print(f"  - {name}: {class_count} images")

        print("[TRAINING] Preprocessing data...")
        X_train, X_test, y_train, y_test = preprocess_data(X, y)
        
        print("[TRAINING] Building model...")
        model = build_model((224, 224, 3), len(class_names))
        
        print("[TRAINING] Model architecture:")
        model.summary()

        print("[TRAINING] Starting training...")
        history = model.fit(
            X_train, y_train,
            epochs=10,
            batch_size=16,
            validation_data=(X_test, y_test),
            verbose=1
        )

        # evaluating the model
        test_loss, test_accuracy = model.evaluate(X_test, y_test, verbose=0)
        print(f"[TRAINING] Test accuracy: {test_accuracy*100:.2f}%")

        print("[TRAINING] Saving model and labels...")
        # saving without compiling
        model.save(MODEL_SAVE_PATH, save_format='h5')
        save_labels(class_names, LABELS_SAVE_PATH)
        
        print(f"[TRAINING] Model saved to {MODEL_SAVE_PATH}")
        print(f"[TRAINING] Labels saved to {LABELS_SAVE_PATH}")
        print(f"[TRAINING] Training completed successfully!")
        print(f"[TRAINING] Final accuracy: {test_accuracy*100:.2f}%")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Training failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
if __name__ == "__main__":
    train_and_save()