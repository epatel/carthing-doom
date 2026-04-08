#!/bin/bash
# Push Doom files to the Car Thing (run once, survives reboots)
# Usage: ./push-doom.sh

ADB="${ADB:-$HOME/Library/Android/sdk/platform-tools/adb}"

echo "[doom] Pushing Doom to Car Thing..."
$ADB shell "mkdir -p /var/doom" 2>/dev/null
$ADB push apps/doom/index.html /var/doom/
$ADB push apps/doom/host.js /var/doom/
$ADB push apps/doom/input.js /var/doom/
$ADB push apps/doom/doom.wasm /var/doom/
echo "[doom] Done! Run ./launch-doom.sh to play."
