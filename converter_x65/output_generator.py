"""
Generation of all output files: binaries, PNGs, JSON, HTML.
"""

import json
import os
from PIL import Image

from .config import CONFIG
from .image_processing import X65Converter


class OutputGenerator:
    """Generates and saves all output files for the X65 project."""

    # Output file names
    FILES = {
        'maps_split': 'x65_maps_split.bin',
        'bg_map': 'x65_background.map',
        'fg_map': 'x65_foreground.map',
        'hires_png': 'x65_hires_ultra.png',
        'sim_png': 'x65_simulation_ultra.png',
        'palette_json': 'x65_palette.json',
        'viewer_html': 'x65_viewer.html',
        'linear_bitmap': 'x65_hires_linear.bin',
    }

    def __init__(self, converter: X65Converter):
        self.converter = converter

    def save_all(self, serve: bool = False) -> list[str]:
        """
        Save all output files.

        Args:
            serve: If True, also generate files needed by the server

        Returns:
            list[str]: List of generated files
        """
        generated = []

        # 1. Colour maps
        bg, fg, combined = self.converter.get_map_bytes()

        with open(self.FILES['maps_split'], 'wb') as f:
            f.write(combined)
        generated.append(self.FILES['maps_split'])

        with open(self.FILES['bg_map'], 'wb') as f:
            f.write(bg)
        generated.append(self.FILES['bg_map'])

        with open(self.FILES['fg_map'], 'wb') as f:
            f.write(fg)
        generated.append(self.FILES['fg_map'])

        # 2. Tiles / tilesets
        tilesets = self.converter.get_tilesets()
        for i, tileset in enumerate(tilesets):
            filename = f'x65_tileset_{i}.bin'
            with open(filename, 'wb') as f:
                for tile in tileset:
                    f.write(tile)
            generated.append(filename)
            print(f"Saved set {i}: {len(tileset)} chars -> {filename}")

        # 3. Linear bitmap
        linear = self.converter.generate_linear_bitmap()
        with open(self.FILES['linear_bitmap'], 'wb') as f:
            f.write(linear)
        generated.append(self.FILES['linear_bitmap'])
        print(f"Saved linear bitmap: {len(linear)} bytes -> {self.FILES['linear_bitmap']}")

        # 4. PNG images
        self.converter.hires_mask.save(self.FILES['hires_png'])
        generated.append(self.FILES['hires_png'])

        # Simulation is generated in analyze_blocks, we save it
        if self.converter._last_simulation:
            self.converter._last_simulation.save(self.FILES['sim_png'])
            generated.append(self.FILES['sim_png'])

        # 5. Palette JSON
        with open(self.FILES['palette_json'], 'w') as f:
            json.dump(self.converter.palette.to_json(), f)
        generated.append(self.FILES['palette_json'])

        # 6. HTML viewer
        from .html_template import generate_viewer_html
        html = generate_viewer_html()
        with open(self.FILES['viewer_html'], 'w', encoding='utf-8') as f:
            f.write(html)
        generated.append(self.FILES['viewer_html'])

        return generated

    def print_summary(self, generated: list[str]) -> None:
        """Print a summary of generated files."""
        print("\nDone! Generated:")
        for name in sorted(set(generated)):
            size = os.path.getsize(name) if os.path.exists(name) else 0
            print(f"- {name} ({size} bytes)")

    @classmethod
    def verify_consistency(cls) -> bool:
        """
        Verify the consistency of output file sizes.

        Returns:
            bool: True if everything matches
        """
        ok = True

        # Check maps
        for name, expected in [
            (cls.FILES['bg_map'], CONFIG.MAP_SIZE),
            (cls.FILES['fg_map'], CONFIG.MAP_SIZE),
            (cls.FILES['maps_split'], CONFIG.SPLIT_MAP_SIZE),
            (cls.FILES['linear_bitmap'], CONFIG.LINEAR_BITMAP_SIZE),
        ]:
            if not os.path.exists(name):
                print(f"[WARN] Missing file: {name}")
                ok = False
                continue

            actual = os.path.getsize(name)
            if actual != expected:
                print(f"[ERROR] {name}: expected {expected}, got {actual}")
                ok = False

        return ok