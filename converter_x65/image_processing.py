"""
Core image‑to‑X65 conversion logic.
"""

import numpy as np
from PIL import Image, ImageEnhance

from .config import CONFIG, ANALYSIS_ORIGINAL
from .palette import PaletteManager
from .tile_encoder import TileEncoder, MaskAccessor


class X65Converter:
    """
    Image converter for the X65 format.
    Processes an input image into all required output files.
    """

    def __init__(self, palette_path: str, method: str = ANALYSIS_ORIGINAL):
        self.palette = PaletteManager(palette_path)
        self.method = method
        self.hires_mask: Image.Image | None = None
        self.attr_map: list[tuple[int, int]] = []
        self.tiles_data: list[bytes] = []
        self._last_simulation: Image.Image | None = None

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
        if self.method == 'adaptive':
            return self._analyze_blocks_adaptive(img)
        return self._analyze_blocks_original(img)

    def _analyze_blocks_original(self, img: Image.Image) -> Image.Image:
        """Original extrema-based global threshold analysis."""
        self.hires_mask = img.convert('L').convert('1')
        pixels_rgb = np.array(img)

        simulation = Image.new('RGB', (CONFIG.WIDTH, CONFIG.HEIGHT))
        self.attr_map = []
        block = CONFIG.TILE_SIZE

        for y in range(0, CONFIG.HEIGHT, block):
            for x in range(0, CONFIG.WIDTH, block):
                block_pixels = pixels_rgb[y:y+block, x:x+block].reshape(-1, 3)

                brightness = np.dot(block_pixels, list(CONFIG.LUMA_WEIGHTS))
                min_idx = int(np.argmin(brightness))
                max_idx = int(np.argmax(brightness))

                bg_idx = self.palette.closest_index(tuple(block_pixels[min_idx]))
                fg_idx = self.palette.closest_index(tuple(block_pixels[max_idx]))

                self.attr_map.append((bg_idx, fg_idx))
                color0 = self.palette.get_rgb(bg_idx)
                color1 = self.palette.get_rgb(fg_idx)

                for by in range(block):
                    for bx in range(block):
                        bit = self.hires_mask.getpixel((x + bx, y + by))
                        simulation.putpixel((x + bx, y + by),
                                          color1 if bit > 0 else color0)

        self._last_simulation = simulation
        return simulation

    def _analyze_blocks_adaptive(self, img: Image.Image) -> Image.Image:
        """
        Improved analysis using local threshold and color centroids.
        Uses Redmean color distance for palette matching.
        """
        pixels_rgb = np.array(img).astype(np.float32)
        new_mask = Image.new('1', (CONFIG.WIDTH, CONFIG.HEIGHT))
        simulation = Image.new('RGB', (CONFIG.WIDTH, CONFIG.HEIGHT))
        self.attr_map = []
        block = CONFIG.TILE_SIZE

        for y in range(0, CONFIG.HEIGHT, block):
            for x in range(0, CONFIG.WIDTH, block):
                block_pixels = pixels_rgb[y:y+block, x:x+block]
                flat_pixels = block_pixels.reshape(-1, 3)

                # Local luminance threshold
                luma = np.dot(flat_pixels, [0.299, 0.587, 0.114])
                tile_threshold = np.mean(luma)

                binary_tile = (luma > tile_threshold).astype(np.uint8)

                high_pixels = flat_pixels[binary_tile == 1]
                low_pixels = flat_pixels[binary_tile == 0]

                if len(high_pixels) == 0:
                    high_pixels = flat_pixels
                if len(low_pixels) == 0:
                    low_pixels = flat_pixels

                avg_fg = np.mean(high_pixels, axis=0)
                avg_bg = np.mean(low_pixels, axis=0)

                # Use Redmean distance
                bg_idx = self.palette.closest_index_redmean(tuple(avg_bg.astype(int)))
                fg_idx = self.palette.closest_index_redmean(tuple(avg_fg.astype(int)))

                self.attr_map.append((bg_idx, fg_idx))
                color_bg = self.palette.get_rgb(bg_idx)
                color_fg = self.palette.get_rgb(fg_idx)

                for by in range(block):
                    for bx in range(block):
                        pixel_val = 1 if luma[by * block + bx] > tile_threshold else 0
                        new_mask.putpixel((x + bx, y + by), pixel_val)
                        simulation.putpixel((x + bx, y + by),
                                          color_fg if pixel_val else color_bg)

        self.hires_mask = new_mask
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