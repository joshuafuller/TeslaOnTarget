"""TAK server connection and communication handling."""

import socket
import time
import logging
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
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        self.connected = False
        logger.info("Disconnected from TAK server")
        
    def send_cot(self, cot_message):
        """Send CoT message to TAK server.
        
        Args:
            cot_message: Formatted CoT message bytes
            
        Returns:
            bool: True if sent successfully
        """
        if not self.connected:
            logger.warning("Not connected to TAK server, attempting to connect...")
            if not self.connect():
                logger.error("Failed to connect to TAK server")
                return False
                
        try:
            bytes_sent = self.socket.sendall(cot_message)
            logger.info(f"Sent CoT message to TAK server ({len(cot_message)} bytes)")
            # Log the entire message for debugging
            logger.info(f"CoT message sent: {cot_message.decode('utf-8', errors='ignore')}")
            return True
            
        except socket.error as e:
            logger.error(f"Failed to send CoT message: {e}")
            self.connected = False
            return False
            
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