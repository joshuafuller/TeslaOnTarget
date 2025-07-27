"""TeslaOnTarget - Bridge Tesla vehicles with TAK servers."""

__version__ = "1.0.0"
__author__ = "TeslaOnTarget Contributors"

from .tesla_api import TeslaCoT
from .tak_client import TAKClient
from .cot import generate_cot_packet, format_cot_for_tak
from .utils import calculate_distance, load_json_file, save_json_file
from .config_handler import Config

__all__ = [
    'TeslaCoT',
    'TAKClient', 
    'Config',
    'generate_cot_packet',
    'format_cot_for_tak',
    'calculate_distance',
    'load_json_file',
    'save_json_file'
]