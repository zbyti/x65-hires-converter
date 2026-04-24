"""
Core image‑to‑X65 conversion logic.
"""

import numpy as np
from PIL import Image, ImageEnhance

from .config import CONFIG
from .palette import PaletteManager
from .tile_encoder import TileEncoder, MaskAccessor


class X65Converter:
    """
    Image converter for the X65 format.
    Processes an input image into all required output files.
    """

    def __init__(self, palette_path: str):
        self.palette = PaletteManager(palette_path)
        self.hires_mask: Image.Image | None = None  # 1‑bit mask
        self.attr_map: list[tuple[int, int]] = []    # (bg_idx, fg_idx) per tile
        self.tiles_data: list[bytes] = []            # encoded tiles
        self._last_simulation: Image.Image | None = None  # for OutputGenerator

    def prepare_image(self, input_path: str) -> Image.Image:
        """
        Load and prepare the input image.

        Returns:
            Image.Image: Preprocessed RGB image 384x240
        """
        img = Image.open(input_path).convert('RGB')
        img = img.resize((CONFIG.WIDTH, CONFIG.HEIGHT), Image.Resampling.LANCZOS)

        # Colour enhancement
        enhancer_col = ImageEnhance.Color(img)
        img = enhancer_col.enhance(CONFIG.COLOR_ENHANCE)
        enhancer_con = ImageEnhance.Contrast(img)
        img = enhancer_con.enhance(CONFIG.CONTRAST_ENHANCE)

        return img

    def analyze_blocks(self, img: Image.Image) -> Image.Image:
        """
        Analyze 8x8 blocks, create a hires mask and colour attribute map.

        Args:
            img: RGB image 384x240

        Returns:
            Image.Image: Simulation RGB image
        """
        # Create monochrome hires mask
        self.hires_mask = img.convert('L').convert('1')
        pixels_rgb = np.array(img)

        # Prepare simulation image
        simulation = Image.new('RGB', (CONFIG.WIDTH, CONFIG.HEIGHT))

        self.attr_map = []
        block = CONFIG.TILE_SIZE

        for y in range(0, CONFIG.HEIGHT, block):
            for x in range(0, CONFIG.WIDTH, block):
                block_pixels = pixels_rgb[y:y+block, x:x+block].reshape(-1, 3)

                # Compute luminance for each pixel in the block
                brightness = np.dot(block_pixels, list(CONFIG.LUMA_WEIGHTS))

                # Darkest = background, brightest = foreground
                min_idx = int(np.argmin(brightness))
                max_idx = int(np.argmax(brightness))

                bg_idx = self.palette.closest_index(tuple(block_pixels[min_idx]))
                fg_idx = self.palette.closest_index(tuple(block_pixels[max_idx]))

                self.attr_map.append((bg_idx, fg_idx))
                color0 = self.palette.get_rgb(bg_idx)
                color1 = self.palette.get_rgb(fg_idx)

                # Fill simulation image
                for by in range(block):
                    for bx in range(block):
                        bit = self.hires_mask.getpixel((x + bx, y + by))
                        simulation.putpixel((x + bx, y + by),
                                          color1 if bit > 0 else color0)

        self._last_simulation = simulation
        return simulation

    def encode_tiles(self) -> list[bytes]:
        """
        Encodes all 8x8 tiles from the hires mask.

        Returns:
            list[bytes]: List of 1440 encoded tiles
        """
        if self.hires_mask is None:
            raise RuntimeError("Run analyze_blocks() first")

        accessor = MaskAccessor(self.hires_mask)
        tiles = []

        for ty in range(CONFIG.TILES_Y):
            for tx in range(CONFIG.TILES_X):
                tile = TileEncoder.encode_tile(accessor, tx, ty)
                tiles.append(tile)

        self.tiles_data = tiles
        return tiles

    def generate_linear_bitmap(self) -> bytes:
        """
        Generates a linear 384x240 bitmap (1 bit per pixel).

        Returns:
            bytes: Linear bitmap
        """
        if self.hires_mask is None:
            raise RuntimeError("Run analyze_blocks() first")

        accessor = MaskAccessor(self.hires_mask)
        rows = []

        for y in range(CONFIG.HEIGHT):
            row = TileEncoder.encode_row(accessor, y)
            rows.append(row)

        return b''.join(rows)

    def get_tilesets(self) -> list[list[bytes]]:
        """
        Splits tiles into 6 sets of 240.

        Returns:
            list[list[bytes]]: 6 tilesets
        """
        if not self.tiles_data:
            raise RuntimeError("Run encode_tiles() first")

        sets = []
        tps = CONFIG.TILES_PER_SET

        for i in range(CONFIG.TILESET_COUNT):
            start = i * tps
            end = start + tps
            sets.append(self.tiles_data[start:end])

        return sets

    def get_map_bytes(self) -> tuple[bytes, bytes, bytes]:
        """
        Returns colour maps as bytes.

        Returns:
            tuple: (bg_map, fg_map, combined_map)
        """
        bg = bytes([attr[0] for attr in self.attr_map])
        fg = bytes([attr[1] for attr in self.attr_map])
        combined = bg + fg
        return bg, fg, combined