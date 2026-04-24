"""
HTTP server with POST /save handling for the maps.
Includes simulation image regeneration after save.
Uses transactional file writing.
"""

import json
import os
import socket
import tempfile
import traceback
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn

from PIL import Image
import numpy as np

from .config import CONFIG, BG_MAP_FILENAME, FG_MAP_FILENAME, MAPS_SPLIT_FILENAME, \
    PALETTE_JSON_FILENAME, HIRES_PNG_FILENAME, SIM_PNG_FILENAME, VIEWER_HTML_FILENAME
from .output_generator import OutputGenerator
from .tile_encoder import ArrayAccessor


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def find_free_port(start_port: int = None) -> int:
    if start_port is None:
        start_port = CONFIG.SERVER_PORT
    for port in range(start_port, start_port + 1000):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('', port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free port found starting from {start_port}")


def _regenerate_simulation_vector(bg_bytes: bytes, fg_bytes: bytes, output_path: str | None = None) -> None:
    with open(PALETTE_JSON_FILENAME, "r") as f:
        palette_raw = json.load(f)
    palette = np.array(palette_raw, dtype=np.uint8)

    hires_img = Image.open(HIRES_PNG_FILENAME).convert('1')
    hires_array = np.array(hires_img, dtype=np.uint8)
    hires_bool = (hires_array > 0).astype(np.uint8)

    bg = np.frombuffer(bg_bytes, dtype=np.uint8)
    fg = np.frombuffer(fg_bytes, dtype=np.uint8)

    ty = np.arange(CONFIG.HEIGHT) // CONFIG.TILE_SIZE
    tx = np.arange(CONFIG.WIDTH) // CONFIG.TILE_SIZE
    tile_idx = ty[:, None] * CONFIG.TILES_X + tx[None, :]

    bg_img = palette[bg[tile_idx]]
    fg_img = palette[fg[tile_idx]]
    sim_array = np.where(hires_bool[:, :, None], fg_img, bg_img)

    simulation = Image.fromarray(sim_array.astype(np.uint8), mode='RGB')
    simulation.save(output_path or SIM_PNG_FILENAME)
    print(f"[SERVER] Generated new {(output_path or SIM_PNG_FILENAME)} (vectorised)")


def regenerate_simulation(bg_bytes: bytes, fg_bytes: bytes) -> None:
    _regenerate_simulation_vector(bg_bytes, fg_bytes)


class X65RequestHandler(SimpleHTTPRequestHandler):
    NO_CACHE_EXTENSIONS = ('.map', '.json', '.bin', '.png')

    def _send_cors_headers(self) -> None:
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self._send_cors_headers()
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_POST(self) -> None:
        if self.path != '/save':
            self.send_error(404, "Not Found")
            return

        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_error(400, "No data")
                return
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            bg = data.get('bg')
            fg = data.get('fg')
            if bg is None or fg is None:
                self.send_error(400, "Missing 'bg' or 'fg'")
                return
            expected = CONFIG.MAP_SIZE
            if len(bg) != expected or len(fg) != expected:
                self.send_error(400, f"Expected {expected} bytes, bg={len(bg)}, fg={len(fg)}")
                return

            bg_bytes = bytes(bg)
            fg_bytes = bytes(fg)

            with tempfile.NamedTemporaryFile(delete=False, suffix='.map') as tmp_bg, \
                 tempfile.NamedTemporaryFile(delete=False, suffix='.map') as tmp_fg, \
                 tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tmp_split, \
                 tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_sim:

                tmp_bg.write(bg_bytes)
                tmp_fg.write(fg_bytes)
                tmp_split.write(bg_bytes + fg_bytes)
                tmp_bg.flush()
                tmp_fg.flush()
                tmp_split.flush()
                tmp_sim_path = tmp_sim.name

            try:
                _regenerate_simulation_vector(bg_bytes, fg_bytes, output_path=tmp_sim_path)
            except Exception as e:
                for f in [tmp_bg.name, tmp_fg.name, tmp_split.name, tmp_sim_path]:
                    try: os.unlink(f)
                    except OSError: pass
                raise RuntimeError(f"Simulation generation error: {e}") from e

            try:
                os.replace(tmp_bg.name, BG_MAP_FILENAME)
                os.replace(tmp_fg.name, FG_MAP_FILENAME)
                os.replace(tmp_split.name, MAPS_SPLIT_FILENAME)
                os.replace(tmp_sim_path, SIM_PNG_FILENAME)
                print("[SERVER] Modified maps saved and simulation refreshed (transactional).")
            except Exception as e:
                for f in [tmp_bg.name, tmp_fg.name, tmp_split.name, tmp_sim_path]:
                    try: os.unlink(f)
                    except OSError: pass
                raise RuntimeError(f"File replacement error: {e}") from e

            response_body = b'OK'
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Content-Length', str(len(response_body)))
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(response_body)

        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
        except Exception as e:
            print(f"[SERVER] Save error: {e}")
            traceback.print_exc()
            self.send_error(500, f"Save error: {str(e)}")

    def end_headers(self) -> None:
        path_lower = self.path.lower()
        if any(path_lower.endswith(ext) for ext in self.NO_CACHE_EXTENSIONS):
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
        super().end_headers()

    def log_message(self, format: str, *args) -> None:
        if 'GET' in format and '/x65_' in format:
            return
        super().log_message(format, *args)


def start_server(port: int = None) -> None:
    if port is None:
        try:
            port = find_free_port(CONFIG.SERVER_PORT)
            print(f"Found free port: {port}")
        except RuntimeError as e:
            print(f"Error: {e}")
            return

    server_address = ('', port)
    ThreadingHTTPServer.allow_reuse_address = True
    try:
        httpd = ThreadingHTTPServer(server_address, X65RequestHandler)
    except OSError as e:
        print(f"Error starting server on port {port}: {e}")
        try:
            port = find_free_port(port + 1)
            server_address = ('', port)
            httpd = ThreadingHTTPServer(server_address, X65RequestHandler)
            print(f"Using alternative port: {port}")
        except Exception as e2:
            print(f"Could not start server: {e2}")
            return

    url = f'http://localhost:{port}/{VIEWER_HTML_FILENAME}'
    print(f"HTTP server running on port {port}")
    print(f"Open browser at {url}")

    required = [
        VIEWER_HTML_FILENAME,
        BG_MAP_FILENAME,
        FG_MAP_FILENAME,
        PALETTE_JSON_FILENAME,
        HIRES_PNG_FILENAME,
        SIM_PNG_FILENAME
    ]
    missing = [f for f in required if not os.path.exists(f)]
    if missing:
        print(f"[WARNING] Missing files: {', '.join(missing)}")

    webbrowser.open(url)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n← Ctrl+C – shutting down server...")
    finally:
        httpd.shutdown()
        httpd.server_close()
        print("Server stopped.")