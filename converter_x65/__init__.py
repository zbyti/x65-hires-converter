"""
Image converter for the X65 format (384x240, 8x8 blocks, 256 colours).
"""

__version__ = "2.0.0"
__author__ = "Refactored"

from .config import CONFIG, X65Config
from .palette import PaletteManager
from .image_processing import X65Converter
from .output_generator import OutputGenerator
from .server import start_server, X65RequestHandler, regenerate_simulation
from .tile_encoder import TileEncoder, MaskAccessor, ArrayAccessor

__all__ = [
    'CONFIG',
    'X65Config',
    'PaletteManager',
    'X65Converter',
    'OutputGenerator',
    'start_server',
    'X65RequestHandler',
    'regenerate_simulation',
    'TileEncoder',
    'MaskAccessor',
    'ArrayAccessor',
]