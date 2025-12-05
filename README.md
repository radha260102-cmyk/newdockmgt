# Dock Management System

A Python-based dock management system that uses YOLOv5 object detection to monitor truck parking and human presence, providing real-time status indicators (Red/Yellow/Green).

## Features

- Real-time object detection using YOLOv5 custom models
- Dock state management with business rule logic
- Simple GUI with visual signal indicators (Red/Yellow/Green)
- Detection of trucks, persons, and forklifts (forklifts are ignored)
- Zone-based monitoring system

## Requirements

- Python 3.8 or higher
- YOLOv5 custom model file (.pt format)
- Webcam or video source
- PyTorch (torch and torchvision)

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Place your YOLO custom model file in the `models/` directory and name it `best.pt` (or update `MODEL_PATH` in `config.py`)

3. Configure your model class IDs in `config.py`:
   - Update `CLASS_IDS` dictionary with your model's class mappings
   - Adjust `CONFIDENCE_THRESHOLD` as needed

## Project Structure

```
HumanBackendLogicNew/
├── main.py                 # Main entry point
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── README.md              # This file
├── src/
│   ├── __init__.py
│   ├── detector.py        # YOLO detection logic
│   ├── dock_manager.py    # Dock state management
│   └── ui.py              # GUI components
├── utils/
│   ├── __init__.py
│   └── helpers.py         # Helper functions
└── models/                # YOLO model files (create this directory)
    └── best.pt            # Your YOLO model file
```

## Business Rules

The system follows these rules to determine dock status:

1. **RED (Violation)**: Truck inside zone + NOT touching parking line + Human present
2. **YELLOW (Warning)**: Truck inside zone + NOT touching parking line + No human
3. **GREEN (OK)**: 
   - Truck inside zone + Touching parking line (with or without human)
   - No truck present (with or without human)

## Configuration

Edit `config.py` to configure:

- `MODEL_PATH`: Path to your YOLO model file
- `CLASS_IDS`: Class ID mappings for your model
- `CONFIDENCE_THRESHOLD`: Detection confidence threshold
- `ZONE_COORDINATES`: Dock zone polygon coordinates
- `PARKING_LINE_THRESHOLD`: Distance threshold for parking line detection
- `VIDEO_SOURCE`: Camera index (0) or video file path

## Usage

Run the application:
```bash
python main.py
```

### UI Controls:
- **Start**: Begin video detection
- **Stop**: Stop video detection
- **Configure Zone**: Configure dock zone (to be implemented)
- **Exit**: Close the application

## Zone Configuration

Currently, zone coordinates need to be set in `config.py`. Future updates will include:
- Interactive zone drawing on video feed
- Parking line configuration via UI
- Zone persistence and loading

## Model Requirements

Your YOLO model should detect:
- Trucks (class name should contain "truck")
- Humans/Persons (class name should contain "human" or "person")
- Parking lines (class name should contain "line" or "parking")

Update the detection logic in `src/detector.py` if your class names differ.

## Troubleshooting

1. **Model not found**: Ensure your model file is in the `models/` directory and `MODEL_PATH` in `config.py` is correct
2. **Camera not working**: Check `VIDEO_SOURCE` in `config.py` (try 0, 1, or 2 for different cameras)
3. **Detection not working**: Verify your model class names match the expected patterns in `detector.py`

## License

This project is for internal use.
