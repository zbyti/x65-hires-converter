#!/usr/bin/env python3
"""
Build script to create a zipapp with the proper package structure.
"""

import os
import shutil
import subprocess
import sys

BUILD_DIR = "build_zipapp"
OUTPUT = "converter_x65.pyz"

def main():
    # Clean previous build
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    if os.path.exists(OUTPUT):
        os.remove(OUTPUT)

    # Create structure: build_zipapp/converter_x65/...
    os.makedirs(f"{BUILD_DIR}/converter_x65")

    for item in os.listdir("converter_x65"):
        if item.startswith("__pycache__"):
            continue
        src = os.path.join("converter_x65", item)
        dst = os.path.join(f"{BUILD_DIR}/converter_x65", item)
        if os.path.isdir(src):
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(src, dst)

    # Create root __main__.py — this is the zipapp entry point
    with open(f"{BUILD_DIR}/__main__.py", "w") as f:
        f.write("""#!/usr/bin/env python3
from converter_x65.__main__ import main
import sys
sys.exit(main())
""")

    # Package
    subprocess.run([
        sys.executable, "-m", "zipapp", BUILD_DIR,
        "-p", "/usr/bin/env python3",
        "-o", OUTPUT
    ], check=True)

    # Clean up
    shutil.rmtree(BUILD_DIR)

    size = os.path.getsize(OUTPUT)
    print(f"\n✓ Done: {OUTPUT} ({size:,} bytes)")
    print("\n" + "=" * 50)
    print("Available commands:")
    print("=" * 50)
    print(f"  python3 {OUTPUT} image.png")
    print("      # Convert an image to the X65 format (all output files)")
    print()
    print(f"  python3 {OUTPUT} image.png --serve")
    print("      # Convert + launch the editor server")
    print()
    print(f"  python3 {OUTPUT} --edit")
    print("      # Only the editor server (requires a previous conversion)")
    print()
    print(f"  python3 {OUTPUT} --verify")
    print("      # Check the consistency of generated files")
    print()
    print("Conversion method:")
    print(f"  python3 {OUTPUT} image.png --method original")
    print("      # Default: extrema per tile (darkest/brightest pixel)")
    print("      #          global threshold mask (128)")
    print()
    print(f"  python3 {OUTPUT} image.png --method adaptive")
    print("      # New: local threshold per tile (average luminance)")
    print("      #       average colour centroid per group")
    print("      #       Redmean perceptual colour distance")
    print()
    print("Palette options:")
    print(f"  python3 {OUTPUT} image.png --palette path/to/palette.png")
    print("      # Use a custom palette file (16×16 PNG)")
    print(f"  python3 {OUTPUT} image.png --palette palette.json")
    print("      # Use a JSON palette (flat list or 32×8)")
    print()
    print("Automatic JSON palette detection:")
    print("  The program automatically uses (in order of priority):")
    print("    1. X65-palette_32x8_rgb.json")
    print("    2. x65_palette.json")
    print("    3. X65_RGB_palette.png")
    print()
    print("Helpful:")
    print(f"  python3 {OUTPUT} --help")
    print("      # Show full help with all arguments")
    print("=" * 50)

if __name__ == "__main__":
    main()