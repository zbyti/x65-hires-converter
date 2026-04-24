"""
Palette handling – loading, matching, conversion.
"""

import json
import os
import numpy as np
from PIL import Image

from .config import CONFIG, DEFAULT_PALETTE_JSON_FILES, DEFAULT_PALETTE_PNG


class PaletteManager:
    """Manages the 256‑colour palette for the X65 format (always 32×8)."""

    def __init__(self, source_path: str = None):
        """
        Args:
            source_path: Path to a JSON file or a PNG image.
                         If None, auto‑detects using predefined paths.
        """
        if source_path is None:
            source_path = self._auto_detect()

        self.path = source_path
        self.colors: list[tuple[int, int, int]] = []
        self._np_array: np.ndarray | None = None
        self._weights: np.ndarray | None = None
        self._load()

    @staticmethod
    def _auto_detect() -> str:
        """Try to locate a palette file in the current directory."""
        for json_name in DEFAULT_PALETTE_JSON_FILES:
            if os.path.exists(json_name):
                return json_name
        return DEFAULT_PALETTE_PNG

    def _load(self) -> None:
        """Load palette from JSON or PNG with error handling."""
        ext = os.path.splitext(self.path)[1].lower()
        try:
            if ext == '.json':
                self._load_from_json()
            else:
                self._load_from_image()
        except FileNotFoundError:
            raise ValueError(f"Palette file not found: {self.path}") from None
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Error loading palette from {self.path}: {e}") from e

    def _load_from_json(self) -> None:
        """Load palette from a JSON file – must be exactly 32 rows × 8 colours."""
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            raise
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in palette file: {e}") from e

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
        try:
            pal_img = Image.open(self.path).convert('RGB')
        except FileNotFoundError:
            raise ValueError(f"Palette image not found: {self.path}") from None
        except Exception as e:
            raise ValueError(f"Cannot open palette image {self.path}: {e}") from e

        w, h = pal_img.size
        if w != 32 or h != 8:
            raise ValueError(
                f"Palette image must be exactly 32×8 pixels (32 columns, 8 rows). "
                f"Received {w}×{h}."
            )

        colors = [pal_img.getpixel((x, y)) for y in range(8) for x in range(32)]

        self.colors = colors[:CONFIG.PALETTE_SIZE]
        while len(self.colors) < CONFIG.PALETTE_SIZE:
            self.colors.append((0, 0, 0))

        self._np_array = np.array(self.colors, dtype=np.float32)
        self._weights = np.array(CONFIG.LUMA_WEIGHTS, dtype=np.float32)

    def closest_index(self, pixel: tuple[int, ...]) -> int:
        if self._np_array is None:
            raise RuntimeError("Palette not initialised")
        pixel_arr = np.array(pixel[:3], dtype=np.float32)
        diff = self._np_array - pixel_arr
        distances = np.sum(self._weights * (diff ** 2), axis=1)
        return int(np.argmin(distances))

    def get_rgb(self, index: int) -> tuple[int, int, int]:
        idx = max(0, min(CONFIG.PALETTE_SIZE - 1, index))
        return self.colors[idx]

    def to_json(self) -> list[list[int]]:
        return [list(c) for c in self.colors]

    def to_numpy(self) -> np.ndarray:
        return self._np_array.copy()