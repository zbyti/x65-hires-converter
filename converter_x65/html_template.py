"""
HTML template for the X65 editor – version with 8×32 palette, live preview,
smoothing toggle, edited tile highlighting, and CRT effect.
"""

from .config import CONFIG


def generate_viewer_html() -> str:
    """Generates the HTML viewer with an 8‑column palette and fixed colour handling."""

    width = CONFIG.WIDTH
    height = CONFIG.HEIGHT
    tile_w = CONFIG.TILE_W
    tile_h = CONFIG.TILE_H
    tiles_x = CONFIG.TILES_X
    tiles_y = CONFIG.TILES_Y
    total = CONFIG.TOTAL_TILES
    scale = CONFIG.CANVAS_SCALE
    tiles_per_set = CONFIG.TILES_PER_SET

    canvas_w = width * scale
    canvas_h = height * scale

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>X65 Tile Editor</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}

        body {{
            font-family: 'Courier New', monospace;
            background: #0d0d14;
            color: #c8c8d8;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 44px 10px 10px;
            gap: 8px;
            overflow-x: auto;
        }}

        /* ── TOOLBAR ─────────────────────────────────────────────── */
        .toolbar {{
            position: fixed;
            top: 0; left: 0; width: 100%;
            z-index: 1000;
            height: 40px;
            background: #111118;
            border-bottom: 2px solid #ffaa44;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .toolbar-inner {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0;
            width: {canvas_w}px;
            max-width: 100%;
            padding: 0;
            margin: 0;
        }}

        .toolbar .panel-box {{
            display: flex;
            align-items: center;
            gap: 4px;
            padding: 0 8px;
            border-right: 1px solid #1e1e2c;
        }}
        .toolbar .panel-box:first-child {{
            border-left: 1px solid #1e1e2c;
        }}

        .toolbar-sep {{
            width: 1px;
            height: 16px;
            background: #252534;
            margin: 0 2px;
            flex-shrink: 0;
        }}

        /* ── TILE INFO ──────────────────────────────────────────── */
        .info-cell {{
            font-size: 10px;
            color: #6a6a88;
            white-space: nowrap;
            line-height: 1;
        }}
        .info-cell strong {{ color: #ffaa44; font-weight: 700; }}
        .info-sep {{ font-size: 9px; color: #2a2a3a; margin: 0 3px; }}

        #tileInfoBlock {{ width: 90px; }}
        #tileInfoSet  {{ width: 120px; }}
        #tileInfoPos  {{ width: 46px; text-align: right; }}

        /* ── COLOR EDITOR ───────────────────────────────────────── */
        .color-row {{ display: flex; align-items: center; gap: 4px; }}

        .color-row label {{
            font-size: 8px;
            color: #505065;
            width: 20px;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            font-weight: 700;
            flex-shrink: 0;
        }}

        .swatch-big {{
            width: 18px; height: 18px;
            border: 1px solid #2a2a40;
            cursor: pointer;
            flex-shrink: 0;
            transition: border-color 0.1s, transform 0.1s;
        }}
        .swatch-big:hover {{ border-color: #ffaa44; transform: scale(1.12); }}

        .idx-input {{
            width: 38px;
            background: #0a0a10;
            border: 1px solid #252534;
            color: #ccc;
            font-family: 'Courier New', monospace;
            font-size: 10px;
            padding: 2px 3px;
            text-align: center;
            outline: none;
            height: 20px;
            -moz-appearance: textfield;
        }}
        .idx-input::-webkit-outer-spin-button,
        .idx-input::-webkit-inner-spin-button {{ -webkit-appearance: none; margin: 0; }}
        .idx-input:focus  {{ border-color: #ffaa44; }}
        .idx-input.changed {{ border-color: #44ddaa; color: #44ddaa; }}

        .hex-label {{ font-size: 9px; color: #555568; width: 22px; flex-shrink: 0; }}

        /* ── BUTTONS ────────────────────────────────────────────── */
        .btn-icon {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 4px;
            height: 26px;
            min-width: 26px;
            padding: 0 6px;
            border: none;
            cursor: pointer;
            font-family: 'Courier New', monospace;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.3px;
            flex-shrink: 0;
            transition: background 0.1s, color 0.1s, opacity 0.1s;
            background: #ffaa44;
            color: #0d0d14;
        }}
        .btn-icon:hover:not(:disabled) {{ background: #ffc060; }}
        .btn-icon:active:not(:disabled) {{ opacity: 0.8; }}
        .btn-icon:disabled {{ opacity: 0.28; cursor: default; pointer-events: none; }}

        .btn-icon.secondary {{
            background: #191924;
            color: #7070a0;
            border: 1px solid #252534;
        }}
        .btn-icon.secondary:hover:not(:disabled) {{
            background: #222230;
            color: #b0b0d0;
            border-color: #383858;
        }}

        .btn-icon#btnSave.unsaved {{
            background: #ffffff;
            color: #0d0d14;
            outline: 2px solid #ffaa44;
            outline-offset: 0;
        }}

        .status-bar {{
            font-size: 9px;
            color: #44ddaa;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            width: 52px;
        }}

        /* ── CANVAS ─────────────────────────────────────────────── */
        canvas {{
            display: block;
            border: 1px solid #1a1a28;
            cursor: crosshair;
            background: #000;
            image-rendering: pixelated;
            max-width: 100%;
            height: auto;
        }}
        .canvas-wrap {{ display: inline-block; position: relative; }}
        #highlightOverlay {{
            position: absolute;
            pointer-events: none;
            border: 2px solid #ffaa44;
            display: none;
            box-shadow: 0 0 0 1px rgba(255,170,68,0.25);
        }}

        /* CRT effect — layered mask: scanlines + aperture grille + vignetting */
        .canvas-wrap.crt-effect::after {{
            content: "";
            position: absolute;
            top: 0; left: 0; width: 100%; height: 100%;
            pointer-events: none;
            z-index: 10;

            background:
                /* 1. Horizontal scanlines — darkens top & bottom of each pixel (scale 3x) */
                repeating-linear-gradient(
                    0deg,
                    rgba(0, 0, 0, 0.30) 0px,
                    rgba(0, 0, 0, 0.10) 1px,
                    rgba(0, 0, 0, 0) 1px,
                    rgba(0, 0, 0, 0) 2px,
                    rgba(0, 0, 0, 0.10) 2px,
                    rgba(0, 0, 0, 0.30) 3px
                ),
                /* 2. Aperture Grille — vertical RGB subpixels every 3px */
                repeating-linear-gradient(
                    90deg,
                    rgba(255, 0, 0, 0.15) 0px,
                    rgba(255, 0, 0, 0.15) 1px,
                    rgba(0, 255, 0, 0.15) 1px,
                    rgba(0, 255, 0, 0.15) 2px,
                    rgba(0, 0, 255, 0.15) 2px,
                    rgba(0, 0, 255, 0.15) 3px
                ),
                /* 3. Vignetting — darkening of corners */
                radial-gradient(
                    ellipse at center,
                    rgba(0, 0, 0, 0) 50%,
                    rgba(0, 0, 0, 0.40) 90%,
                    rgba(0, 0, 0, 0.70) 100%
                );

            background-size:
                100% 3px,   /* scanline every 3px = 1 pixel row */
                3px 100%,   /* RGB mask every 3px = 1 pixel width */
                100% 100%;  /* vignetting */

            mix-blend-mode: multiply;
            opacity: 0.85;

            /* Subtle inner shadow — simulates screen curvature */
            box-shadow: inset 0 0 80px rgba(0,0,0,0.6);
        }}

        /* Color boost under the CRT mask */
        .canvas-wrap.crt-effect canvas {{
            filter: contrast(1.12) brightness(1.06) saturate(1.12);
        }}

        /* ── PALETTE PICKER ─────────────────────────────────────── */
        #palettePicker {{
            position: fixed; top: 44px; left: 50%; transform: translateX(-50%);
            background: #13131c;
            border: 1px solid #2a2a40;
            padding: 4px;
            display: none;
            z-index: 2000;
            box-shadow: 0 8px 28px rgba(0,0,0,0.85);
        }}
        .palette-grid {{
            display: grid;
            grid-template-columns: repeat(8, 22px);
            gap: 1px;
            background: #1a1a28;
        }}
        .palette-cell {{
            width: 22px; height: 18px;
            cursor: pointer;
            border: 1px solid transparent;
            transition: transform 0.08s;
        }}
        .palette-cell:hover  {{ outline: 2px solid #fff; z-index: 5; transform: scale(1.1); }}
        .palette-cell.active {{ outline: 2px solid #ffaa44; z-index: 4; }}
    </style>
</head>
<body>

<div id="palettePicker">
    <div class="palette-grid" id="paletteGrid"></div>
</div>

<div class="toolbar">
    <div class="toolbar-inner">

        <!-- ① Tile info -->
        <div class="panel-box">
            <span class="info-cell" id="tileInfoBlock">Block <strong>1</strong>/1440</span>
            <span class="info-sep">·</span>
            <span class="info-cell" id="tileInfoSet">Set <strong>1</strong> Char <strong>001</strong></span>
            <span class="info-sep">·</span>
            <span class="info-cell" id="tileInfoPos">(0,0)</span>
        </div>

        <!-- ② Colors + edit actions -->
        <div class="panel-box">
            <div class="color-row">
                <label>BG</label>
                <div class="swatch-big" id="bgSwatch" title="Click to pick from palette"></div>
                <input class="idx-input" id="bgInput" type="number" min="0" max="255" value="0" disabled>
                <div class="hex-label" id="bgHex">$00</div>

                <div class="toolbar-sep"></div>

                <label>FG</label>
                <div class="swatch-big" id="fgSwatch" title="Click to pick from palette"></div>
                <input class="idx-input" id="fgInput" type="number" min="0" max="255" value="0" disabled>
                <div class="hex-label" id="fgHex">$00</div>

                <div class="toolbar-sep"></div>

                <!-- Copy attributes -->
                <button class="btn-icon secondary" id="btnCopy" disabled title="Copy tile attributes (C)">
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none"
                         stroke="currentColor" stroke-width="1.5"
                         stroke-linecap="round" stroke-linejoin="round">
                        <rect x="4" y="4" width="8" height="8" rx="1"/>
                        <path d="M2 10V3a1 1 0 0 1 1-1h7"/>
                    </svg>
                </button>

                <!-- Paste attributes -->
                <button class="btn-icon secondary" id="btnPaste" disabled title="Paste tile attributes (V)">
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none"
                         stroke="currentColor" stroke-width="1.5"
                         stroke-linecap="round" stroke-linejoin="round">
                        <rect x="2" y="3" width="10" height="10" rx="1"/>
                        <path d="M5 3V2h4v1"/>
                        <line x1="5" y1="7" x2="9" y2="7"/>
                        <line x1="5" y1="9.5" x2="7.5" y2="9.5"/>
                    </svg>
                </button>

                <!-- Undo -->
                <button class="btn-icon secondary" id="btnUndo" disabled title="Undo last change (Z)">
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none"
                         stroke="currentColor" stroke-width="1.5"
                         stroke-linecap="round" stroke-linejoin="round">
                        <path d="M3 7h8"/>
                        <path d="M6 4l-3 3 3 3"/>
                    </svg>
                </button>

                <!-- Apply changes -->
                <button class="btn-icon" id="btnApply" disabled title="Apply colour changes">
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none"
                         stroke="currentColor" stroke-width="2.2"
                         stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="2 7.5 5.5 11 12 3"/>
                    </svg>
                </button>
            </div>
        </div>

        <!-- ③ View tools -->
        <div class="panel-box">

            <!-- Toggle grid -->
            <button class="btn-icon secondary" id="btnToggleGrid" title="Show/hide tile grid">
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none"
                     stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
                    <rect x="1" y="1" width="12" height="12" rx="1"/>
                    <line x1="5" y1="1" x2="5" y2="13"/>
                    <line x1="9" y1="1" x2="9" y2="13"/>
                    <line x1="1" y1="5" x2="13" y2="5"/>
                    <line x1="1" y1="9" x2="13" y2="9"/>
                </svg>
            </button>

            <!-- Highlight modified tiles -->
            <button class="btn-icon secondary" id="btnHighlightModified" title="Highlight edited tiles">
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none"
                     stroke="currentColor" stroke-width="1.5"
                     stroke-linecap="round" stroke-linejoin="round">
                    <path d="M9.5 1.5 l3 3 -7 7 H2.5 V9 Z"/>
                    <line x1="7.5" y1="3.5" x2="10.5" y2="6.5"/>
                </svg>
            </button>

            <div class="toolbar-sep"></div>

            <!-- CRT effect -->
            <button class="btn-icon secondary" id="btnToggleCRT" title="CRT effect (simulated tube mask)">
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none"
                     stroke="currentColor" stroke-width="1.5"
                     stroke-linecap="round" stroke-linejoin="round">
                    <rect x="1" y="1.5" width="12" height="8.5" rx="1.5"/>
                    <line x1="1.5" y1="4.5" x2="12.5" y2="4.5"/>
                    <line x1="1.5" y1="7"   x2="12.5" y2="7"/>
                    <line x1="4.5" y1="10"  x2="9.5"  y2="10"/>
                    <line x1="7"   y1="10"  x2="7"    y2="12.5"/>
                </svg>
            </button>

            <!-- Toggle smoothing: square=sharp, circle=smooth -->
            <button class="btn-icon secondary" id="btnToggleSmoothing" title="Smoothing: sharp">
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none"
                     stroke="currentColor" stroke-width="1.5"
                     stroke-linecap="round" stroke-linejoin="round">
                    <rect x="1.5" y="5" width="4" height="4"/>
                    <circle cx="10" cy="7" r="2.5"/>
                </svg>
            </button>
        </div>

        <!-- ④ Save -->
        <div class="panel-box">
            <button class="btn-icon" id="btnSave" title="Save changes on the server">
                <svg width="13" height="13" viewBox="0 0 14 14" fill="none"
                     stroke="currentColor" stroke-width="1.5"
                     stroke-linecap="round" stroke-linejoin="round">
                    <path d="M2 1h8l2 2v9a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V1z"/>
                    <rect x="4" y="1" width="5" height="3.5"/>
                    <rect x="3.5" y="8" width="7" height="4" rx="0.5"/>
                </svg>
                Save
            </button>
            <div id="saveStatus" class="status-bar"></div>
        </div>

        <!-- ⑤ Downloads -->
        <div class="panel-box">
            <!-- Download BG map -->
            <button class="btn-icon secondary" id="btnDlBg" title="Download background map">
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none"
                     stroke="currentColor" stroke-width="1.5"
                     stroke-linecap="round" stroke-linejoin="round">
                    <line x1="6" y1="1" x2="6" y2="8"/>
                    <polyline points="3.5 5.5 6 8 8.5 5.5"/>
                    <line x1="1.5" y1="10.5" x2="10.5" y2="10.5"/>
                </svg>
                <span style="font-size:9px;font-weight:700;letter-spacing:0.3px;">BG</span>
            </button>

            <!-- Download FG map -->
            <button class="btn-icon secondary" id="btnDlFg" title="Download foreground map">
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none"
                     stroke="currentColor" stroke-width="1.5"
                     stroke-linecap="round" stroke-linejoin="round">
                    <line x1="6" y1="1" x2="6" y2="8"/>
                    <polyline points="3.5 5.5 6 8 8.5 5.5"/>
                    <line x1="1.5" y1="10.5" x2="10.5" y2="10.5"/>
                </svg>
                <span style="font-size:9px;font-weight:700;letter-spacing:0.3px;">FG</span>
            </button>

            <!-- Download split (BG+FG) -->
            <button class="btn-icon secondary" id="btnDlSplit" title="Download combined maps (BG+FG)">
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none"
                     stroke="currentColor" stroke-width="1.5"
                     stroke-linecap="round" stroke-linejoin="round">
                    <line x1="6" y1="1" x2="6" y2="8"/>
                    <polyline points="3.5 5.5 6 8 8.5 5.5"/>
                    <line x1="1.5" y1="10.5" x2="10.5" y2="10.5"/>
                </svg>
                <span style="font-size:9px;font-weight:700;letter-spacing:0.3px;">B+F</span>
            </button>
        </div>

    </div>
</div>

<div class="main-layout" style="width: 100%; text-align: center;">
    <div class="canvas-wrap" id="canvasWrap">
        <canvas id="tileCanvas" width="{canvas_w}" height="{canvas_h}"></canvas>
        <div id="highlightOverlay"></div>
    </div>
</div>

<script>
(function() {{
    const WIDTH = {width}, HEIGHT = {height}, TILE_W = {tile_w}, TILE_H = {tile_h};
    const TILES_X = {tiles_x}, TILES_Y = {tiles_y}, TOTAL = {total}, SCALE = {scale}, TILES_PER_SET = {tiles_per_set};

    let palette, bgMap, fgMap, simImage, hiresMask;
    const modified = new Set();
    let selectedTile = 0, gridVisible = true, smoothingEnabled = false, highlightModified = false;
    let copiedBg = null, copiedFg = null;
    let pickingFor = null;
    let crtEnabled = false;

    const MAX_HISTORY = 20;
    const history = [];
    const btnUndo = document.getElementById('btnUndo');

    const canvas = document.getElementById('tileCanvas'), ctx = canvas.getContext('2d');
    const canvasWrap = document.getElementById('canvasWrap');
    const overlay = document.getElementById('highlightOverlay'), saveStatus = document.getElementById('saveStatus');
    const bgInput = document.getElementById('bgInput'), fgInput = document.getElementById('fgInput');
    const bgSwatch = document.getElementById('bgSwatch'), fgSwatch = document.getElementById('fgSwatch');
    const bgHexEl = document.getElementById('bgHex'), fgHexEl = document.getElementById('fgHex');
    const palettePicker = document.getElementById('palettePicker'), paletteGrid = document.getElementById('paletteGrid');
    const btnCopy = document.getElementById('btnCopy'), btnPaste = document.getElementById('btnPaste'), btnSave = document.getElementById('btnSave');
    const btnToggleGrid = document.getElementById('btnToggleGrid');
    const btnToggleSmoothing = document.getElementById('btnToggleSmoothing');
    const btnHighlightModified = document.getElementById('btnHighlightModified');
    const btnToggleCRT = document.getElementById('btnToggleCRT');

    function rgb(idx) {{ return palette[idx] || [0,0,0]; }}
    function toHex(c) {{ return '#' + ((1<<24)+(c[0]<<16)+(c[1]<<8)+c[2]).toString(16).slice(1).toUpperCase(); }}
    function toHexByte(val) {{ return '$' + val.toString(16).toUpperCase().padStart(2, '0'); }}

    function pushHistory() {{
        if (history.length >= MAX_HISTORY) history.shift();
        history.push({{
            bg: new Uint8Array(bgMap),
            fg: new Uint8Array(fgMap),
            modified: new Set(modified)
        }});
        btnUndo.disabled = false;
    }}

    function undo() {{
        if (history.length === 0) return;
        const state = history.pop();
        bgMap.set(state.bg);
        fgMap.set(state.fg);
        modified.clear();
        state.modified.forEach(v => modified.add(v));
        drawAll();
        updatePanel(selectedTile);
        btnUndo.disabled = history.length === 0;
        btnSave.classList.toggle('unsaved', modified.size > 0);
    }}

    btnUndo.onclick = undo;

    async function loadData() {{
        try {{
            const ts = Date.now();
            const [palRes, bgRes, fgRes] = await Promise.all([
                fetch('x65_palette.json?t='+ts),
                fetch('x65_background.map?t='+ts),
                fetch('x65_foreground.map?t='+ts)
            ]);

            if (!palRes.ok || !bgRes.ok || !fgRes.ok) {{
                throw new Error('Failed to load data files: ' + [palRes.status, bgRes.status, fgRes.status].join(','));
            }}

            palette = await palRes.json();
            bgMap = new Uint8Array(await bgRes.arrayBuffer());
            fgMap = new Uint8Array(await fgRes.arrayBuffer());

            const simImg = new Image(), hiresImg = new Image();
            const promises = [
                new Promise((resolve, reject) => {{
                    simImg.onload = resolve;
                    simImg.onerror = reject;
                    simImg.src = 'x65_simulation_ultra.png?t='+ts;
                }}),
                new Promise((resolve, reject) => {{
                    hiresImg.onload = resolve;
                    hiresImg.onerror = reject;
                    hiresImg.src = 'x65_hires_ultra.png?t='+ts;
                }})
            ];
            await Promise.all(promises);
            simImage = simImg;

            const tmpC = document.createElement('canvas'); tmpC.width = WIDTH; tmpC.height = HEIGHT;
            const tmpCtx = tmpC.getContext('2d'); tmpCtx.drawImage(hiresImg, 0, 0);
            const data = tmpCtx.getImageData(0,0,WIDTH,HEIGHT).data;
            hiresMask = new Uint8Array(WIDTH*HEIGHT);
            for(let i=0; i<data.length; i+=4) hiresMask[i/4] = data[i]>128?1:0;

            initPalette();
            drawAll(); updatePanel(0); positionOverlay(0);

            // Set initial toggle titles / styles
            btnToggleSmoothing.title = smoothingEnabled ? 'Disable smoothing' : 'Enable smoothing';
            btnToggleGrid.style.background = gridVisible ? '#44ddaa' : '';
            btnToggleGrid.style.color = gridVisible ? '#0d0d14' : '';
        }} catch(e) {{
            console.error(e);
            alert('Failed to load data. Check the console.');
        }}
    }}

    function initPalette() {{
        paletteGrid.innerHTML = '';
        const headerRow = document.createElement('div');
        headerRow.style.display = 'contents';
        for (let i = 0; i < 8; i++) {{
            const h = document.createElement('div');
            h.style.fontSize = '9px';
            h.style.color = '#aaa';
            h.style.textAlign = 'center';
            h.textContent = i;
            headerRow.appendChild(h);
        }}
        paletteGrid.appendChild(headerRow);

        palette.forEach((color, i) => {{
            const div = document.createElement('div');
            div.className = 'palette-cell';
            div.style.background = toHex(color);
            div.title = `${{i}} (${{toHexByte(i)}})  R:${{color[0]}} G:${{color[1]}} B:${{color[2]}}`;
            div.onclick = (e) => {{
                if(pickingFor === 'bg') bgInput.value = i;
                else fgInput.value = i;
                updateLivePreview();
                palettePicker.style.display = 'none';
                e.stopPropagation();
            }};
            if ((i + 1) % 8 === 0 && i < 255) {{
                div.style.marginBottom = '1px';
            }}
            paletteGrid.appendChild(div);
        }});
    }}

    function updateLivePreview() {{
        let bVal = parseInt(bgInput.value); if(isNaN(bVal)) bVal=0;
        let fVal = parseInt(fgInput.value); if(isNaN(fVal)) fVal=0;
        bgSwatch.style.background = toHex(rgb(bVal));
        fgSwatch.style.background = toHex(rgb(fVal));
        bgHexEl.textContent = toHexByte(bVal);
        fgHexEl.textContent = toHexByte(fVal);
        bgInput.classList.toggle('changed', bVal !== bgMap[selectedTile]);
        fgInput.classList.toggle('changed', fVal !== fgMap[selectedTile]);
    }}

    function drawAll() {{
        if (!simImage) return;
        ctx.imageSmoothingEnabled = smoothingEnabled;
        ctx.drawImage(simImage, 0, 0, WIDTH, HEIGHT, 0, 0, canvas.width, canvas.height);
        for(const idx of modified) redrawTile(idx);
        if(gridVisible) drawGrid();
        if(highlightModified) drawModifiedHighlights();
    }}

    function redrawTile(idx) {{
        const tx = idx % TILES_X, ty = Math.floor(idx / TILES_X);
        const bg = rgb(bgMap[idx]), fg = rgb(fgMap[idx]);
        const startX = tx * TILE_W * SCALE, startY = ty * TILE_H * SCALE;

        const tileCanvas = document.createElement('canvas');
        tileCanvas.width = TILE_W;
        tileCanvas.height = TILE_H;
        const tileCtx = tileCanvas.getContext('2d');
        const imgData = tileCtx.createImageData(TILE_W, TILE_H);

        for(let py=0; py<TILE_H; py++) {{
            for(let px=0; px<TILE_W; px++) {{
                const color = hiresMask[(ty*TILE_H+py)*WIDTH+(tx*TILE_W+px)] ? fg : bg;
                const dIdx = (py*TILE_W+px)*4;
                imgData.data[dIdx]   = color[0];
                imgData.data[dIdx+1] = color[1];
                imgData.data[dIdx+2] = color[2];
                imgData.data[dIdx+3] = 255;
            }}
        }}
        tileCtx.putImageData(imgData, 0, 0);
        ctx.drawImage(tileCanvas, 0, 0, TILE_W, TILE_H, startX, startY, TILE_W*SCALE, TILE_H*SCALE);
    }}

    function drawGrid() {{
        ctx.save();
        ctx.setLineDash([2, 4]);
        ctx.strokeStyle = '#44ddaa44';
        ctx.lineWidth = 1;
        for(let ty=0; ty<=TILES_Y; ty++) {{
            ctx.beginPath();
            ctx.moveTo(0, ty*TILE_H*SCALE);
            ctx.lineTo(canvas.width, ty*TILE_H*SCALE);
            ctx.stroke();
        }}
        for(let tx=0; tx<=TILES_X; tx++) {{
            ctx.beginPath();
            ctx.moveTo(tx*TILE_W*SCALE, 0);
            ctx.lineTo(tx*TILE_W*SCALE, canvas.height);
            ctx.stroke();
        }}
        ctx.restore();
    }}

    function drawModifiedHighlights() {{
        if (modified.size === 0) return;
        ctx.save();
        ctx.strokeStyle = '#ff3333';
        ctx.lineWidth = 3;
        ctx.setLineDash([]);
        for(const idx of modified) {{
            const tx = idx % TILES_X, ty = Math.floor(idx / TILES_X);
            ctx.strokeRect(tx*TILE_W*SCALE, ty*TILE_H*SCALE, TILE_W*SCALE, TILE_H*SCALE);
        }}
        ctx.restore();
    }}

    function updatePanel(idx) {{
        const setN = Math.floor(idx / TILES_PER_SET) + 1, charN = (idx % TILES_PER_SET) + 1;
        document.getElementById('tileInfoBlock').innerHTML = `Block <strong>${{idx + 1}}</strong>/${{TOTAL}}`;
        document.getElementById('tileInfoSet').innerHTML = `Set <strong>${{setN}}</strong> Char <strong>${{charN.toString().padStart(3, '0')}}</strong>`;
        document.getElementById('tileInfoPos').textContent = `(${{Math.floor(idx/TILES_X)}},${{idx%TILES_X}})`;
        bgInput.value = bgMap[idx]; fgInput.value = fgMap[idx];
        bgInput.disabled = fgInput.disabled = false;
        updateLivePreview();
        document.getElementById('btnApply').disabled = false;
        btnCopy.disabled = false; btnPaste.disabled = (copiedBg === null);
        btnSave.classList.toggle('unsaved', modified.size > 0);
    }}

    function positionOverlay(idx) {{
        const tx = idx % TILES_X, ty = Math.floor(idx / TILES_X), r = canvas.getBoundingClientRect(), s = r.width/canvas.width;
        overlay.style.display = 'block';
        overlay.style.left = (tx*TILE_W*SCALE*s)+'px'; overlay.style.top = (ty*TILE_H*SCALE*s)+'px';
        overlay.style.width = (TILE_W*SCALE*s)+'px'; overlay.style.height = (TILE_H*SCALE*s)+'px';
    }}

    canvas.addEventListener('click', e => {{
        const r = canvas.getBoundingClientRect(), s = canvas.width/r.width;
        const tx = Math.floor(((e.clientX-r.left)*s)/(TILE_W*SCALE)), ty = Math.floor(((e.clientY-r.top)*s)/(TILE_H*SCALE));
        if (tx>=0 && tx<TILES_X && ty>=0 && ty<TILES_Y) {{
            selectedTile = ty * TILES_X + tx;
            updatePanel(selectedTile); positionOverlay(selectedTile);
        }}
    }});

    bgInput.addEventListener('input', updateLivePreview);
    fgInput.addEventListener('input', updateLivePreview);

    bgSwatch.onclick = (e) => {{ pickingFor = 'bg'; palettePicker.style.display = 'block'; e.stopPropagation(); }};
    fgSwatch.onclick = (e) => {{ pickingFor = 'fg'; palettePicker.style.display = 'block'; e.stopPropagation(); }};
    window.onclick = () => {{ palettePicker.style.display = 'none'; }};

    document.getElementById('btnApply').onclick = () => {{
        pushHistory();
        bgMap[selectedTile] = parseInt(bgInput.value); fgMap[selectedTile] = parseInt(fgInput.value);
        modified.add(selectedTile); drawAll(); updatePanel(selectedTile);
    }};

    btnCopy.onclick = () => {{
        copiedBg = bgMap[selectedTile]; copiedFg = fgMap[selectedTile];
        btnPaste.disabled = false;
        btnCopy.style.background = '#44ddaa';
        setTimeout(() => btnCopy.style.background = '', 200);
    }};

    btnPaste.onclick = () => {{
        if (copiedBg === null) return;
        bgInput.value = copiedBg; fgInput.value = copiedFg;
        updateLivePreview();
        document.getElementById('btnApply').click();
        btnPaste.style.background = '#44ddaa';
        setTimeout(() => btnPaste.style.background = '', 200);
    }};

    btnSave.onclick = async () => {{
        try {{
            saveStatus.textContent = 'Saving...';
            btnSave.disabled = true;
            const res = await fetch('/save', {{ method: 'POST', headers: {{'Content-Type':'application/json'}}, body: JSON.stringify({{bg:Array.from(bgMap), fg:Array.from(fgMap)}}) }});
            if(res.ok) {{
                saveStatus.textContent = 'Saved!';
                modified.clear();
                btnSave.classList.remove('unsaved');
                // Immediately navigate to the new URL – without drawing the old image
                const url = new URL(window.location.href);
                url.searchParams.set('t', Date.now());
                window.location.href = url.toString();
            }} else {{
                const text = await res.text();
                saveStatus.textContent = 'Error: '+res.status;
                alert('Save error: ' + text);
                btnSave.disabled = false;
            }}
        }} catch(e) {{
            console.error(e);
            saveStatus.textContent = 'Error';
            alert('Exception during save: ' + e);
            btnSave.disabled = false;
        }}
    }};

    btnToggleGrid.onclick = () => {{
        gridVisible = !gridVisible;
        btnToggleGrid.style.background = gridVisible ? '#44ddaa' : '';
        btnToggleGrid.style.color = gridVisible ? '#0d0d14' : '';
        drawAll();
    }};

    btnToggleSmoothing.onclick = () => {{
        smoothingEnabled = !smoothingEnabled;
        btnToggleSmoothing.title = smoothingEnabled ? 'Disable smoothing' : 'Enable smoothing';
        btnToggleSmoothing.style.background = smoothingEnabled ? '#44ddaa' : '';
        btnToggleSmoothing.style.color = smoothingEnabled ? '#0d0d14' : '';
        ctx.imageSmoothingEnabled = smoothingEnabled;
        drawAll();
    }};

    btnHighlightModified.onclick = () => {{
        highlightModified = !highlightModified;
        btnHighlightModified.style.background = highlightModified ? '#44ddaa' : '';
        btnHighlightModified.style.color = highlightModified ? '#0d0d14' : '';
        drawAll();
    }};

    btnToggleCRT.onclick = () => {{
        crtEnabled = !crtEnabled;
        if (crtEnabled) {{
            canvasWrap.classList.add('crt-effect');
            btnToggleCRT.style.background = '#44ddaa';
            btnToggleCRT.style.color = '#0d0d14';
        }} else {{
            canvasWrap.classList.remove('crt-effect');
            btnToggleCRT.style.background = '';
            btnToggleCRT.style.color = '';
        }}
    }};

    /* ── KEYBOARD SHORTCUTS ───────────────────────────────────── */
    window.addEventListener('keydown', e => {{
        // Do not capture when user is editing an input
        if (document.activeElement.tagName === 'INPUT') return;
        // Do not capture when modifiers (Ctrl, Alt, Meta) are held
        if (e.ctrlKey || e.altKey || e.metaKey) return;

        const key = e.key.toLowerCase();
        if (key === 'z') {{
            e.preventDefault();
            undo();
        }} else if (key === 'c') {{
            e.preventDefault();
            if (!btnCopy.disabled) btnCopy.click();
        }} else if (key === 'v') {{
            e.preventDefault();
            if (!btnPaste.disabled) btnPaste.click();
        }}
    }});

    document.getElementById('btnDlBg').onclick = () => download(bgMap, 'x65_background.map');
    document.getElementById('btnDlFg').onclick = () => download(fgMap, 'x65_foreground.map');
    document.getElementById('btnDlSplit').onclick = () => {{
        let c = new Uint8Array(bgMap.length+fgMap.length); c.set(bgMap); c.set(fgMap, bgMap.length);
        download(c, 'x65_maps_split.bin');
    }};

    function download(d, f) {{
        let b = new Blob([d]), u = URL.createObjectURL(b), a = document.createElement('a');
        a.href = u; a.download = f; a.click();
    }}

    loadData();
}})();
</script>
</body>
</html>
"""