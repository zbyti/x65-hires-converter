"""
Generation of all output files: binaries, PNGs, JSON, HTML.
"""

import json
import os
from PIL import Image

from .config import CONFIG, BG_MAP_FILENAME, FG_MAP_FILENAME, MAPS_SPLIT_FILENAME, \
    HIRES_PNG_FILENAME, SIM_PNG_FILENAME, PALETTE_JSON_FILENAME, VIEWER_HTML_FILENAME, \
    LINEAR_BITMAP_FILENAME, TILESET_PREFIX
from .image_processing import X65Converter


class OutputGenerator:
    """Generates and saves all output files for the X65 project."""

    # Mapowanie – używa stałych z config.py
    FILES = {
        'maps_split': MAPS_SPLIT_FILENAME,
        'bg_map': BG_MAP_FILENAME,
        'fg_map': FG_MAP_FILENAME,
        'hires_png': HIRES_PNG_FILENAME,
        'sim_png': SIM_PNG_FILENAME,
        'palette_json': PALETTE_JSON_FILENAME,
        'viewer_html': VIEWER_HTML_FILENAME,
        'linear_bitmap': LINEAR_BITMAP_FILENAME,
    }

    def __init__(self, converter: X65Converter):
        self.converter = converter

    def save_all(self, serve: bool = False) -> list[str]:
        generated = []

        bg, fg, combined = self.converter.get_map_bytes()

        with open(MAPS_SPLIT_FILENAME, 'wb') as f:
            f.write(combined)
        generated.append(MAPS_SPLIT_FILENAME)

        with open(BG_MAP_FILENAME, 'wb') as f:
            f.write(bg)
        generated.append(BG_MAP_FILENAME)

        with open(FG_MAP_FILENAME, 'wb') as f:
            f.write(fg)
        generated.append(FG_MAP_FILENAME)

        tilesets = self.converter.get_tilesets()
        for i, tileset in enumerate(tilesets):
            filename = f'{TILESET_PREFIX}{i}.bin'
            with open(filename, 'wb') as f:
                for tile in tileset:
                    f.write(tile)
            generated.append(filename)
            print(f"Saved set {i}: {len(tileset)} chars -> {filename}")

        linear = self.converter.generate_linear_bitmap()
        with open(LINEAR_BITMAP_FILENAME, 'wb') as f:
            f.write(linear)
        generated.append(LINEAR_BITMAP_FILENAME)
        print(f"Saved linear bitmap: {len(linear)} bytes -> {LINEAR_BITMAP_FILENAME}")

        if self.converter.hires_mask:
            self.converter.hires_mask.save(HIRES_PNG_FILENAME)
            generated.append(HIRES_PNG_FILENAME)

        if self.converter._last_simulation:
            self.converter._last_simulation.save(SIM_PNG_FILENAME)
            generated.append(SIM_PNG_FILENAME)

        with open(PALETTE_JSON_FILENAME, 'w') as f:
            json.dump(self.converter.palette.to_json(), f)
        generated.append(PALETTE_JSON_FILENAME)

        from .html_template import generate_viewer_html
        html = generate_viewer_html()
        with open(VIEWER_HTML_FILENAME, 'w', encoding='utf-8') as f:
            f.write(html)
        generated.append(VIEWER_HTML_FILENAME)

        return generated

    def print_summary(self, generated: list[str]) -> None:
        print("\nDone! Generated:")
        for name in sorted(set(generated)):
            size = os.path.getsize(name) if os.path.exists(name) else 0
            print(f"- {name} ({size} bytes)")

    @classmethod
    def verify_consistency(cls) -> bool:
        ok = True
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