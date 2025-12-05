# Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Main Application                      │
│                         (main.py)                           │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Detector   │ │ Dock Manager │ │      UI      │
│  (YOLO)      │ │   (Logic)    │ │  (Tkinter)   │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                 │                 │
       │                 │                 │
       ▼                 ▼                 ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  YOLO Model  │ │   Helpers    │ │   Video      │
│   (.pt)      │ │  (Geometry)  │ │   Source     │
└──────────────┘ └──────────────┘ └──────────────┘
```

## Data Flow

1. **Video Input** → UI captures frames from video source
2. **Detection** → Detector processes frames with YOLO model
3. **State Logic** → Dock Manager applies business rules
4. **UI Update** → Signal indicator updates (Red/Yellow/Green)

## Module Responsibilities

### 1. `main.py`
- Entry point of the application
- Initializes all components
- Handles application lifecycle

### 2. `config.py`
- Centralized configuration
- Model paths, thresholds, class IDs
- Zone and parking line coordinates

### 3. `src/detector.py` (YOLODetector)
- Loads and manages YOLO model
- Performs object detection on frames
- Returns structured detection results
- Categorizes detections (trucks, humans, parking lines)

### 4. `src/dock_manager.py` (DockManager)
- Implements business logic rules
- Determines dock state based on:
  - Truck presence and position
  - Human presence
  - Zone boundaries
  - Parking line proximity
- Returns state: RED, YELLOW, or GREEN

### 5. `src/ui.py` (DockManagementUI)
- Tkinter-based GUI
- Video feed display
- Signal indicator (circular Red/Yellow/Green)
- Detection information panel
- Start/Stop controls

### 6. `utils/helpers.py`
- Geometric calculations:
  - Point-in-polygon (zone checking)
  - Distance calculations
  - Line intersection detection
  - Point-to-line distance

## Business Logic Flow

```
Frame Input
    │
    ▼
YOLO Detection
    │
    ├─→ Trucks detected?
    ├─→ Humans detected?
    └─→ Parking lines detected?
    │
    ▼
Dock Manager Logic
    │
    ├─→ No truck? → GREEN
    │
    ├─→ Truck in zone?
    │   ├─→ Touching parking line? → GREEN
    │   └─→ NOT touching parking line?
    │       ├─→ Human present? → RED (Violation)
    │       └─→ No human? → YELLOW (Warning)
    │
    └─→ Default → GREEN
    │
    ▼
State Output (RED/YELLOW/GREEN)
    │
    ▼
UI Signal Update
```

## State Determination Rules

| Condition | Truck in Zone | Touching Line | Human Present | Result |
|-----------|---------------|---------------|---------------|--------|
| 1 | No | - | - | GREEN |
| 2 | Yes | Yes | Yes/No | GREEN |
| 3 | Yes | No | Yes | RED (Violation) |
| 4 | Yes | No | No | YELLOW (Warning) |

## File Structure

```
HumanBackendLogicNew/
├── main.py                    # Application entry point
├── config.py                  # Configuration settings
├── requirements.txt           # Dependencies
├── README.md                  # User documentation
├── ARCHITECTURE.md            # This file
├── .gitignore                 # Git ignore rules
│
├── src/                       # Source code modules
│   ├── __init__.py
│   ├── detector.py           # YOLO detection module
│   ├── dock_manager.py       # Business logic module
│   └── ui.py                 # GUI module
│
├── utils/                     # Utility functions
│   ├── __init__.py
│   └── helpers.py            # Geometric helpers
│
└── models/                    # YOLO model storage
    ├── .gitkeep
    └── best.pt               # Your YOLO model (not in git)
```

## Extension Points

1. **Zone Configuration**: Add interactive zone drawing
2. **Parking Line Detection**: Improve line detection accuracy
3. **Logging**: Add state history and logging
4. **Alerts**: Add audio/visual alerts for violations
5. **Database**: Store detection history
6. **API**: Expose REST API for state queries
7. **Multi-Dock**: Support multiple dock zones

## Dependencies

- **ultralytics**: YOLO model inference
- **opencv-python**: Video processing and image operations
- **Pillow**: Image handling for UI
- **tkinter**: GUI framework (usually included with Python)
- **numpy**: Numerical operations

## Configuration Requirements

Before running:
1. Place YOLO model in `models/best.pt`
2. Update `CLASS_IDS` in `config.py` to match your model
3. Configure `ZONE_COORDINATES` (or set via UI)
4. Configure `PARKING_LINE_POINTS` (or set via UI)
5. Set `VIDEO_SOURCE` (0 for webcam or file path)
