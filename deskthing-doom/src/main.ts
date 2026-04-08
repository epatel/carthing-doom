import { DeskThing } from '@deskthing/client';

// Initialize DeskThing client
DeskThing.on('start', () => {
  console.log('DeskThing client connected');
});

// --- DOOM WASM Host ---

const canvas = document.getElementById("doom-canvas") as HTMLCanvasElement;
const ctx = canvas.getContext("2d")!;
const loadingEl = document.getElementById("loading")!;
const menuBtn = document.getElementById("menu-btn")!;

let doomExports: any = null;
let doomMemory: WebAssembly.Memory | null = null;
let screenWidth = 0;
let screenHeight = 0;
let imageData: ImageData | null = null;

function readString(ptr: number, len: number): string {
  if (!doomMemory) return "";
  return new TextDecoder().decode(new Uint8Array(doomMemory.buffer, ptr, len));
}

const imports = {
  console: {
    onErrorMessage(ptr: number, len: number) {
      console.error("DOOM:", readString(ptr, len));
    },
    onInfoMessage(ptr: number, len: number) {
      console.log("DOOM:", readString(ptr, len));
    },
  },
  gameSaving: {
    readSaveGame() { return 0; },
    sizeOfSaveGame() { return 0; },
    writeSaveGame() { return 0; },
  },
  loading: {
    onGameInit(width: number, height: number) {
      screenWidth = width;
      screenHeight = height;

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
    readWads() {},
    wadSizes() {},
  },
  runtimeControl: {
    timeInMilliseconds() {
      return Math.floor(performance.now());
    },
  },
  ui: {
    drawFrame(ptr: number) {
      if (!doomMemory || !imageData) return;
      const pixels = new Uint8Array(doomMemory.buffer, ptr, screenWidth * screenHeight * 4);
      const data = imageData.data;
      for (let i = 0; i < screenWidth * screenHeight; i++) {
        const src = i * 4;
        const dst = i * 4;
        data[dst] = pixels[src + 2];
        data[dst + 1] = pixels[src + 1];
        data[dst + 2] = pixels[src];
        data[dst + 3] = 255;
      }
      ctx.putImageData(imageData, 0, 0);
    },
  },
};

// --- Input Mapping ---

const BUTTON_MAP: Record<string, string[]> = {
  "Digit1": ["KEY_UPARROW"],
  "Digit2": ["KEY_DOWNARROW"],
  "Digit3": ["KEY_STRAFE_L"],
  "Digit4": ["KEY_STRAFE_R"],
  "KeyM":   ["KEY_USE"],
  "Enter":  ["KEY_FIRE", "KEY_ENTER"],
  "Escape": ["KEY_ESCAPE"],
};

document.addEventListener("keydown", (e) => {
  const doomKeys = BUTTON_MAP[e.code];
  if (!doomKeys || !doomExports) return;
  e.preventDefault();
  e.stopPropagation();
  for (const key of doomKeys) {
    doomExports.reportKeyDown(doomExports[key]);
  }
}, true);

document.addEventListener("keyup", (e) => {
  const doomKeys = BUTTON_MAP[e.code];
  if (!doomKeys || !doomExports) return;
  e.preventDefault();
  e.stopPropagation();
  for (const key of doomKeys) {
    doomExports.reportKeyUp(doomExports[key]);
  }
}, true);

// Dial handling
const DIAL_RELEASE_MS = 80;
let dialDirection = 0;
let dialReleaseTimer: ReturnType<typeof setTimeout> | null = null;

function dialRelease() {
  if (doomExports && dialDirection !== 0) {
    const key = dialDirection > 0 ? doomExports.KEY_RIGHTARROW : doomExports.KEY_LEFTARROW;
    doomExports.reportKeyUp(key);
  }
  dialDirection = 0;
  dialReleaseTimer = null;
}

document.addEventListener("wheel", (e) => {
  e.preventDefault();
  if (!doomExports) return;

  let delta = e.deltaX;
  if (delta === 0) delta = e.deltaY;
  if (delta === 0) return;

  const newDirection = delta > 0 ? 1 : -1;

  // Direction change: release old turn key
  if (dialDirection !== 0 && dialDirection !== newDirection) {
    const oldKey = dialDirection > 0 ? doomExports.KEY_RIGHTARROW : doomExports.KEY_LEFTARROW;
    doomExports.reportKeyUp(oldKey);
    dialDirection = 0;
  }

  // Press turn key for gameplay
  if (dialDirection === 0) {
    const newKey = newDirection > 0 ? doomExports.KEY_RIGHTARROW : doomExports.KEY_LEFTARROW;
    doomExports.reportKeyDown(newKey);
    dialDirection = newDirection;
  }

  if (dialReleaseTimer !== null) clearTimeout(dialReleaseTimer);
  dialReleaseTimer = setTimeout(dialRelease, DIAL_RELEASE_MS);
}, { passive: false, capture: true });

// Touch: run toggle
let running = false;
canvas.addEventListener("touchstart", (e) => {
  const touch = e.touches[0];
  if (touch.clientX > 750 && touch.clientY < 50) return;
  e.preventDefault();
  if (!doomExports) return;
  running = !running;
  if (running) {
    doomExports.reportKeyDown(doomExports.KEY_SHIFT);
  } else {
    doomExports.reportKeyUp(doomExports.KEY_SHIFT);
  }
  const indicator = document.getElementById("run-indicator");
  if (indicator) indicator.style.display = running ? "block" : "none";
}, { passive: false });

// Menu toggle button
(window as any).doomMenuToggle = () => {
  if (!doomExports) return;
  doomExports.reportKeyDown(doomExports.KEY_ESCAPE);
  setTimeout(() => { doomExports.reportKeyUp(doomExports.KEY_ESCAPE); }, 100);
};

// --- Load and Start DOOM ---

async function startDoom() {
  try {
    loadingEl.querySelector(".sub")!.textContent = "Downloading DOOM engine...";
    const response = await fetch("doom.wasm");
    loadingEl.querySelector(".sub")!.textContent = "Compiling WebAssembly...";
    const wasmBytes = await response.arrayBuffer();
    const result = await WebAssembly.instantiate(wasmBytes, imports);

    doomExports = result.instance.exports;
    doomMemory = doomExports.memory as WebAssembly.Memory;

    loadingEl.querySelector(".sub")!.textContent = "Starting DOOM...";
    doomExports.initGame();

    function gameLoop() {
      doomExports.tickGame();
      requestAnimationFrame(gameLoop);
    }
    requestAnimationFrame(gameLoop);

    console.log("DOOM initialized successfully");
  } catch (err: any) {
    loadingEl.innerHTML = `ERROR<br><span class="sub">${err.message}</span>`;
    console.error("Failed to load DOOM:", err);
  }
}

startDoom();
