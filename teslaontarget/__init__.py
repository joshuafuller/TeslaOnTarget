"""TeslaOnTarget - Bridge Tesla vehicles with TAK servers."""

__version__ = "1.2.0"  # x-release-please-version
__author__ = "TeslaOnTarget Contributors"

from .tesla_api import TeslaCoT
from .tak_client import TAKClient
from .cot import generate_cot_packet, format_cot_for_tak
from .utils import calculate_distance, load_json_file, save_json_file
from .config_handler import AppConfig, load_config

__all__ = [
    'TeslaCoT',
    'TAKClient',
    'AppConfig',
    'load_config',
    'generate_cot_packet',
    'format_cot_for_tak',
    'calculate_distance',
    'load_json_file',
    'save_json_file',
]