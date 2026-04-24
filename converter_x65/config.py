"""
Configuration constants for the X65 format.
All dimensions and parameters in one place.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class X65Config:
    """Immutable configuration for the X65 system."""

    # Screen resolution
    WIDTH: int = 384
    HEIGHT: int = 240

    # Tile size
    TILE_SIZE: int = 8
    TILE_W: int = 8  # alias for compatibility
    TILE_H: int = 8

    # Palette
    PALETTE_SIZE: int = 256
    PALETTE_GRID: int = 16  # 16x16 colors

    # Luminance weights for color matching
    LUMA_WEIGHTS: tuple = (0.299, 0.587, 0.114)

    # Color boost during conversion
    COLOR_ENHANCE: float = 1.6
    CONTRAST_ENHANCE: float = 1.2

    # Display scale in the HTML editor
    CANVAS_SCALE: int = 3

    # Tileset split
    TILESET_COUNT: int = 6

    # Binarization threshold for the hi-res mask (0-255)
    THRESHOLD: int = 128

    @property
    def TILES_X(self) -> int:
        """Number of tiles horizontally."""
        return self.WIDTH // self.TILE_SIZE

    @property
    def TILES_Y(self) -> int:
        """Number of tiles vertically."""
        return self.HEIGHT // self.TILE_SIZE

    @property
    def TOTAL_TILES(self) -> int:
        """Total number of tiles on screen."""
        return self.TILES_X * self.TILES_Y

    @property
    def TILES_PER_SET(self) -> int:
        """Number of tiles in one set."""
        return self.TOTAL_TILES // self.TILESET_COUNT

    @property
    def BYTES_PER_TILE(self) -> int:
        """Bytes per tile (8 rows × 1 byte)."""
        return self.TILE_SIZE

    @property
    def MAP_SIZE(self) -> int:
        """Size of a single map in bytes."""
        return self.TOTAL_TILES

    @property
    def SPLIT_MAP_SIZE(self) -> int:
        """Size of combined maps in bytes."""
        return self.MAP_SIZE * 2

    @property
    def LINEAR_BITMAP_SIZE(self) -> int:
        """Size of the linear bitmap in bytes."""
        return (self.WIDTH * self.HEIGHT) // 8


# Global configuration instance
CONFIG = X65Config()