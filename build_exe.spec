# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Dock Management System
"""

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all data files and submodules
# NOTE: Only models folder is kept EXTERNAL to the exe
# Config files are bundled in the exe
datas = [
    ('config.py', '.'),  # Bundle config.py
    ('zone_config.json', '.'),  # Bundle zone_config.json if exists
    ('settings.json', '.'),  # Bundle settings.json if exists
    # Models directory is EXCLUDED - must be external (in exe directory)
    # license_cache.json will be auto-created in exe directory (no need to bundle)
]

# Hidden imports for modules that PyInstaller might miss
# Define this first so we can extend it below
hiddenimports = [
    'torch',
    'torch.nn',
    'torch.nn.functional',
    'torchvision',
    'cv2',
    'cv2.cv2',
    'numpy',
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'pandas',
    'requests',
    'pyModbusTCP',  # Note: The actual package name is pyModbusTCP (not pymodbus)
    'pyModbusTCP.client',
    'tkinter',
    'tkinter.ttk',
    'tkinter.messagebox',
    'tkinter.filedialog',
    'json',
    'queue',
    'threading',
    'time',
    'datetime',
    'collections',
    'urllib',
    'urllib.request',
    'urllib.error',
    'urllib.parse',
    'warnings',
    'traceback',
    'sys',
    'os',
    'logging',
    'logging.config',  # Required for YOLOv5/utils
    'logging.handlers',
    'ultralytics',  # For YOLOv5 via torch.hub
    'ultralytics.yolo',  # YOLOv5 submodules
    'ultralytics.models',  # YOLOv5 models
    'ultralytics.utils',  # YOLOv5 utils
    'ultralytics.nn',  # YOLOv5 neural network modules
    'ultralytics.trackers',  # YOLOv5 tracking
    'yolov5',  # YOLOv5 package (primary method)
    'yolov5.models',  # YOLOv5 models submodule
    'yolov5.utils',  # YOLOv5 utils submodule
    'yolov5.models.common',  # YOLOv5 common models
    'yolov5.utils.general',  # YOLOv5 general utils
    'yolov5.utils.augmentations',  # YOLOv5 augmentations
    'yolov5.utils.dataloaders',  # YOLOv5 dataloaders
    'hubconf',  # torch.hub support files
    'torch.hub',  # torch.hub module for loading YOLO
    'torch.utils',  # torch utilities
    'torch.jit',  # torch JIT compiler
]

# Collect torch and torchvision data files
try:
    torch_datas = collect_data_files('torch')
    datas += torch_datas
    # Also collect torch submodules
    torch_submodules = collect_submodules('torch')
    hiddenimports.extend(torch_submodules)
except:
    pass

# Collect yolov5 data files and submodules (CRITICAL - must be included)
try:
    import yolov5
    yolov5_datas = collect_data_files('yolov5')
    datas += yolov5_datas
    yolov5_submodules = collect_submodules('yolov5')
    hiddenimports.extend(yolov5_submodules)
    print(f"✓ Collected yolov5 package: {len(yolov5_submodules)} submodules")
except ImportError:
    print("⚠ Warning: yolov5 package not found. Make sure it's installed: pip install yolov5")
except Exception as e:
    print(f"⚠ Warning: Could not collect yolov5 files: {e}")

# Collect ultralytics data files (for torch.hub yolov5)
try:
    import ultralytics
    ultralytics_datas = collect_data_files('ultralytics')
    datas += ultralytics_datas
    ultralytics_submodules = collect_submodules('ultralytics')
    hiddenimports.extend(ultralytics_submodules)
except:
    pass

# Collect torch.hub cache data if it exists (YOLOv5 models cache)
try:
    import torch
    hub_cache = os.path.join(os.path.expanduser('~'), '.cache', 'torch', 'hub')
    if os.path.exists(hub_cache):
        # Collect ultralytics/yolov5 from hub cache if it exists
        yolov5_hub_path = os.path.join(hub_cache, 'ultralytics_yolov5_master')
        if os.path.exists(yolov5_hub_path):
            # This helps if torch.hub has already downloaded YOLOv5
            # Note: torch.hub will download at runtime if needed, but having this helps
            pass
except:
    pass

# Collect tkinter data files (if any)
try:
    tkinter_datas = collect_data_files('tkinter')
    datas += tkinter_datas
except:
    pass

# Collect cv2 (OpenCV) data files
try:
    cv2_datas = collect_data_files('cv2')
    datas += cv2_datas
except:
    pass

# Pre-import critical libraries to ensure PyInstaller detects them
# This is done at build time, not runtime
try:
    import torch
    import torchvision
    import cv2
    import numpy
    import PIL
    import pandas
    import requests
    try:
        import pyModbusTCP  # The actual package name
    except ImportError:
        pass
    import tkinter
    import logging  # Ensure logging is imported
    import logging.config  # Ensure logging.config is imported
    # Try to import yolov5 at build time (CRITICAL - ensures it's bundled)
    try:
        import yolov5
        print(f"✓ yolov5 package found: {yolov5.__version__ if hasattr(yolov5, '__version__') else 'unknown version'}")
    except ImportError:
        print("⚠ WARNING: yolov5 package not found. Install it with: pip install yolov5")
        print("  The executable may fail to load YOLO models without this package.")
    except Exception as e:
        print(f"⚠ Warning importing yolov5: {e}")
    # Try to import ultralytics at build time
    try:
        import ultralytics
    except:
        pass
except Exception as e:
    print(f"Warning during build-time imports: {e}")

# Analyze the main script
# Config files are bundled in the exe
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Create PYZ archive
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Create executable - directory mode (better for large apps with models)
# This creates a folder with the .exe and all dependencies
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # Put binaries in separate folder
    name='DockManagementSystem',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Keep console for debugging, set to False for windowed mode
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon file path here if you have one (e.g., 'icon.ico')
)

# Create COLLECT to bundle everything into a directory
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DockManagementSystem',
)

