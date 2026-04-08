(async function () {
    const canvas = document.getElementById("doom-canvas");
    const ctx = canvas.getContext("2d");
    const loadingEl = document.getElementById("loading");
    const menuBtn = document.getElementById("menu-btn");

    var doomExports = null;
    var doomMemory = null;
    var screenWidth = 0;
    var screenHeight = 0;
    var imageData = null;
    var currentBuffer = null;

    // Helper: read a C string from WASM memory
    function readString(ptr, len) {
        if (!doomMemory) return "";
        return new TextDecoder().decode(new Uint8Array(doomMemory.buffer, ptr, len));
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
                var scaleX = 800 / width;
                var scaleY = 480 / height;
                var scale = Math.min(scaleX, scaleY);

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
                return Math.floor(performance.now());
            },
        },
        ui: {
            drawFrame(ptr) {
                if (!doomMemory || !imageData) return;
                // Get fresh view of memory buffer (may have grown/detached)
                var buf = doomMemory.buffer;
                var pixels = new Uint8Array(buf, ptr, screenWidth * screenHeight * 4);
                var data = imageData.data;
                for (var i = 0; i < screenWidth * screenHeight; i++) {
                    var src = i * 4;
                    var dst = i * 4;
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
        loadingEl.querySelector(".sub").textContent = "Downloading DOOM engine...";
        var response = await fetch("doom.wasm");
        loadingEl.querySelector(".sub").textContent = "Compiling WebAssembly...";
        var wasmBytes = await response.arrayBuffer();
        var result = await WebAssembly.instantiate(wasmBytes, imports);

        doomExports = result.instance.exports;
        doomMemory = doomExports.memory;

        // Expose exports for input.js
        window.doomExports = doomExports;

        // Menu toggle via touch button
        window.doomMenuToggle = function () {
            doomExports.reportKeyDown(doomExports.KEY_ESCAPE);
            setTimeout(function () { doomExports.reportKeyUp(doomExports.KEY_ESCAPE); }, 100);
        };

        // Initialize and start game loop
        loadingEl.querySelector(".sub").textContent = "Starting DOOM...";
        doomExports.initGame();

        function gameLoop() {
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
