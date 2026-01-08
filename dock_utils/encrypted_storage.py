"""
Encrypted storage utility for settings and license data
Stores data in encrypted format when running as executable
Uses AES encryption with a bundled key
"""
import os
import sys
import json
from cryptography.fernet import Fernet


# Encryption key bundled in exe (Fernet format - base64-urlsafe-encoded 32-byte key)
# This key is hardcoded and will be compiled into the exe binary
# Not easily readable without reverse engineering the exe
# Fernet keys are 32 bytes, base64-urlsafe-encoded (44 characters)
# This key is generated once and bundled - same key used for all encryption/decryption
_ENCRYPTION_KEY = b'VGecwETdB5rFz1wtVzNBjzHIewOz2RpNDbP8-kETB3c='
# Cache for Fernet instance
_FERNET_INSTANCE = None


def _get_encryption_key():
    """
    Get the encryption key (bundled in exe)
    Returns:
        bytes: Fernet encryption key (base64-urlsafe-encoded 32-byte key)
    """
    # Use the hardcoded key directly - it's already in proper Fernet format
    # This key is bundled in the exe and not easily accessible
    return _ENCRYPTION_KEY


def _get_fernet():
    """Get Fernet cipher instance for encryption/decryption (cached)"""
    global _FERNET_INSTANCE
    if _FERNET_INSTANCE is None:
        key = _get_encryption_key()
        _FERNET_INSTANCE = Fernet(key)
    return _FERNET_INSTANCE


def _get_encrypted_file_path(filename):
    """Get path for encrypted file (in exe directory when frozen)"""
    if getattr(sys, 'frozen', False):
        # Running as exe - store in exe directory with .encrypted extension
        exe_dir = os.path.dirname(sys.executable)
        # Change extension to .encrypted to make it non-readable as JSON
        base_name = os.path.splitext(filename)[0]
        return os.path.join(exe_dir, f"{base_name}.encrypted")
    else:
        # Development mode - use original filename
        return filename


def save_encrypted_data(data_dict, filename):
    """
    Save data dictionary in encrypted format using AES encryption
    Args:
        data_dict: Dictionary to save
        filename: Original filename (will be changed to .encrypted when frozen)
    Returns:
        bool: True if successful
    """
    try:
        # Convert dict to JSON string
        json_str = json.dumps(data_dict, indent=None)  # No indent to reduce size
        json_bytes = json_str.encode('utf-8')
        
        # Encrypt using Fernet (AES-128 in CBC mode with HMAC)
        fernet = _get_fernet()
        encrypted_bytes = fernet.encrypt(json_bytes)
        
        # Save to file (already base64 encoded by Fernet)
        file_path = _get_encrypted_file_path(filename)
        with open(file_path, 'wb') as f:
            f.write(encrypted_bytes)
        
        if getattr(sys, 'frozen', False):
            print(f"Settings saved to encrypted file: {os.path.basename(file_path)}")
        else:
            print(f"Settings saved to {file_path}")
        return True
    except Exception as e:
        print(f"Error saving encrypted data: {e}")
        import traceback
        traceback.print_exc()
        return False


def load_encrypted_data(filename):
    """
    Load data dictionary from encrypted format
    Args:
        filename: Original filename (will look for .encrypted version when frozen)
    Returns:
        dict: Loaded data or None if file doesn't exist or error
    """
    file_path = _get_encrypted_file_path(filename)
    
    if not os.path.exists(file_path):
        # Try original filename as fallback (for development or migration)
        if getattr(sys, 'frozen', False):
            # In exe mode, also try checking exe directory with original name
            exe_dir = os.path.dirname(sys.executable)
            fallback_path = os.path.join(exe_dir, filename)
            if os.path.exists(fallback_path):
                file_path = fallback_path
            else:
                return None
        else:
            return None
    
    try:
        # Read encrypted data
        with open(file_path, 'rb') as f:
            encrypted_bytes = f.read()
        
        # Decrypt using Fernet
        fernet = _get_fernet()
        json_bytes = fernet.decrypt(encrypted_bytes)
        
        # Parse JSON
        json_str = json_bytes.decode('utf-8')
        data_dict = json.loads(json_str)
        
        return data_dict
    except Exception as e:
        # If decryption fails, try reading as plain JSON (for migration from old format)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Try to read as JSON (might be old format)
                content = f.read()
                try:
                    return json.loads(content)
                except:
                    # Not valid JSON, decryption failed
                    print(f"Warning: Could not decrypt data from {file_path}: {e}")
                    return None
        except Exception as e2:
            print(f"Warning: Could not load encrypted data from {file_path}: {e}, {e2}")
            return None

