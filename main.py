"""
Main Entry Point for Dock Management System
"""
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'dock_utils'))

from src.detector import YOLODetector
from src.dock_manager import DockManager
from src.ui import DockManagementUI
from src.license_manager import LicenseManager
import config


def main():
    """Main function to initialize and run the application"""
    print("=" * 50)
    print("Dock Management System")
    print("=" * 50)
    
    # License validation - MUST pass before continuing (always enabled)
    try:
        license_manager = LicenseManager(
            license_key=config.LICENSE_KEY,
            cache_file=config.LICENSE_CACHE_FILE
        )
        license_manager.check_license_and_exit_if_invalid()
    except SystemExit:
        # License check failed, application should exit
        raise
    except Exception as e:
        print(f"\n❌ LICENSE VALIDATION ERROR: {str(e)}")
        print("Application will now exit.")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Check if model exists
    if not os.path.exists(config.MODEL_PATH):
        print(f"\nERROR: Model file not found at {config.MODEL_PATH}")
        print("Please ensure your YOLO model file is placed in the models/ directory")
        print("and update MODEL_PATH in config.py if needed.")
        return
    
    try:
        # Check CUDA availability
        import torch
        if torch.cuda.is_available():
            print(f"\n✓ CUDA GPU detected: {torch.cuda.get_device_name(0)}")
            print(f"  GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
        else:
            print("\n⚠ CUDA GPU not available. Using CPU (slower performance).")
            if config.USE_GPU:
                print("  To use GPU, install CUDA-enabled PyTorch:")
                print("  Visit: https://pytorch.org/get-started/locally/")
        
        # Initialize dock manager first to get zone coordinates
        print("\nInitializing dock manager...")
        dock_manager = DockManager()
        
        # Initialize detector with zone coordinates for filtering
        print("Initializing YOLO detector...")
        detector = YOLODetector(zone_coordinates=dock_manager.zone_coordinates)
        
        # Check zone configuration
        zone_configured = dock_manager.zone_coordinates is not None and len(dock_manager.zone_coordinates) >= 3
        line_configured = dock_manager.parking_line_points is not None and len(dock_manager.parking_line_points) >= 2
        
        if zone_configured and line_configured:
            print(f"✓ Zone configured: {len(dock_manager.zone_coordinates)} points")
            print(f"✓ Parking line configured: {len(dock_manager.parking_line_points)} points")
        else:
            print("\n⚠ Zone configuration needed:")
            if not zone_configured:
                print("  - Zone coordinates not configured (need at least 3 points)")
            if not line_configured:
                print("  - Parking line not configured (need at least 2 points)")
            print(f"\nRun 'python configure_zones.py' to configure zones and parking line.")
        
        # Initialize and run UI
        print("\nStarting UI...")
        ui = DockManagementUI(detector, dock_manager)
        ui.run()
        
    except KeyboardInterrupt:
        print("\n\nApplication interrupted by user")
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup resources
        try:
            if 'dock_manager' in locals():
                dock_manager.cleanup()
        except:
            pass


if __name__ == "__main__":
    main()
