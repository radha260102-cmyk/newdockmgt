"""
PLC Manager Module
Handles Modbus TCP communication with PLC for controlling dock lights
Runs in a separate thread to avoid blocking video processing
"""
import config
import threading
import queue
import time
from pyModbusTCP.client import ModbusClient


class PLCManager:
    """Manages PLC communication via Modbus TCP in a separate thread"""
    
    def __init__(self, host=None, port=None, auto_open=None, auto_close=None):
        """
        Initialize PLC Manager
        Args:
            host: PLC host address (defaults to config.PLC_HOST)
            port: PLC port (defaults to config.PLC_PORT)
            auto_open: Auto-open connection (defaults to config.PLC_AUTO_OPEN)
            auto_close: Auto-close connection (defaults to config.PLC_AUTO_CLOSE)
        """
        self.host = host or config.PLC_HOST
        self.port = port or config.PLC_PORT
        self.auto_open = auto_open if auto_open is not None else config.PLC_AUTO_OPEN
        self.auto_close = auto_close if auto_close is not None else config.PLC_AUTO_CLOSE
        
        # Initialize Modbus client
        # Note: pyModbusTCP doesn't support auto_open/auto_close in constructor
        # We'll handle connection manually
        self.client = ModbusClient(host=self.host, port=self.port)
        
        # Coil configurations
        self.green_coils = config.PLC_GREEN_LIGHT_COILS
        self.red_coils = config.PLC_RED_LIGHT_COILS
        self.yellow_coils = config.PLC_YELLOW_LIGHT_COILS
        self.coil_start_address = config.PLC_COIL_START_ADDRESS
        
        # Thread management
        self.is_running = False
        self.command_queue = queue.Queue(maxsize=10)  # Queue for state change commands
        self.plc_thread = None
        self.current_state = "UNKNOWN"
        
        # Connection status
        self.is_connected = False
        self.last_error = None
        
        # Start PLC thread if enabled
        if config.ENABLE_PLC:
            self.start()
    
    def start(self):
        """Start the PLC communication thread"""
        if self.is_running:
            return
        
        self.is_running = True
        self.plc_thread = threading.Thread(target=self._plc_loop, daemon=True)
        self.plc_thread.start()
        print(f"PLC Manager started (host: {self.host}, port: {self.port})")
    
    def stop(self):
        """Stop the PLC communication thread"""
        self.is_running = False
        if self.plc_thread and self.plc_thread.is_alive():
            self.plc_thread.join(timeout=2.0)
        if self.client and self.client.is_open:
            if self.auto_close:
                self.client.close()
        print("PLC Manager stopped")
    
    def update_state(self, new_state):
        """
        Queue a state change command (non-blocking)
        Args:
            new_state: New dock state ('RED', 'YELLOW', 'GREEN')
        """
        if not config.ENABLE_PLC:
            return
        
        if not self.is_running:
            return
        
        # Only queue if state changed
        if new_state != self.current_state:
            try:
                self.command_queue.put_nowait(new_state)
            except queue.Full:
                # Queue is full, drop oldest command and add new one
                try:
                    self.command_queue.get_nowait()
                    self.command_queue.put_nowait(new_state)
                except queue.Empty:
                    pass
    
    def _plc_loop(self):
        """Main PLC communication loop running in separate thread"""
        reconnect_delay = 2.0  # Wait 2 seconds before reconnecting
        last_reconnect_attempt = 0
        
        while self.is_running:
            try:
                # Check connection status
                if not self.client.is_open:
                    # Try to reconnect if enough time has passed
                    current_time = time.time()
                    if current_time - last_reconnect_attempt >= reconnect_delay:
                        try:
                            if self.client.open():
                                self.is_connected = True
                                self.last_error = None
                                print(f"✓ PLC connected to {self.host}:{self.port}")
                            else:
                                self.is_connected = False
                                self.last_error = "Connection failed"
                        except Exception as e:
                            self.is_connected = False
                            self.last_error = str(e)
                        last_reconnect_attempt = current_time
                else:
                    self.is_connected = True
                
                # Process queued commands
                try:
                    # Get command with timeout to allow checking is_running
                    new_state = self.command_queue.get(timeout=0.1)
                    
                    if self.is_connected and self.client.is_open:
                        # Update coils based on state
                        success = self._update_coils(new_state)
                        if success:
                            self.current_state = new_state
                            print(f"✓ PLC coils updated for state: {new_state}")
                        else:
                            print(f"✗ Failed to update PLC coils for state: {new_state}")
                    else:
                        # Connection not available, just update current state
                        self.current_state = new_state
                        print(f"⚠ PLC not connected, state change queued: {new_state}")
                
                except queue.Empty:
                    # No commands, continue loop
                    pass
                
                # Small sleep to prevent busy waiting
                time.sleep(0.01)
                
            except Exception as e:
                self.last_error = str(e)
                print(f"✗ PLC error: {e}")
                time.sleep(0.1)
    
    def _update_coils(self, state):
        """
        Update PLC coils based on dock state
        Args:
            state: Dock state ('RED', 'YELLOW', 'GREEN')
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            coils_to_write = None
            
            if state == "GREEN":
                coils_to_write = self.green_coils
            elif state == "RED":
                coils_to_write = self.red_coils
            elif state == "YELLOW":
                coils_to_write = self.yellow_coils
            else:
                # Unknown state, turn off all lights (all False)
                coils_to_write = [False] * 8
            
            if coils_to_write is None:
                return False
            
            # Write coils to PLC
            # pyModbusTCP uses write_multiple_coils(address, values)
            result = self.client.write_multiple_coils(self.coil_start_address, coils_to_write)
            
            return result
            
        except Exception as e:
            self.last_error = str(e)
            print(f"✗ Error updating PLC coils: {e}")
            return False
    
    def get_status(self):
        """
        Get PLC connection status
        Returns:
            dict: Status information
        """
        return {
            'is_connected': self.is_connected and self.client.is_open if self.client else False,
            'is_running': self.is_running,
            'current_state': self.current_state,
            'last_error': self.last_error,
            'host': self.host,
            'port': self.port,
            'queue_size': self.command_queue.qsize()
        }
    
    def __del__(self):
        """Cleanup on deletion"""
        self.stop()

