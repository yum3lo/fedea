# Smart Pet Feeder IoT System

An intelligent pet feeding system built with an Orange Pi Zero 2W that uses computer vision to recognize the user's cats and dispense food automatically via MQTT commands. The system has an infrared sensor able to detect movement till a certain distance, a stepper motor that dispenses food, a camera that takes pictures for the cat recognition model and when motion is detected, a 1kg load cell that updates the user with any weight changes, alerting about food levels, and an Arduino Uno. Initially the system was designed to have an additional load cell (200g) for monitoring the food level in the tray so the system doesn't overfeed the cats or overflow the tray, but because of some hardware issues it will be implemented in the future. On a similar note an Arduino Uno was used for controlling the sensors and the motor as no GPIO library would work on the Orange Pi board I used. The Arduino was connected to the Orange Pi with the `arduino.cpp` file on it. 

## Features

- **Cat Recognition**: Uses TensorFlow/Keras to identify different cats
- **Motion Detection**: Triggers when pets approach the feeder
- **Weight Monitoring**: Tracks food bowl weight in real-time
- **MQTT Integration**: Remote control and monitoring via MQTT
- **Camera System**: Captures photos for training and identification
- **Auto Training**: Retrains the model with new cat photos
- **Custom 3D Printed Housing**: Designed and printed custom enclosure for all components

## Used Hardware Components

- Orange Pi Zero 2W
- Arduino Uno
- USB Camera Module
- 1kg Load Cell / Weighing Sensor
- E18-D80NK Infrared Obstacle Avoidance Sensor
- 28BYJ-48 Stepper Motor + ULN2003 Driver
- Custom 3D printed enclosure (3MF files included)

## 3D Printed Components
This project features a completely custom-designed 3D printed housing that integrates all electronic components in a pet-safe, functional design.

### Design Features

- Modular design for easy assembly and maintenance
- Integrated camera and IR sensor mount with optimal viewing angle
- Secure electronics compartment with ventilation
- Food dispensing mechanism housing
- Cable management and access ports
- Pet-safe rounded edges and food-grade compatible design

### 3D Model Screenshots
![image](https://github.com/user-attachments/assets/ce70c32a-278b-4faf-8843-d8ff2c57c15d)
![image](https://github.com/user-attachments/assets/6b300647-ad0f-455b-8f9a-064445be347b)
![image](https://github.com/user-attachments/assets/64f727b3-9c1b-48a5-992e-3b64715cf606)

3D Files
All 3MF files are available in the /3d_models/ directory.

## Software Dependencies

```bash
pip install opencv-python
pip install tensorflow
pip install paho-mqtt
pip install pyserial
pip install scikit-learn
pip install python-dotenv
```

## Project Structure

```
fedea/
├── main.py              # Main system controller
├── mqtt.py              # MQTT client and message handling
├── camera.py            # Camera operations and photo capture
├── recognition.py       # Cat recognition using TensorFlow
├── train_model.py       # Model training functionality
├── photos/              # Training images storage (generated)
│   ├── cat_[name]/      # Individual cat training photos
│   ├── bg/              # Background images for training
│   └── temp/            # Temporary images
├── keras_Model.h5       # Trained TensorFlow model (generated)
├── labels.txt           # Class labels for the model (generated)
├── 3d_models/           # 3D model files
├── requirements.txt     # Python dependencies
└── .gitignore           # Git ignore file
```

## Setup

1. Clone this repository:
   ```bash
   git clone https://github.com/yum3lo/fedea.git
   cd fedea
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file and save your MQTT credentials:
   ```python
   BROKER = your-mqtt-broker
   CLIENT_ID = your_client_id
   TOPIC = your/topic
   USERNAME = your-username
   PASSWORD = your-password
   ```

4. Connect your Arduino to `/dev/ttyACM0` (or update the serial port in `main.py`)

5. Run the system:
   ```bash
   python main.py
   ```

## Usage

### MQTT Commands

The system listens for commands on: `pet-feeder/bc:f6:c1:98:4a:3a/commands/#`

- **Dispense Food**: `{"action": "dispense", "catId": "1", "amount": 20}`
- **Capture Images**: `{"action": "sendImage", "catId": "1"}`
- **Train Model**: `{"action": "trainModel"}`

### Status Updates

The system publishes weight status to: `pet-feeder/bc:f6:c1:98:4a:3a/status`
