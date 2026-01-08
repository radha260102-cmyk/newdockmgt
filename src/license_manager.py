"""
License Manager for Keygen API-based licensing
Handles online validation and offline fallback
"""
import os
import json
import requests
import sys
from datetime import datetime, timezone
import traceback


class LicenseManager:
    """Manages license validation using Keygen API"""
    
    def __init__(self, license_key=None, cache_file="license_cache.json"):
        """
        Initialize License Manager
        Args:
            license_key: License key string (if None, will try to load from cache)
            cache_file: Path to cache file for offline license data
        """
        self.license_key = license_key
        # Resolve cache file path relative to exe directory when frozen
        if getattr(sys, 'frozen', False):
            import config
            self.cache_file = config.get_resource_path(cache_file)
        else:
            self.cache_file = cache_file
        self.license_data = None
        self.api_url = "https://api.keygen.sh/v1/accounts/radha260102/licenses/actions/validate-key"
        self.api_headers = {
            'Content-Type': 'application/vnd.api+json',
            'Accept': 'application/vnd.api+json'
        }
        self.api_payload = {
            "meta": {
                "key": None,  # Will be set when validating
                "scope": {
                    "product": "b170c0b1-f215-4622-916e-2aa6657c1fa5",
                    "policy": "74b096d5-d69a-4e3f-aecf-d7c50d4881f8"
                }
            }
        }
    
    def validate_license(self):
        """
        Validate license key - tries API first, falls back to cache
        Returns:
            dict: {
                'valid': bool,
                'expired': bool,
                'message': str,
                'data': dict (license data if valid)
            }
        """
        # Try to get license key from cache if not provided
        if not self.license_key:
            cached_data = self.load_from_cache()
            if cached_data and cached_data.get('key'):
                self.license_key = cached_data.get('key')
                print(f"Loaded license key from cache")
        
        if not self.license_key:
            return {
                'valid': False,
                'expired': False,
                'message': 'No license key found. Please provide a valid license key.',
                'data': None
            }
        
        # Try API validation first
        api_result = self.validate_via_api()
        
        # Check API result - even if API call succeeded, check if license is expired/invalid
        # Note: Cache is already updated in validate_via_api() for all API responses (even expired/invalid)
        if api_result.get('valid') and not api_result.get('expired'):
            # API validation successful and license is valid - update config
            if api_result.get('data'):
                self.update_config_with_license_data(api_result['data'])
                self.license_data = api_result['data']
            return api_result
        elif api_result.get('expired') or (api_result.get('data') and api_result['data'].get('expired')):
            # License is expired according to API - cache already updated, but don't use it, exit
            if api_result.get('data'):
                self.license_data = api_result['data']  # Store for reference
            return {
                'valid': False,
                'expired': True,
                'message': api_result.get('message', 'License expired according to API'),
                'data': api_result.get('data')
            }
        else:
            # API failed - try cache
            print(f"API validation failed: {api_result['message']}")
            print("Attempting to use cached license data...")
            
            cached_result = self.validate_from_cache()
            if cached_result['valid']:
                print("Using cached license data (offline mode)")
                return cached_result
            else:
                # Both API and cache failed
                return {
                    'valid': False,
                    'expired': cached_result.get('expired', False),
                    'message': f"License validation failed. API: {api_result['message']}, Cache: {cached_result['message']}",
                    'data': None
                }
    
    def validate_via_api(self):
        """
        Validate license via Keygen API
        Returns:
            dict: Validation result
        """
        if not self.license_key:
            return {
                'valid': False,
                'expired': False,
                'message': 'No license key provided',
                'data': None
            }
        
        try:
            payload = self.api_payload.copy()
            payload['meta']['key'] = self.license_key
            
            print(f"Validating license via API...")
            response = requests.post(
                self.api_url,
                headers=self.api_headers,
                json=payload,
                timeout=10  # 10 second timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract license information
                license_info = self._parse_api_response(data)
                
                # Always save API response to cache, even if expired/invalid
                # This ensures we have the latest data from API
                self.save_to_cache(license_info)
                
                # Always check the API response data - even if API call succeeded,
                # the license might be expired or invalid according to the response
                if license_info['valid'] and not license_info['expired']:
                    # License is valid and not expired - update config with latest data
                    self.update_config_with_license_data(license_info)
                    return {
                        'valid': True,
                        'expired': False,
                        'message': 'License validated successfully',
                        'data': license_info
                    }
                else:
                    # License is invalid or expired according to API response
                    # Cache has already been updated above
                    return {
                        'valid': False,
                        'expired': license_info.get('expired', False),
                        'message': license_info.get('message', 'License validation failed'),
                        'data': license_info  # Return data even if invalid for debugging
                    }
            else:
                error_msg = f"API returned status {response.status_code}"
                try:
                    error_data = response.json()
                    if 'errors' in error_data:
                        error_msg = error_data['errors'][0].get('detail', error_msg)
                except:
                    pass
                
                return {
                    'valid': False,
                    'expired': False,
                    'message': f"API error: {error_msg}",
                    'data': None
                }
                
        except requests.exceptions.Timeout:
            return {
                'valid': False,
                'expired': False,
                'message': 'API request timed out (offline or network issue)',
                'data': None
            }
        except requests.exceptions.ConnectionError:
            return {
                'valid': False,
                'expired': False,
                'message': 'Cannot connect to API (offline or network issue)',
                'data': None
            }
        except Exception as e:
            return {
                'valid': False,
                'expired': False,
                'message': f'API validation error: {str(e)}',
                'data': None
            }
    
    def _parse_api_response(self, api_data):
        """
        Parse Keygen API response
        Args:
            api_data: JSON response from API
        Returns:
            dict: Parsed license information
        """
        try:
            # Keygen API response structure
            data = api_data.get('data', {})
            attributes = data.get('attributes', {})
            
            # Extract license details
            license_info = {
                'key': self.license_key,
                'valid': True,
                'expired': False,
                'status': attributes.get('status', 'unknown'),
                'expiry_date': None,
                'created_at': attributes.get('created', None),
                'updated_at': attributes.get('updated', None),
                'metadata': attributes.get('metadata', {}),
                'raw_data': api_data
            }
            
            # Check expiry if available
            expiry = attributes.get('expiry', None)
            if expiry:
                try:
                    # Parse expiry date
                    expiry_dt = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
                    now = datetime.now(timezone.utc)
                    
                    license_info['expiry_date'] = expiry_dt.isoformat()
                    
                    if expiry_dt < now:
                        license_info['expired'] = True
                        license_info['valid'] = False
                        license_info['message'] = f'License expired on {expiry_dt.strftime("%Y-%m-%d %H:%M:%S")}'
                except Exception as e:
                    print(f"Warning: Could not parse expiry date: {e}")
            
            # Check status
            status = attributes.get('status', '').upper()
            if status in ['SUSPENDED', 'REVOKED', 'EXPIRED']:
                license_info['valid'] = False
                license_info['expired'] = (status == 'EXPIRED')
                license_info['message'] = f'License status: {status}'
            
            return license_info
            
        except Exception as e:
            return {
                'key': self.license_key,
                'valid': False,
                'expired': False,
                'message': f'Error parsing API response: {str(e)}',
                'raw_data': api_data
            }
    
    def update_config_with_license_data(self, license_data):
        """
        Update config.py with latest license key from API response
        Args:
            license_data: License information dict from API
        """
        try:
            # Get the license key from the API response
            api_key = license_data.get('key', self.license_key)
            if not api_key:
                return
            
            # Read current config.py
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.py')
            if not os.path.exists(config_path):
                print(f"Warning: config.py not found at {config_path}")
                return
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config_content = f.read()
            
            # Update LICENSE_KEY in config
            import re
            # Pattern to match LICENSE_KEY assignment - handles both single and double quotes
            # Match: _license_key_env = os.getenv('LICENSE_KEY', "old_key")
            pattern = r"(_license_key_env = os\.getenv\('LICENSE_KEY',\s*)([\"'])([^\"']*)\2\)"
            
            def replacement_func(match):
                quote_char = match.group(2)  # Preserve the original quote type
                return f"{match.group(1)}{quote_char}{api_key}{quote_char})"
            
            if re.search(pattern, config_content):
                config_content = re.sub(pattern, replacement_func, config_content)
                
                # Write updated config
                with open(config_path, 'w', encoding='utf-8') as f:
                    f.write(config_content)
                
                print(f"✓ Updated LICENSE_KEY in config.py with latest data from API")
            else:
                print(f"Warning: Could not find LICENSE_KEY pattern in config.py to update")
                
        except Exception as e:
            print(f"Warning: Could not update config.py: {e}")
    
    def save_to_cache(self, license_data):
        """
        Save license data to cache file (encrypted when running as exe)
        Args:
            license_data: License information dict
        """
        try:
            cache_data = {
                'key': license_data.get('key', self.license_key),
                'status': license_data.get('status', 'unknown'),
                'expiry_date': license_data.get('expiry_date'),
                'expired': license_data.get('expired', False),
                'valid': license_data.get('valid', False),
                'cached_at': datetime.now(timezone.utc).isoformat(),
                'raw_data': license_data.get('raw_data', {})
            }
            
            if getattr(sys, 'frozen', False):
                # Running as exe - use encrypted storage
                from dock_utils.encrypted_storage import save_encrypted_data
                save_encrypted_data(cache_data, self.cache_file)
            else:
                # Development mode - save as plain JSON
                with open(self.cache_file, 'w') as f:
                    json.dump(cache_data, f, indent=2)
                print(f"License data cached to {self.cache_file}")
            
        except Exception as e:
            print(f"Warning: Could not save license cache: {e}")
    
    def load_from_cache(self):
        """
        Load license data from cache file (encrypted when running as exe)
        Returns:
            dict: Cached license data or None
        """
        if getattr(sys, 'frozen', False):
            # Running as exe - try encrypted storage first
            from dock_utils.encrypted_storage import load_encrypted_data
            cache_data = load_encrypted_data(self.cache_file)
            if cache_data is not None:
                return cache_data
            # Fallback to plain JSON if encrypted file doesn't exist (migration)
            if os.path.exists(self.cache_file):
                try:
                    with open(self.cache_file, 'r') as f:
                        return json.load(f)
                except:
                    return None
            return None
        else:
            # Development mode - load from plain JSON
            if not os.path.exists(self.cache_file):
                return None
            try:
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                return cache_data
            except Exception as e:
                print(f"Warning: Could not load license cache: {e}")
                return None
    
    def validate_from_cache(self):
        """
        Validate license using cached data
        Returns:
            dict: Validation result
        """
        cache_data = self.load_from_cache()
        
        if not cache_data:
            return {
                'valid': False,
                'expired': False,
                'message': 'No cached license data found',
                'data': None
            }
        
        # Check if cached data is expired
        if cache_data.get('expired', False):
            return {
                'valid': False,
                'expired': True,
                'message': 'Cached license is expired',
                'data': cache_data
            }
        
        # Check expiry date if available
        expiry_date = cache_data.get('expiry_date')
        if expiry_date:
            try:
                expiry_dt = datetime.fromisoformat(expiry_date.replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                
                if expiry_dt < now:
                    return {
                        'valid': False,
                        'expired': True,
                        'message': f'License expired on {expiry_dt.strftime("%Y-%m-%d %H:%M:%S")}',
                        'data': cache_data
                    }
            except Exception as e:
                print(f"Warning: Could not parse cached expiry date: {e}")
        
        # Check status
        status = cache_data.get('status', '').upper()
        if status in ['SUSPENDED', 'REVOKED', 'EXPIRED']:
            return {
                'valid': False,
                'expired': (status == 'EXPIRED'),
                'message': f'License status: {status}',
                'data': cache_data
            }
        
        # License appears valid from cache
        self.license_data = cache_data
        return {
            'valid': True,
            'expired': False,
            'message': 'License valid (from cache)',
            'data': cache_data
        }
    
    def check_license_and_exit_if_invalid(self):
        """
        Check license and exit application if invalid/expired/missing
        This is the main method to call at application startup
        """
        print("\n" + "=" * 50)
        print("License Validation")
        print("=" * 50)
        
        result = self.validate_license()
        
        # Check if license is expired or invalid - check both result and data
        is_expired = result.get('expired', False) or (result.get('data') and result['data'].get('expired', False))
        is_invalid = not result.get('valid', False)
        
        if is_expired:
            print(f"\n❌ LICENSE EXPIRED: {result.get('message', 'License has expired')}")
            if result.get('data') and result['data'].get('expiry_date'):
                try:
                    expiry_dt = datetime.fromisoformat(result['data']['expiry_date'].replace('Z', '+00:00'))
                    print(f"   Expired on: {expiry_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                except:
                    pass
            print("   Please renew your license.")
            print("\nApplication will now exit.")
            sys.exit(1)
        
        if is_invalid:
            print(f"\n❌ LICENSE ERROR: {result.get('message', 'License is invalid')}")
            print("   Please ensure you have a valid license key.")
            print("\nApplication will now exit.")
            sys.exit(1)
        
        # License is valid
        status = result['data'].get('status', 'unknown')
        expiry = result['data'].get('expiry_date')
        
        print(f"\n✓ License validated successfully")
        print(f"  Status: {status}")
        if expiry:
            try:
                expiry_dt = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
                print(f"  Expiry: {expiry_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Calculate days remaining
                now = datetime.now(timezone.utc)
                days_left = (expiry_dt - now).days
                if days_left > 0:
                    print(f"  Days remaining: {days_left}")
                else:
                    print(f"  ⚠️ License expires today!")
            except:
                print(f"  Expiry: {expiry}")
        
        return True

