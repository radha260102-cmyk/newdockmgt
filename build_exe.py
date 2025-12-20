"""
Build script for creating executable from Dock Management System
Usage: python build_exe.py
"""
import os
import sys
import subprocess
import shutil

def main():
    print("=" * 60)
    print("Dock Management System - Executable Builder")
    print("=" * 60)
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
        print(f"✓ PyInstaller found: {PyInstaller.__version__}")
    except ImportError:
        print("\n❌ PyInstaller is not installed.")
        print("Please install it using: pip install pyinstaller")
        return 1
    
    # Check if required files exist
    if not os.path.exists('main.py'):
        print("\n❌ main.py not found. Please run this script from the project root.")
        return 1
    
    if not os.path.exists('build_exe.spec'):
        print("\n❌ build_exe.spec not found. Please ensure the spec file exists.")
        return 1
    
    # Clean previous builds
    print("\nCleaning previous builds...")
    for folder in ['build', 'dist']:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
                print(f"  ✓ Removed {folder}/")
            except Exception as e:
                print(f"  ⚠ Could not remove {folder}/: {e}")
    
    # Build the executable
    print("\nBuilding executable...")
    print("This may take several minutes...\n")
    
    try:
        # Run PyInstaller with the spec file
        result = subprocess.run(
            [sys.executable, '-m', 'PyInstaller', 'build_exe.spec', '--clean'],
            check=True,
            capture_output=False
        )
        
        # Copy models directory to dist directory (keep it external)
        print("\nCopying models directory (external)...")
        dist_dir = os.path.join('dist', 'DockManagementSystem')
        
        if os.path.exists(dist_dir):
            # Copy models directory (keep it external)
            models_src = 'models'
            models_dest = os.path.join(dist_dir, 'models')
            if os.path.exists(models_src):
                try:
                    if os.path.exists(models_dest):
                        shutil.rmtree(models_dest)
                    shutil.copytree(models_src, models_dest)
                    print(f"  ✓ Copied {models_src}/ directory")
                except Exception as e:
                    print(f"  ⚠ Could not copy {models_src}/: {e}")
            else:
                print(f"  ⚠ {models_src}/ directory not found (models must be placed manually)")
        
        print("\n" + "=" * 60)
        print("✓ Build completed successfully!")
        print("=" * 60)
        print(f"\nExecutable location: dist/DockManagementSystem/DockManagementSystem.exe")
        print("\nExternal files (editable, in exe directory):")
        print("  - models/ (directory with model files)")
        print("\nBundled in exe:")
        print("  - config.py (bundled, not external)")
        print("  - zone_config.json (bundled, not external)")
        print("  - settings.json (bundled, not external)")
        print("  - All libraries (torch, ultralytics, opencv, etc.)")
        print("\nAuto-created files (in exe directory):")
        print("  - license_cache.json (created automatically)")
        print("\nNote:")
        print("  - The entire 'dist/DockManagementSystem' folder contains your application")
        print("  - Copy the entire folder to distribute your application")
        print("  - Only models/ folder is external and can be replaced without rebuilding")
        print("  - All libraries are bundled in the exe (no separate installation needed)")
        print("\nTo run: dist/DockManagementSystem/DockManagementSystem.exe")
        
        return 0
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Build failed with error code {e.returncode}")
        return 1
    except Exception as e:
        print(f"\n❌ Build failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())

