# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Dock Management System
"""

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all data files and submodules
datas = [
    ('zone_config.json', '.'),
    ('settings.json', '.'),  # Include if exists, will be created if not
    ('license_cache.json', '.'),  # Include if exists, will be created if not
    ('models', 'models'),  # Include models directory
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
    'pymodbus',
    'pymodbus.client',
    'pymodbus.client.sync',
    'pymodbus.constants',
    'pymodbus.payload',
    'pymodbus.transaction',
    'pymodbus.client.tcp',
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
    'ultralytics',  # For YOLOv5 via torch.hub
    'ultralytics.yolo',  # YOLOv5 submodules
    'yolov5',  # Alternative YOLOv5 package if installed
    'yolov5.models',  # YOLOv5 models submodule
    'yolov5.utils',  # YOLOv5 utils submodule
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

# Collect yolov5 data files and submodules
try:
    import yolov5
    yolov5_datas = collect_data_files('yolov5')
    datas += yolov5_datas
    yolov5_submodules = collect_submodules('yolov5')
    hiddenimports.extend(yolov5_submodules)
except:
    pass

# Collect ultralytics data files (for torch.hub yolov5)
try:
    import ultralytics
    ultralytics_datas = collect_data_files('ultralytics')
    datas += ultralytics_datas
    ultralytics_submodules = collect_submodules('ultralytics')
    hiddenimports.extend(ultralytics_submodules)
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
    import pymodbus
    import tkinter
    # Try to import yolov5 at build time
    try:
        import yolov5
    except:
        pass
    # Try to import ultralytics at build time
    try:
        import ultralytics
    except:
        pass
except Exception as e:
    print(f"Warning during build-time imports: {e}")

# Analyze the main script
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

