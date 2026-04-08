# Car Thing: Doom + Minimal Server Design

## Overview

Two independent sub-projects to get a web-based Doom running on the Spotify Car Thing, managed by a minimal Python server.

---

## Sub-project 1: Doom on Car Thing

### Goal

Run Doom (shareware) in the Car Thing's Chromium browser using a pre-built WebAssembly port, with physical button and dial controls.

### Architecture

A static HTML/JS/WASM application that:

1. Loads a pre-built PrBoom-WASM (or similar) Doom port
2. Renders to an 800x480 canvas (Car Thing's native resolution)
3. Intercepts Car Thing hardware events in the browser and translates them to Doom key inputs

### Input Mapping

The Car Thing's hardware surfaces in Chromium as standard browser events:

| Car Thing Input | Browser Event | Doom Action |
|---|---|---|
| Dial clockwise | ScrollDown/ScrollRight | Turn right |
| Dial counter-clockwise | ScrollUp/ScrollLeft | Turn left |
| Preset 1 (Digit1) | keydown `Digit1` | Move forward |
| Preset 2 (Digit2) | keydown `Digit2` | Move backward |
| Preset 3 (Digit3) | keydown `Digit3` | Strafe left |
| Preset 4 (Digit4) | keydown `Digit4` | Strafe right |
| Home (Enter) | keydown `Enter` | Shoot |
| Back (Escape) | keydown `Escape` | Use / Open door |

**Note:** Doom's native Escape key opens the menu. Since we remap Escape to "Use", the Doom menu will be accessible via a touchscreen tap in a designated corner (top-right, small menu icon) which synthesizes a native Escape keypress to Doom.

### Dial Handling

The dial is the most critical input. Strategy:

- Listen for `wheel` and scroll events on the document
- Accumulate scroll delta values over a short window (~16ms, one frame)
- Map accumulated delta to Doom turn speed: small delta = fine aim, large delta = fast turn
- Synthesize Doom-compatible `keydown`/`keyup` events for left/right arrow keys
- Use a decay timer — if no scroll events arrive within ~50ms, release the turn key

This gives smooth, proportional turning from the physical dial.

### Display

- Canvas sized to 800x480 (native resolution, no scaling needed)
- Doom's internal 320x200 is upscaled by the WASM port
- Fullscreen, no browser chrome (Chromium launched in kiosk mode)

### Audio

- Car Thing has a built-in speaker
- Doom audio via Web Audio API (supported in Car Thing's Chromium)

### WAD File

- Bundle DOOM1.WAD (shareware, freely distributable)
- ~4MB, loaded from the server via HTTP

### File Structure

```
apps/doom/
├── index.html      # Doom loader page, canvas setup
├── input.js        # Car Thing event → Doom key translation
├── doom.js         # Pre-built WASM Doom port (JS glue)
├── doom.wasm       # Compiled Doom engine
├── doom.data       # Asset bundle (if needed by port)
└── DOOM1.WAD       # Shareware Doom WAD
```

---

## Sub-project 2: Minimal Python Server

### Goal

A lean Python server that detects the Car Thing, serves web apps to it, and provides WebSocket communication. No Electron, no GUI, no app store.

### Architecture

Three components in a single Python package:

1. **ADB Manager** — Device detection, setup commands, browser launch
2. **HTTP Server** — Serves static files (web apps) over USB network
3. **WebSocket Bridge** — Real-time bidirectional communication for future extensibility

### Network Topology

```
[Mac/PC]                          [Car Thing]
Python Server :8080  ──HTTP/WS──>  Chromium browser
     │
  ADB over USB  ────────────────>  Device setup / launch
```

The Car Thing's USB network gadget (already configured in DeskThing's rootfs) creates a network interface. The server binds to `172.16.42.1:8080` (the host side of the USB network).

### Startup Flow

1. Detect Car Thing via `adb devices` (using `adb-shell` library)
2. Verify USB network interface is up (ping `172.16.42.2`)
3. Start FastAPI server on `172.16.42.1:8080`
4. ADB shell: launch Chromium on Car Thing pointing to `http://172.16.42.1:8080/doom/`
5. Server serves static files from `apps/` directory

### WebSocket Protocol

Simple JSON messages for future extensibility:

```json
// Server → Car Thing
{"type": "config", "data": {"volume": 80}}

// Car Thing → Server
{"type": "input", "data": {"button": "Digit1", "event": "press"}}
```

Not needed for Doom initially, but the plumbing is there for future apps.

### Dependencies

- `fastapi` — HTTP + WebSocket server
- `uvicorn` — ASGI server
- `adb-shell` — ADB communication without requiring adb binary
- `websockets` — WebSocket support (FastAPI dependency)

### File Structure

```
server/
├── main.py          # Entry point, CLI, orchestration
├── adb_manager.py   # Device detection, ADB commands
├── server.py        # FastAPI app, routes, WebSocket
└── requirements.txt # Python dependencies
```

### CLI Usage

```bash
# Install dependencies
pip install -r server/requirements.txt

# Run (detects device, starts server, launches Doom)
python server/main.py

# Run with custom app
python server/main.py --app weather
```

---

## Build Order

1. **Server first** — Get the Python server detecting the Car Thing and serving a test page
2. **Doom second** — Once we can serve pages, add the Doom WASM app with input mapping
3. **Dial tuning** — Iterate on dial sensitivity and feel with the physical device

---

## Constraints & Assumptions

- Car Thing is already flashed with DeskThing-compatible firmware (superbird-tool)
- USB network gadget is configured (172.16.42.x subnet)
- ADB is accessible over USB
- Car Thing runs Chromium capable of WebAssembly and Web Audio
- Python 3.10+ on the host machine
- Doom shareware WAD is freely distributable (id Software's license permits this)

## Open Questions

- Exact scroll event shape from the dial in Chromium (wheel vs. custom) — needs testing on device
- Whether the Car Thing's Chromium supports `requestAnimationFrame` at 60fps or is capped
- Audio latency over Web Audio on the Car Thing
