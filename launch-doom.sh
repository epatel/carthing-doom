#!/bin/bash
# Launch Doom on the Car Thing (files must already be pushed to /var/doom/)
# Usage: ./launch-doom.sh

ADB="${ADB:-$HOME/Library/Android/sdk/platform-tools/adb}"

echo "[doom] Checking for Car Thing..."
if ! $ADB devices 2>/dev/null | grep -q "device$"; then
    echo "[doom] ERROR: No Car Thing found. Is it plugged in?"
    exit 1
fi
echo "[doom] Device connected!"

# Forward Chrome DevTools port
$ADB forward tcp:2222 tcp:2222 >/dev/null 2>&1

echo "[doom] Navigating to Doom..."
python3 -c "
import asyncio, json, urllib.request, websockets

r = urllib.request.urlopen('http://127.0.0.1:2222/json')
pages = json.loads(r.read())
ws_url = pages[0]['webSocketDebuggerUrl']

async def nav():
    async with websockets.connect(ws_url) as ws:
        await ws.send(json.dumps({'id': 1, 'method': 'Page.navigate', 'params': {'url': 'file:///var/doom/index.html'}}))
        resp = json.loads(await ws.recv())
        if 'result' in resp:
            print('[doom] Doom launched! Controls:')
            print('  Dial rotate  = Turn / Menu navigate')
            print('  Dial press   = Shoot / Menu select')
            print('  Preset 1-4   = Forward / Back / Strafe L / Strafe R')
            print('  5th button   = Use / Open doors')
            print('  Back         = Doom menu')
        else:
            print('[doom] ERROR:', resp)

asyncio.run(nav())
"
