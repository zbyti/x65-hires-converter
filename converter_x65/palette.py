"""
Palette handling – loading, matching, conversion.
"""

import json
import os
import numpy as np
from PIL import Image

from .config import CONFIG


class PaletteManager:
    """Manages the 256‑colour palette for the X65 format (always 32×8)."""

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
        """Load palette from a JSON file – must be exactly 32 rows × 8 colours."""
        with open(self.path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Accept a dict with a "palette" key
        if isinstance(data, dict):
            if 'palette' in data:
                data = data['palette']
            else:
                raise ValueError("JSON object does not contain a 'palette' key or a direct colour list.")

        if not isinstance(data, list):
            raise ValueError("JSON file does not contain a colour list.")

        # Must be exactly 32 rows × 8 columns
        if len(data) != 32 or not all(isinstance(row, list) and len(row) == 8 for row in data):
            raise ValueError(
                "Invalid palette JSON. Expected 32 rows × 8 columns (list of 32 lists, each with 8 colours)."
            )

        colors = [tuple(color) for row in data for color in row]
        if len(colors) != CONFIG.PALETTE_SIZE:
            raise ValueError(f"Palette must contain exactly {CONFIG.PALETTE_SIZE} colours, got {len(colors)}.")

        self.colors = colors
        self._np_array = np.array(self.colors, dtype=np.float32)
        self._weights = np.array(CONFIG.LUMA_WEIGHTS, dtype=np.float32)

    def _load_from_image(self) -> None:
        """Load palette from a PNG image – must be exactly 32 pixels wide and 8 pixels tall."""
        pal_img = Image.open(self.path).convert('RGB')
        w, h = pal_img.size

        if w != 32 or h != 8:
            raise ValueError(
                f"Palette image must be exactly 32×8 pixels (32 columns, 8 rows). "
                f"Received {w}×{h}."
            )

        # Read pixels in row-major order (left-to-right, top-to-bottom)
        colors = [pal_img.getpixel((x, y)) for y in range(8) for x in range(32)]

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
        """Export palette as a JSON‑ready list (flat list of 256 colours)."""
        return [list(c) for c in self.colors]

    def to_numpy(self) -> np.ndarray:
        """Return a copy of the palette as a NumPy array."""
        return self._np_array.copy()