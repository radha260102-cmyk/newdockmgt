# Building Executable for Dock Management System

This guide explains how to create a standalone executable (.exe) file from the Dock Management System.

## Prerequisites

1. **Install PyInstaller**:
   ```bash
   pip install pyinstaller
   ```

2. **Ensure all dependencies are installed**:
   ```bash
   pip install -r requirements.txt
   ```

## Building the Executable

### Option 1: Using the Build Script (Recommended)

Simply run:
```bash
python build_exe.py
```

This script will:
- Check if PyInstaller is installed
- Clean previous builds
- Build the executable using `build_exe.spec`
- Provide instructions on where to find the executable

### Option 2: Using PyInstaller Directly

```bash
pyinstaller build_exe.spec --clean
```

## Output Location

After building, you'll find your executable in:
```
dist/DockManagementSystem/DockManagementSystem.exe
```

## Important Notes

1. **Distribution**: Copy the entire `dist/DockManagementSystem` folder to distribute your application. The folder contains:
   - `DockManagementSystem.exe` - The main executable
   - `models/` - Model files directory (if included)
   - Various DLL and dependency files
   - `zone_config.json`, `settings.json` - Configuration files

2. **Configuration Files**: 
   - `zone_config.json` and `settings.json` will be included if they exist
   - Users can edit these files to configure the application
   - If they don't exist, the application will create them on first run

3. **Models**: The `models/` directory structure is included, but you may need to ensure your model files are present when distributing.

4. **First Run**: The first time you run the executable, PyTorch may download YOLOv5 code via torch.hub. This requires an internet connection.

5. **File Size**: The executable folder will be large (several hundred MB) due to PyTorch and other dependencies. This is normal.

## Troubleshooting

### "Module not found" errors

If you encounter missing module errors:
1. Check that all dependencies are installed: `pip install -r requirements.txt`
2. The spec file includes hidden imports - if a module is still missing, add it to the `hiddenimports` list in `build_exe.spec`

### Large file size

The executable will be large due to:
- PyTorch libraries
- CUDA libraries (if GPU support is included)
- YOLOv5 dependencies
- OpenCV libraries

This is expected. Consider using UPX compression (already enabled in the spec file) to reduce size slightly.

### torch.hub download issues

If the executable fails to download YOLOv5 code:
- Ensure internet connection on first run
- Or pre-download YOLOv5 by running the Python script once before building

## Advanced: Creating a Single-File Executable

If you prefer a single .exe file (slower startup, but easier distribution):

1. Edit `build_exe.spec`
2. Change the EXE section to use `onefile=True` instead of directory mode
3. Note: This will make the executable slower to start and require extracting to a temp directory

The current spec uses directory mode which is recommended for this application due to:
- Large model files
- Need for editable configuration files
- Better performance (no extraction on startup)

