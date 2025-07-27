"""Configuration handling for TeslaOnTarget."""

import os
import sys
import logging

logger = logging.getLogger(__name__)


class Config:
    """Configuration handler with defaults and validation."""
    
    # Default configuration values
    COT_URL = "tcp://YOUR-TAK-SERVER:8085"
    API_LOOP_DELAY = 10
    DEAD_RECKONING_DELAY = 1
    TESLA_USERNAME = None
    LAST_POSITION_FILE = "last_known_position.json"
    MPH_TO_MS = 0.44704
    
    @classmethod
    def load_from_file(cls, config_path=None):
        """Load configuration from Python file.
        
        Args:
            config_path: Path to config.py file
        """
        if config_path is None:
            # Look for config.py in parent directory
            parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(parent_dir, 'config.py')
            
        if not os.path.exists(config_path):
            logger.warning(f"Config file not found at {config_path}, using defaults")
            return
            
        try:
            # Import config module dynamically
            sys.path.insert(0, os.path.dirname(config_path))
            import config
            
            # Update class attributes with config values
            for attr in dir(config):
                if not attr.startswith('_'):
                    setattr(cls, attr, getattr(config, attr))
                    
            logger.info(f"Configuration loaded from {config_path}")
            
        except Exception as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
            
    @classmethod
    def validate(cls):
        """Validate configuration values.
        
        Returns:
            bool: True if configuration is valid
        """
        if not cls.TESLA_USERNAME:
            logger.error("TESLA_USERNAME not configured")
            return False
            
        if not cls.COT_URL:
            logger.error("COT_URL not configured")
            return False
            
        return True