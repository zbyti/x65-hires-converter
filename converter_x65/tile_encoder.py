"""
Encoding/decoding of 8x8 tiles — central place for bit‑level logic.
Eliminates duplication among tileset generation, linear bitmap, and simulation.
"""

from typing import Protocol, Optional
from PIL import Image
import numpy as np

from .config import CONFIG


class PixelAccessor(Protocol):
    """Protocol for an object that provides pixels via a call."""
    def __call__(self, x: int, y: int) -> int: ...


class TileEncoder:
    """
    Encoder for 8x8 tiles.
    Each tile = 8 bytes, each byte = 8 pixels in a row (MSB on the left).
    """

    BYTES_PER_TILE = CONFIG.TILE_SIZE  # 8

    @classmethod
    def encode_tile(cls, pixel_accessor: PixelAccessor, tile_x: int, tile_y: int,
                    tile_w: Optional[int] = None, tile_h: Optional[int] = None) -> bytes:
        """
        Encode a tile into 8 bytes.

        Args:
            pixel_accessor: function(x, y) -> int (0 or 1)
            tile_x: tile coordinate in tile units
            tile_y: tile coordinate in tile units
            tile_w: tile width (default from CONFIG)
            tile_h: tile height (default from CONFIG)

        Returns:
            bytes: 8 bytes representing the tile
        """
        tw = tile_w or CONFIG.TILE_W
        th = tile_h or CONFIG.TILE_H
        base_x = tile_x * tw
        base_y = tile_y * th

        result = bytearray(th)
        for py in range(th):
            byte_val = 0
            for px in range(tw):
                bit = pixel_accessor(base_x + px, base_y + py)
                # MSB on the left: bit 7 corresponds to px=0
                byte_val |= ((1 if bit else 0) << (7 - px))
            result[py] = byte_val

        return bytes(result)

    @classmethod
    def encode_row(cls, pixel_accessor: PixelAccessor, row_y: int,
                   width: Optional[int] = None) -> bytes:
        """
        Encode a full pixel row into byte form (for linear bitmap).

        Args:
            pixel_accessor: function(x, y) -> int (0 or 1)
            row_y: row number
            width: row width in pixels (default from CONFIG)

        Returns:
            bytes: width // 8 bytes
        """
        width = width or CONFIG.WIDTH
        row_bytes = bytearray(width // 8)

        for x in range(0, width, 8):
            byte_val = 0
            for px in range(8):
                bit = pixel_accessor(x + px, row_y)
                byte_val |= ((1 if bit else 0) << (7 - px))
            row_bytes[x // 8] = byte_val

        return bytes(row_bytes)

    @classmethod
    def decode_tile_byte(cls, byte_val: int, pixel_x: int) -> int:
        """
        Decode a single pixel from a tile byte.

        Args:
            byte_val: byte value
            pixel_x: pixel position in the row (0–7)

        Returns:
            int: 0 or 1
        """
        return (byte_val >> (7 - pixel_x)) & 1

    @classmethod
    def get_bit_from_bytes(cls, tile_data: bytes, pixel_x: int, pixel_y: int) -> int:
        """
        Retrieve a bit from decoded tile data.

        Args:
            tile_data: 8 bytes of the tile
            pixel_x: X position within the tile (0–7)
            pixel_y: Y position within the tile (0–7)

        Returns:
            int: 0 or 1
        """
        return cls.decode_tile_byte(tile_data[pixel_y], pixel_x)


class MaskAccessor:
    """
    Wrapper for a 1‑bit PIL.Image mask.
    Unifies the interface for TileEncoder.
    """

    def __init__(self, mask_image: Image.Image):
        """
        Args:
            mask_image: PIL.Image in mode '1' (1‑bit)
        """
        self.mask = mask_image
        self._cache: dict[tuple[int, int], int] = {}

    def __call__(self, x: int, y: int) -> int:
        """Return 1 if the pixel is set, 0 otherwise."""
        key = (x, y)
        if key not in self._cache:
            # In mode '1', getpixel returns 0 or 255
            self._cache[key] = 1 if self.mask.getpixel((x, y)) > 0 else 0
        return self._cache[key]

    def clear_cache(self) -> None:
        """Clear the cache if the image changes."""
        self._cache.clear()


class ArrayAccessor:
    """
    Wrapper for a NumPy array mask (used in regenerate_simulation).
    """

    def __init__(self, mask_array: np.ndarray):
        """
        Args:
            mask_array: NumPy array of shape (HEIGHT, WIDTH) with 0/1 values
        """
        self.array = mask_array
        self.height, self.width = mask_array.shape

    def __call__(self, x: int, y: int) -> int:
        """Return pixel value with boundary protection."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return int(self.array[y, x])
        return 0