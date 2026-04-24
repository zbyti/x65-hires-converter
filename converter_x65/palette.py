"""
Palette handling — loading, matching, conversion.
"""

import json
import os
import numpy as np
from PIL import Image

from .config import CONFIG


class PaletteManager:
    """Manages the 256‑colour palette for the X65 format."""

    def __init__(self, source_path: str = None):
        """
        Args:
            source_path: Path to a JSON file or a PNG image.
                         If None, tries to auto‑detect a JSON file.
        """
        if source_path is None:
            # Auto‑detection: look for JSON first, then PNG
            if os.path.exists("X65-palette_32x8_rgb.json"):
                source_path = "X65-palette_32x8_rgb.json"
            elif os.path.exists("x65_palette.json"):
                source_path = "x65_palette.json"
            else:
                source_path = "X65_RGB_palette.png"

        self.path = source_path
        self.colors: list[tuple[int, int, int]] = []
        self._np_array: np.ndarray | None = None
        self._weights: np.ndarray | None = None
        self._load()

    def _load(self) -> None:
        """Load palette from JSON or PNG."""
        ext = os.path.splitext(self.path)[1].lower()
        if ext == '.json':
            self._load_from_json()
        else:
            self._load_from_image()

    def _load_from_json(self) -> None:
        """Load palette from a JSON file."""
        with open(self.path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # If data is a dict, try to extract the list from the "palette" key
        if isinstance(data, dict):
            if 'palette' in data:
                data = data['palette']
            else:
                raise ValueError("JSON object does not contain a 'palette' key or a direct colour list.")

        if not isinstance(data, list):
            raise ValueError("JSON file does not contain a colour list.")

        # Check format: flat list of 256 RGB triplets, or 32×8
        if len(data) == CONFIG.PALETTE_SIZE and all(isinstance(c, (list, tuple)) and len(c) == 3 for c in data):
            # Flat list
            colors = [tuple(c) for c in data]
        elif len(data) == 32 and all(isinstance(row, list) and len(row) == 8 for row in data):
            # 32 rows × 8 colours
            colors = [tuple(color) for row in data for color in row]
        else:
            raise ValueError(
                f"Invalid JSON palette format. Expected a flat list of {CONFIG.PALETTE_SIZE} "
                f"colours or 32×8. Received: {len(data)} elements."
            )

        self.colors = colors[:CONFIG.PALETTE_SIZE]
        while len(self.colors) < CONFIG.PALETTE_SIZE:
            self.colors.append((0, 0, 0))

        self._np_array = np.array(self.colors, dtype=np.float32)
        self._weights = np.array(CONFIG.LUMA_WEIGHTS, dtype=np.float32)

    def _load_from_image(self) -> None:
        """Load palette from an image (default 16×16)."""
        pal_img = Image.open(self.path).convert('RGB')
        w, h = pal_img.size
        grid = CONFIG.PALETTE_GRID
        cell_w = w // grid
        cell_h = h // grid
        offset_x = cell_w // 2
        offset_y = cell_h // 2

        colors = []
        for row in range(grid):
            for col in range(grid):
                x = col * cell_w + offset_x
                y = row * cell_h + offset_y
                x = min(x, w - 1)
                y = min(y, h - 1)
                colors.append(pal_img.getpixel((x, y)))

        self.colors = colors[:CONFIG.PALETTE_SIZE]
        while len(self.colors) < CONFIG.PALETTE_SIZE:
            self.colors.append((0, 0, 0))

        self._np_array = np.array(self.colors, dtype=np.float32)
        self._weights = np.array(CONFIG.LUMA_WEIGHTS, dtype=np.float32)

    def closest_index(self, pixel: tuple[int, ...]) -> int:
        """Find the palette index closest to the given pixel."""
        if self._np_array is None:
            raise RuntimeError("Palette not initialised")
        pixel_arr = np.array(pixel[:3], dtype=np.float32)
        diff = self._np_array - pixel_arr
        distances = np.sum(self._weights * (diff ** 2), axis=1)
        return int(np.argmin(distances))

    def get_rgb(self, index: int) -> tuple[int, int, int]:
        """Return the RGB triplet for a given palette index."""
        idx = max(0, min(CONFIG.PALETTE_SIZE - 1, index))
        return self.colors[idx]

    def to_json(self) -> list[list[int]]:
        """Export palette as a JSON‑ready list."""
        return [list(c) for c in self.colors]

    def to_numpy(self) -> np.ndarray:
        """Return a copy of the palette as a NumPy array."""
        return self._np_array.copy()