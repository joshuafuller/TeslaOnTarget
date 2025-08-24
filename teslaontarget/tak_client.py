"""TAK server connection and communication handling."""

import socket
import time
import logging
import threading
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class TAKClient:
    """Handle connection and communication with TAK server."""
    
    def __init__(self, cot_url):
        """Initialize TAK client.
        
        Args:
            cot_url: TAK server URL (e.g., 'tcp://192.168.1.100:8085')
        """
        parsed = urlparse(cot_url)
        self.host = parsed.hostname
        self.port = parsed.port
        self.socket = None
        self.connected = False
        self.reconnect_thread = None
        self.stop_reconnect = threading.Event()
        self.reconnect_interval = 5  # seconds between reconnection attempts
        
    def connect(self):
        """Connect to TAK server."""
        try:
            if self.socket:
                self.disconnect()
                
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.host, self.port))
            self.connected = True
            logger.info(f"Connected to TAK server at {self.host}:{self.port}")
            # Set TCP_NODELAY to send packets immediately
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            return True
            
        except socket.error as e:
            logger.error(f"Failed to connect to TAK server: {e}")
            self.connected = False
            return False
            
    def disconnect(self):
        """Disconnect from TAK server."""
        # Stop reconnection thread
        self.stop_reconnect.set()
        if self.reconnect_thread and self.reconnect_thread.is_alive():
            self.reconnect_thread.join(timeout=2)
            
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        self.connected = False
        logger.info("Disconnected from TAK server")
        
    def send_cot(self, cot_message):
        """Send CoT message to TAK server with infinite retry logic.
        
        Args:
            cot_message: Formatted CoT message bytes
            
        Returns:
            bool: True if sent successfully
        """
        retry_count = 0
        while True:
            if not self.connected:
                retry_count += 1
                logger.warning(f"Not connected to TAK server, attempting to connect (attempt {retry_count})")
                if not self.connect():
                    logger.warning(f"Failed to connect to TAK server, retrying in 30 seconds...")
                    time.sleep(30)
                    continue
                    
            try:
                bytes_sent = self.socket.sendall(cot_message)
                logger.info(f"Sent CoT message to TAK server ({len(cot_message)} bytes)")
                # Log the entire message for debugging
                logger.info(f"CoT message sent: {cot_message.decode('utf-8', errors='ignore')}")
                return True
                
            except socket.error as e:
                logger.error(f"Failed to send CoT message: {e}")
                self.connected = False
                retry_count += 1
                logger.warning(f"Connection lost, retrying in 30 seconds... (attempt {retry_count})")
                time.sleep(30)
                continue
    
    def _background_reconnect(self):
        """Background thread to keep trying to reconnect to TAK server."""
        logger.info("Starting background reconnection thread")
        while not self.stop_reconnect.is_set():
            if not self.connected:
                logger.info(f"Attempting background reconnection to TAK server...")
                if self.connect():
                    logger.info("Background reconnection successful!")
                    return  # Exit thread when successfully connected
                else:
                    logger.warning(f"Background reconnection failed, retrying in {self.reconnect_interval} seconds")
            
            # Wait before next attempt, but check for stop signal
            self.stop_reconnect.wait(self.reconnect_interval)
        
        logger.info("Background reconnection thread stopped")
    
    def start_background_reconnect(self):
        """Start background reconnection thread if not already running."""
        if not self.connected and (not self.reconnect_thread or not self.reconnect_thread.is_alive()):
            self.stop_reconnect.clear()
            self.reconnect_thread = threading.Thread(target=self._background_reconnect, daemon=True)
            self.reconnect_thread.start()
            logger.info("Started background reconnection thread")
            
    def ensure_connected(self):
        """Ensure connection to TAK server is active."""
        if not self.connected:
            return self.connect()
            
        # Test connection with a small timeout
        try:
            self.socket.setblocking(0)
            data = self.socket.recv(1, socket.MSG_PEEK)
            if not data:
                # Connection closed
                self.connected = False
                return self.connect()
        except socket.error:
            # No data available (normal) or connection error
            pass
        finally:
            self.socket.setblocking(1)
            
        return True