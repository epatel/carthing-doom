/**
 * Car Thing Input -> Doom Key Translation
 *
 * Verified hardware events (from test page):
 *   Buttons: keydown/keyup events
 *     - Preset 1: code "Digit1"
 *     - Preset 2: code "Digit2"
 *     - Preset 3: code "Digit3"
 *     - Preset 4: code "Digit4"
 *     - Home/Center: code "KeyM"
 *     - Back: code "Escape"
 *
 *   Dial: wheel events
 *     - Clockwise: deltaX = +53, deltaY = 0
 *     - Counter-clockwise: deltaX = -53, deltaY = 0
 *
 * Doom key exports from doom.wasm:
 *   KEY_UPARROW, KEY_DOWNARROW, KEY_LEFTARROW, KEY_RIGHTARROW
 *   KEY_FIRE, KEY_USE, KEY_ENTER, KEY_ESCAPE
 *   KEY_STRAFE_L, KEY_STRAFE_R, KEY_SHIFT, KEY_ALT, KEY_TAB
 */

(function () {
    "use strict";

    // Wait for doom exports to be available
    var exports = null;

    function getExports() {
        if (!exports && window.doomExports) {
            exports = window.doomExports;
        }
        return exports;
    }

    // --- Button Mapping ---
    // Verified key codes from Car Thing hardware test

    // Maps each Car Thing button to one or more Doom keys
    // Multiple keys allows a button to work in both menus and gameplay
    var BUTTON_MAP = {
        "Digit1": ["KEY_UPARROW"],           // Preset 1 = Forward / Menu up
        "Digit2": ["KEY_DOWNARROW"],         // Preset 2 = Backward / Menu down
        "Digit3": ["KEY_STRAFE_L"],          // Preset 3 = Strafe left
        "Digit4": ["KEY_STRAFE_R"],          // Preset 4 = Strafe right
        "KeyM":   ["KEY_USE"],               // 5th top button = Use/Open door
        "Enter":  ["KEY_FIRE", "KEY_ENTER"], // Dial press = Shoot + Menu select
        "Escape": ["KEY_ESCAPE"],            // Back = Doom menu
    };

    document.addEventListener("keydown", function (e) {
        var doomKeys = BUTTON_MAP[e.code];
        if (!doomKeys) return;

        e.preventDefault();
        e.stopPropagation();

        var ex = getExports();
        if (ex) {
            for (var i = 0; i < doomKeys.length; i++) {
                ex.reportKeyDown(ex[doomKeys[i]]);
            }
        }
    }, true);

    document.addEventListener("keyup", function (e) {
        var doomKeys = BUTTON_MAP[e.code];
        if (!doomKeys) return;

        e.preventDefault();
        e.stopPropagation();

        var ex = getExports();
        if (ex) {
            for (var i = 0; i < doomKeys.length; i++) {
                ex.reportKeyUp(ex[doomKeys[i]]);
            }
        }
    }, true);

    // --- Dial (Rotary Encoder) -> Turn Left/Right ---
    //
    // The Car Thing dial generates wheel events with deltaX:
    //   Clockwise: deltaX = +53 per detent
    //   Counter-clockwise: deltaX = -53 per detent
    //
    // Strategy:
    //   - Each wheel event presses the turn key
    //   - Key stays held until no events arrive for DIAL_RELEASE_MS
    //   - Fast spinning = continuous hold, slow ticks = brief taps
    //   - This gives smooth, natural turning from the physical dial

    var DIAL_RELEASE_MS = 80;  // Release turn key after this many ms of no events
    var dialDirection = 0;     // -1 = left, 0 = none, 1 = right
    var dialReleaseTimer = null;

    function dialRelease() {
        var ex = getExports();
        if (ex && dialDirection !== 0) {
            var key = dialDirection > 0 ? ex.KEY_RIGHTARROW : ex.KEY_LEFTARROW;
            ex.reportKeyUp(key);
        }
        dialDirection = 0;
        dialReleaseTimer = null;
    }

    document.addEventListener("wheel", function (e) {
        e.preventDefault();

        var ex = getExports();
        if (!ex) return;

        // Car Thing dial uses deltaX (horizontal scroll)
        var delta = e.deltaX;
        if (delta === 0) delta = e.deltaY;  // fallback
        if (delta === 0) return;

        var newDirection = delta > 0 ? 1 : -1;

        // If direction changed, release old turn key first
        if (dialDirection !== 0 && dialDirection !== newDirection) {
            var oldKey = dialDirection > 0 ? ex.KEY_RIGHTARROW : ex.KEY_LEFTARROW;
            ex.reportKeyUp(oldKey);
            dialDirection = 0;
        }

        // Press the turn key if not already held (for gameplay turning)
        if (dialDirection === 0) {
            var newKey = newDirection > 0 ? ex.KEY_RIGHTARROW : ex.KEY_LEFTARROW;
            ex.reportKeyDown(newKey);
            dialDirection = newDirection;
        }

        // Reset the release timer — key stays held while dial keeps moving
        if (dialReleaseTimer !== null) {
            clearTimeout(dialReleaseTimer);
        }
        dialReleaseTimer = setTimeout(dialRelease, DIAL_RELEASE_MS);

    }, { passive: false, capture: true });

    // --- Touchscreen: Run Toggle + Menu ---
    // Tap the canvas to toggle run mode (Shift key)
    // The menu button (top-right) calls window.doomMenuToggle() for Doom menu

    var running = false;
    var canvasEl = document.getElementById("doom-canvas");
    var runIndicator = document.getElementById("run-indicator");

    if (canvasEl) {
        canvasEl.addEventListener("touchstart", function (e) {
            // Ignore if touching the menu button area (top-right 50x50)
            var touch = e.touches[0];
            if (touch.clientX > 750 && touch.clientY < 50) return;

            e.preventDefault();
            var ex = getExports();
            if (!ex) return;

            running = !running;
            if (running) {
                ex.reportKeyDown(ex.KEY_SHIFT);
            } else {
                ex.reportKeyUp(ex.KEY_SHIFT);
            }

            if (runIndicator) {
                runIndicator.style.display = running ? "block" : "none";
            }
        }, { passive: false });
    }

    console.log("Car Thing input mapping loaded");
    console.log("Controls: Digit1=Forward, Digit2=Back, Digit3=StrafeL, Digit4=StrafeR");
    console.log("          KeyM(Home)=Shoot, Escape(Back)=Use, Dial=Turn");
    console.log("          Touch screen=Toggle Run, Menu btn=Doom menu");
})();
