# Car Thing Doom — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run Doom (shareware) in the Car Thing's Chromium browser using jacobenget/doom.wasm, with physical dial and button controls.

**Architecture:** A static web app in `apps/doom/` that loads a single `.wasm` file (doom.wasm) with a thin JS host providing framebuffer rendering, input translation, and audio. The Car Thing's physical buttons and rotary dial are intercepted as browser events and injected into the WASM Doom engine via its `reportKeyDown`/`reportKeyUp` exports.

**Tech Stack:** HTML5 Canvas, vanilla JavaScript, WebAssembly (jacobenget/doom.wasm)

**Depends on:** Server plan (Task 1-5) must be completed first.

---

## File Structure

```
apps/doom/
├── index.html      # Page shell: canvas, loading screen
├── host.js         # WASM host: imports, framebuffer rendering, game loop
├── input.js        # Car Thing hardware → Doom key translation
└── doom.wasm       # Pre-built from jacobenget/doom.wasm v0.1.0
```

---

### Task 1: Download doom.wasm and Create Page Shell

**Files:**
- Create: `apps/doom/index.html`
- Download: `apps/doom/doom.wasm`

- [ ] **Step 1: Download the pre-built doom.wasm**

Run:
```bash
mkdir -p /Users/epatel/Development/claude/carthing/apps/doom
curl -L -o /Users/epatel/Development/claude/carthing/apps/doom/doom.wasm \
  https://github.com/jacobenget/doom.wasm/releases/download/v0.1.0/doom-v0.1.0.wasm
```

Verify: `ls -la apps/doom/doom.wasm` — should be ~2-4MB.

- [ ] **Step 2: Create index.html**

Create `apps/doom/index.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=800, height=480, initial-scale=1, user-scalable=no">
    <title>DOOM - Car Thing</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #000;
            width: 800px;
            height: 480px;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        canvas {
            image-rendering: pixelated;
            image-rendering: crisp-edges;
        }
        #loading {
            color: #b00;
            font-family: monospace;
            font-size: 32px;
            text-align: center;
            position: absolute;
        }
        #loading .sub { font-size: 16px; color: #666; margin-top: 10px; }
        #menu-btn {
            position: absolute;
            top: 5px;
            right: 5px;
            width: 40px;
            height: 40px;
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 5px;
            color: #fff;
            font-size: 20px;
            cursor: pointer;
            z-index: 10;
            display: none;
            line-height: 40px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div id="loading">
        LOADING DOOM...
        <div class="sub">Preparing WAD data</div>
    </div>
    <canvas id="doom-canvas"></canvas>
    <button id="menu-btn" onclick="window.doomMenuToggle()">&#9776;</button>
    <script src="input.js"></script>
    <script src="host.js"></script>
</body>
</html>
```

- [ ] **Step 3: Commit**

```bash
git add apps/doom/index.html apps/doom/doom.wasm
git commit -m "feat: add doom page shell and download doom.wasm binary"
```

---

### Task 2: WASM Host (Framebuffer + Game Loop)

**Files:**
- Create: `apps/doom/host.js`

- [ ] **Step 1: Create host.js**

Create `apps/doom/host.js`:

```javascript
(async function () {
    const canvas = document.getElementById("doom-canvas");
    const ctx = canvas.getContext("2d");
    const loadingEl = document.getElementById("loading");
    const menuBtn = document.getElementById("menu-btn");

    let doomExports = null;
    let framebufferPtr = 0;
    let screenWidth = 0;
    let screenHeight = 0;
    let imageData = null;
    let memoryBytes = null;

    // Helper: read a C string from WASM memory
    function readString(ptr, len) {
        return new TextDecoder().decode(new Uint8Array(memoryBytes.buffer, ptr, len));
    }

    // Imports required by doom.wasm
    const imports = {
        console: {
            onErrorMessage(ptr, len) {
                console.error("DOOM:", readString(ptr, len));
            },
            onInfoMessage(ptr, len) {
                console.log("DOOM:", readString(ptr, len));
            },
        },
        gameSaving: {
            readSaveGame() { return 0; },
            sizeOfSaveGame() { return 0; },
            writeSaveGame() { return 0; },
        },
        loading: {
            onGameInit(width, height) {
                screenWidth = width;
                screenHeight = height;

                // Scale to fit 800x480 while maintaining aspect ratio
                const scaleX = 800 / width;
                const scaleY = 480 / height;
                const scale = Math.min(scaleX, scaleY);

                canvas.width = width;
                canvas.height = height;
                canvas.style.width = Math.floor(width * scale) + "px";
                canvas.style.height = Math.floor(height * scale) + "px";

                imageData = ctx.createImageData(width, height);

                loadingEl.style.display = "none";
                menuBtn.style.display = "block";
            },
            readWads() {
                // No-op: doom.wasm includes shareware WAD
            },
            wadSizes() {
                // No-op: doom.wasm includes shareware WAD
            },
        },
        runtimeControl: {
            timeInMilliseconds() {
                return BigInt(Math.floor(performance.now()));
            },
        },
        ui: {
            drawFrame(ptr) {
                framebufferPtr = ptr;
                // ARGB stored little-endian = BGRA in memory
                const pixels = new Uint8Array(
                    memoryBytes.buffer,
                    ptr,
                    screenWidth * screenHeight * 4
                );
                const data = imageData.data;
                for (let i = 0; i < screenWidth * screenHeight; i++) {
                    const src = i * 4;
                    const dst = i * 4;
                    data[dst] = pixels[src + 2];     // R (from BGRA)
                    data[dst + 1] = pixels[src + 1]; // G
                    data[dst + 2] = pixels[src];     // B
                    data[dst + 3] = 255;             // A
                }
                ctx.putImageData(imageData, 0, 0);
            },
        },
    };

    // Load and instantiate WASM
    try {
        const response = await fetch("doom.wasm");
        const { instance } = await WebAssembly.instantiateStreaming(response, imports);

        doomExports = instance.exports;
        memoryBytes = new Uint8Array(doomExports.memory.buffer);

        // Expose exports for input.js
        window.doomExports = doomExports;

        // Menu toggle via touch button
        window.doomMenuToggle = function () {
            doomExports.reportKeyDown(doomExports.KEY_ESCAPE);
            setTimeout(() => doomExports.reportKeyUp(doomExports.KEY_ESCAPE), 100);
        };

        // Initialize and start game loop
        doomExports.initGame();

        function gameLoop() {
            // Update memory reference in case it grew
            if (memoryBytes.buffer !== doomExports.memory.buffer) {
                memoryBytes = new Uint8Array(doomExports.memory.buffer);
            }
            doomExports.tickGame();
            requestAnimationFrame(gameLoop);
        }
        requestAnimationFrame(gameLoop);

        console.log("DOOM initialized successfully");
    } catch (err) {
        loadingEl.innerHTML = "ERROR<br><span class='sub'>" + err.message + "</span>";
        console.error("Failed to load DOOM:", err);
    }
})();
```

- [ ] **Step 2: Quick test in a regular browser**

Start the server locally:
```bash
cd /Users/epatel/Development/claude/carthing && python -m server.main --no-launch --host 127.0.0.1 --app doom &
```

Open `http://127.0.0.1:8080/doom/` in a browser. Verify Doom loads and renders.

Kill server: `kill %1`

- [ ] **Step 3: Commit**

```bash
git add apps/doom/host.js
git commit -m "feat: add WASM host with framebuffer rendering and game loop"
```

---

### Task 3: Input Mapping (Buttons + Dial)

**Files:**
- Create: `apps/doom/input.js`

This is the critical task — mapping Car Thing hardware to Doom controls, especially the dial.

- [ ] **Step 1: Create input.js**

Create `apps/doom/input.js`:

```javascript
/**
 * Car Thing Input → Doom Key Translation
 *
 * Car Thing hardware events in Chromium:
 *   - Buttons: keydown/keyup with code Digit1-4, Enter, Escape
 *   - Dial: wheel events (deltaY for scroll)
 *
 * Doom key exports from doom.wasm:
 *   KEY_UPARROW, KEY_DOWNARROW, KEY_LEFTARROW, KEY_RIGHTARROW
 *   KEY_FIRE, KEY_USE, KEY_ENTER, KEY_ESCAPE
 *   KEY_STRAFE_L, KEY_STRAFE_R, KEY_SHIFT, KEY_ALT, KEY_TAB
 */

(function () {
    "use strict";

    // Wait for doom exports to be available
    let exports = null;
    const pendingKeys = [];

    function getExports() {
        if (!exports && window.doomExports) {
            exports = window.doomExports;
            // Process any keys that arrived before Doom loaded
            for (const [fn, key] of pendingKeys) {
                fn === "down" ? exports.reportKeyDown(key) : exports.reportKeyUp(key);
            }
            pendingKeys.length = 0;
        }
        return exports;
    }

    // --- Button Mapping ---

    const BUTTON_MAP = {
        // Digit1-4: Movement
        "Digit1": "KEY_UPARROW",     // Forward
        "Digit2": "KEY_DOWNARROW",   // Backward
        "Digit3": "KEY_STRAFE_L",    // Strafe left
        "Digit4": "KEY_STRAFE_R",    // Strafe right
        // Home button: Shoot
        "Enter": "KEY_FIRE",
        // Back button: Use/Open
        "Escape": "KEY_USE",
    };

    document.addEventListener("keydown", function (e) {
        const doomKeyName = BUTTON_MAP[e.code];
        if (!doomKeyName) return;

        e.preventDefault();
        e.stopPropagation();

        const ex = getExports();
        if (ex) {
            ex.reportKeyDown(ex[doomKeyName]);
        }
    }, true);

    document.addEventListener("keyup", function (e) {
        const doomKeyName = BUTTON_MAP[e.code];
        if (!doomKeyName) return;

        e.preventDefault();
        e.stopPropagation();

        const ex = getExports();
        if (ex) {
            ex.reportKeyUp(ex[doomKeyName]);
        }
    }, true);

    // --- Dial (Rotary Encoder) → Turn Left/Right ---
    //
    // The dial generates wheel events. We accumulate delta over a short
    // window and translate to Doom turn key presses. The challenge:
    // Doom expects held keys for continuous turning, but the dial
    // sends discrete scroll events.
    //
    // Strategy:
    //   - Each wheel event adds to an accumulated delta
    //   - We press the turn key on first delta, release after a timeout
    //   - Fast spinning = continuous hold, slow = brief taps
    //   - Sensitivity multiplier controls how much each detent turns

    const DIAL_RELEASE_MS = 80;       // Release turn key after this many ms of no events
    const DIAL_SENSITIVITY = 1;        // Scroll events per turn key press (lower = more sensitive)

    let dialDelta = 0;                 // Accumulated scroll delta
    let dialDirection = 0;             // -1 = left, 0 = none, 1 = right
    let dialReleaseTimer = null;

    function dialRelease() {
        const ex = getExports();
        if (ex && dialDirection !== 0) {
            const key = dialDirection > 0 ? ex.KEY_RIGHTARROW : ex.KEY_LEFTARROW;
            ex.reportKeyUp(key);
        }
        dialDirection = 0;
        dialDelta = 0;
        dialReleaseTimer = null;
    }

    document.addEventListener("wheel", function (e) {
        e.preventDefault();

        const ex = getExports();
        if (!ex) return;

        // Use deltaY for vertical scroll (most common dial mapping)
        // Also check deltaX for horizontal scroll events
        const delta = e.deltaY !== 0 ? e.deltaY : e.deltaX;
        if (delta === 0) return;

        const newDirection = delta > 0 ? 1 : -1;

        // If direction changed, release old key first
        if (dialDirection !== 0 && dialDirection !== newDirection) {
            const oldKey = dialDirection > 0 ? ex.KEY_RIGHTARROW : ex.KEY_LEFTARROW;
            ex.reportKeyUp(oldKey);
            dialDirection = 0;
        }

        // Press the turn key if not already held
        if (dialDirection === 0) {
            const newKey = newDirection > 0 ? ex.KEY_RIGHTARROW : ex.KEY_LEFTARROW;
            ex.reportKeyDown(newKey);
            dialDirection = newDirection;
        }

        // Reset the release timer — key stays held while dial keeps moving
        if (dialReleaseTimer !== null) {
            clearTimeout(dialReleaseTimer);
        }
        dialReleaseTimer = setTimeout(dialRelease, DIAL_RELEASE_MS);

    }, { passive: false, capture: true });

    // --- Touchscreen: Menu Access ---
    // Since we remapped Escape to "Use", provide a touch target for Doom menu
    // The menu button in index.html calls window.doomMenuToggle()

    // Also allow touch-drag for aiming (future enhancement)

    console.log("Car Thing input mapping loaded");
    console.log("Controls: Digit1=Forward, Digit2=Back, Digit3=StrafeL, Digit4=StrafeR");
    console.log("          Enter=Shoot, Escape=Use, Dial=Turn, Touch menu btn=Doom menu");
})();
```

- [ ] **Step 2: Test input mapping in a regular browser**

Start the server:
```bash
cd /Users/epatel/Development/claude/carthing && python -m server.main --no-launch --host 127.0.0.1 --app doom &
```

Open `http://127.0.0.1:8080/doom/` in a browser. Test:
- Press 1,2,3,4 keys → should move in Doom
- Press Enter → should shoot
- Scroll mouse wheel → should turn left/right
- Click the menu button (top-right hamburger) → should open Doom menu

Kill server: `kill %1`

- [ ] **Step 3: Commit**

```bash
git add apps/doom/input.js
git commit -m "feat: add Car Thing input mapping with dial-to-turn translation"
```

---

### Task 4: Dial Tuning and Polish

**Files:**
- Modify: `apps/doom/input.js`
- Modify: `apps/doom/index.html`

- [ ] **Step 1: Add run (shift) toggle to Enter long-press**

The Car Thing has limited buttons. Add a secondary action: holding Enter briefly shoots, but the `KEY_SHIFT` (run) can be toggled by touching the screen.

Edit `apps/doom/input.js` — add before the closing `})();`:

```javascript
    // --- Run Toggle (touch screen) ---
    // Tap anywhere on the canvas to toggle run mode (Shift key)
    let running = false;

    canvas_el = document.getElementById("doom-canvas");
    if (canvas_el) {
        canvas_el.addEventListener("touchstart", function (e) {
            // Ignore if touching the menu button area (top-right 50x50)
            const touch = e.touches[0];
            if (touch.clientX > 750 && touch.clientY < 50) return;

            e.preventDefault();
            const ex = getExports();
            if (!ex) return;

            running = !running;
            if (running) {
                ex.reportKeyDown(ex.KEY_SHIFT);
            } else {
                ex.reportKeyUp(ex.KEY_SHIFT);
            }
        }, { passive: false });
    }
```

- [ ] **Step 2: Add a visual run indicator to index.html**

Edit `apps/doom/index.html` — add before `</body>`:

```html
    <div id="run-indicator" style="
        position: absolute;
        bottom: 5px;
        left: 5px;
        color: #0f0;
        font-family: monospace;
        font-size: 14px;
        opacity: 0.5;
        display: none;
        z-index: 10;
    ">RUN</div>
```

Update the touch handler in `input.js` to toggle the indicator:

```javascript
            const indicator = document.getElementById("run-indicator");
            if (indicator) {
                indicator.style.display = running ? "block" : "none";
            }
```

- [ ] **Step 3: Test dial feel parameters**

The key tuning parameters in `input.js` are:
- `DIAL_RELEASE_MS = 80` — how long to hold the turn key after last scroll event
  - Lower (40-60ms) = snappier but may stutter
  - Higher (100-150ms) = smoother but less responsive
- These can be adjusted once testing on the actual Car Thing hardware

- [ ] **Step 4: Commit**

```bash
git add apps/doom/input.js apps/doom/index.html
git commit -m "feat: add run toggle via touchscreen and dial tuning parameters"
```

---

### Task 5: End-to-End Test on Car Thing

**Files:**
- None created — hardware verification

- [ ] **Step 1: Connect Car Thing via USB**

Verify: `adb devices` shows the device.

- [ ] **Step 2: Check USB network**

Run: `ping -c 3 172.16.42.2`

Expected: Successful pings.

- [ ] **Step 3: Launch Doom via server**

Run: `cd /Users/epatel/Development/claude/carthing && python -m server.main --app doom`

Expected:
1. "Device connected!" message
2. "Launching doom on Car Thing..." message
3. "Starting server on 0.0.0.0:8080" message
4. Doom loads and renders on the Car Thing display

- [ ] **Step 4: Test all controls on hardware**

Verify each control:
- Dial clockwise → turns right in Doom
- Dial counter-clockwise → turns left in Doom
- Preset 1 → move forward
- Preset 2 → move backward
- Preset 3 → strafe left
- Preset 4 → strafe right
- Home (Enter) → shoot
- Back (Escape) → use/open doors
- Touch screen → toggle run
- Touch menu button → Doom menu

- [ ] **Step 5: Tune dial sensitivity if needed**

If the dial feels too slow or too fast, adjust `DIAL_RELEASE_MS` in `apps/doom/input.js`:
- Too sluggish: decrease to 40-60ms
- Too twitchy: increase to 100-150ms

- [ ] **Step 6: Final commit**

```bash
git add -u
git commit -m "tune: adjust dial sensitivity after hardware testing"
```
