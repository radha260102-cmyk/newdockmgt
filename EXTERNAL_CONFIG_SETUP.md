# External Configuration Files and Models Setup

This document explains how configuration files and models are handled as external files (outside the executable bundle).

## Overview

Configuration files and models are kept **EXTERNAL** to the executable, allowing you to edit/replace them without rebuilding:

- `config.py` - Main configuration Python file
- `zone_config.json` - Zone coordinates configuration
- `settings.json` - Application settings
- `models/` - Directory containing YOLO model files (.pt files)
- `license_cache.json` - License cache (auto-created, managed by app - stays internal)

## How It Works

1. **During Build**: 
   - Config files and models directory are NOT included in the PyInstaller bundle
   - `config.py` is bundled as a fallback, but an external copy takes precedence
   - The build script automatically copies all config files and models directory to the `dist/DockManagementSystem/` directory
   - All Python libraries (torch, ultralytics, opencv, pyModbusTCP, etc.) are bundled in the exe

2. **At Runtime**:
   - When running as an executable, `main.py` adds the executable's directory to `sys.path` first
   - This ensures that external `config.py` (if present) is loaded instead of the bundled version
   - JSON config files and models are read from the executable's directory using `config.get_resource_path()`
   - All libraries are loaded from the bundled executable (no external dependencies needed)

## File Locations

After building, configuration files and models are in the same directory as `DockManagementSystem.exe`:

```
dist/DockManagementSystem/
  ├── DockManagementSystem.exe  ← Main executable (all libraries bundled)
  ├── config.py                 ← External, editable
  ├── zone_config.json          ← External, editable
  ├── settings.json             ← External, editable
  ├── models/                   ← External, replaceable
  │   ├── best_doc4.pt
  │   └── [other model files]
  ├── license_cache.json        ← Auto-created (managed by app)
  └── [bundled DLLs and libraries]
```

## Editing Configuration

You can edit or replace any of these files directly:
- Edit `config.py` to change default Python configuration values
- Edit `zone_config.json` to update zone coordinates
- Edit `settings.json` to update application settings
- Replace or add model files in `models/` directory
- `license_cache.json` is managed automatically by the application (don't edit manually)

No need to rebuild the executable after editing these files!

## Distribution

To distribute the application:
1. Copy the entire `dist/DockManagementSystem` folder
2. Ensure all external files (config.py, JSON files, models/) are included
3. The executable is self-contained - no Python or library installation needed on target machine

