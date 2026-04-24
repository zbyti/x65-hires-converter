#!/usr/bin/env python3
"""
Entry point — command‑line argument handling.
"""

import argparse
import os
import sys

from .config import CONFIG, SERVER_PORT
from .image_processing import X65Converter
from .output_generator import OutputGenerator
from .server import start_server


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='X65 image converter and tile editor.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m converter_x65 image.png                     # conversion
  python -m converter_x65 image.png --serve             # conversion + server
  python -m converter_x65 --edit                        # server only
        """
    )
    parser.add_argument('input_image', nargs='?', help='Input PNG file (omit for --edit)')
    parser.add_argument('--palette', default=None, help='Palette file (PNG or JSON). Default: auto‑detect.')
    parser.add_argument('--serve', action='store_true', help='After conversion, start the editor server')
    parser.add_argument('--edit', action='store_true', help='Only start the server for existing files')
    parser.add_argument('--verify', action='store_true', help='Check the consistency of generated files')
    return parser


def main() -> int:
    parser = create_parser()
    args = parser.parse_args()

    if args.edit:
        if not os.path.exists('x65_viewer.html'):
            print("Error: x65_viewer.html does not exist. Run a conversion first.")
            return 1
        start_server(port=SERVER_PORT)
        return 0

    if args.verify:
        ok = OutputGenerator.verify_consistency()
        return 0 if ok else 1

    if not args.input_image:
        parser.print_help()
        print("\nError: You must provide an input file or use --edit")
        return 1

    if not os.path.exists(args.input_image):
        print(f"Error: Input file not found: {args.input_image}")
        return 1

    print(f"Conversion: {args.input_image}")
    print(f"Palette:    {args.palette or 'auto‑detect'}")
    print(f"Resolution: {CONFIG.WIDTH}x{CONFIG.HEIGHT}")
    print(f"Tile:       {CONFIG.TILE_SIZE}x{CONFIG.TILE_SIZE}")
    print(f"Tilesets:   {CONFIG.TILESET_COUNT} x {CONFIG.TILES_PER_SET} tiles")
    print("-" * 40)

    try:
        converter = X65Converter(args.palette)
        img = converter.prepare_image(args.input_image)
        converter.analyze_blocks(img)
        converter.encode_tiles()

        generator = OutputGenerator(converter)
        generated = generator.save_all(serve=args.serve)
        generator.print_summary(generated)

        print("\nChecking consistency...")
        OutputGenerator.verify_consistency()

    except Exception as e:
        print(f"\nConversion error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    if args.serve:
        print("\n" + "=" * 40)
        start_server(port=SERVER_PORT)

    return 0


if __name__ == "__main__":
    sys.exit(main())