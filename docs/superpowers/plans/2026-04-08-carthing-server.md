# Car Thing Minimal Server — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A minimal Python server that detects the Car Thing via ADB, serves web apps to its Chromium browser over USB networking, and provides WebSocket communication.

**Architecture:** FastAPI serves static files and WebSocket endpoints over the USB network interface (172.16.42.1:8080). An ADB manager handles device detection and browser launching. A CLI entry point orchestrates startup.

**Tech Stack:** Python 3.10+, FastAPI, uvicorn, subprocess (ADB via system `adb` binary)

---

## File Structure

```
server/
├── main.py              # CLI entry point, orchestration
├── adb_manager.py       # ADB device detection, shell commands, browser launch
├── server.py            # FastAPI app, static files, WebSocket
├── requirements.txt     # Python dependencies
└── tests/
    ├── test_adb_manager.py
    ├── test_server.py
    └── conftest.py
apps/
└── test/
    └── index.html       # Simple test page to verify serving works
```

---

### Task 1: Project Scaffolding

**Files:**
- Create: `server/requirements.txt`
- Create: `server/__init__.py`
- Create: `server/tests/__init__.py`
- Create: `server/tests/conftest.py`
- Create: `apps/test/index.html`

- [ ] **Step 1: Create requirements.txt**

```txt
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
websockets>=12.0
pytest>=8.0.0
httpx>=0.27.0
pytest-asyncio>=0.23.0
```

- [ ] **Step 2: Create empty __init__.py files**

Create empty files at `server/__init__.py` and `server/tests/__init__.py`.

- [ ] **Step 3: Create test conftest.py**

```python
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_apps_dir(tmp_path):
    """Create a temporary apps directory with a test page."""
    app_dir = tmp_path / "test"
    app_dir.mkdir()
    index = app_dir / "index.html"
    index.write_text("<html><body><h1>Test App</h1></body></html>")
    return tmp_path


@pytest.fixture
def client(test_apps_dir):
    """Create a FastAPI test client with temporary apps directory."""
    from server.server import create_app

    app = create_app(apps_dir=str(test_apps_dir))
    return TestClient(app)
```

- [ ] **Step 4: Create test page**

Create `apps/test/index.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Car Thing Test</title>
    <style>
        body {
            margin: 0;
            background: #1a1a2e;
            color: #eee;
            font-family: monospace;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            width: 800px;
        }
        .info { text-align: center; }
        h1 { font-size: 48px; color: #0f0; }
        p { font-size: 24px; }
        #events { font-size: 16px; color: #0ff; min-height: 100px; }
    </style>
</head>
<body>
    <div class="info">
        <h1>Car Thing Server</h1>
        <p>Server is working!</p>
        <p>Press buttons or turn dial:</p>
        <div id="events"></div>
    </div>
    <script>
        const eventsDiv = document.getElementById('events');
        function log(msg) {
            eventsDiv.textContent = msg + '\n' + eventsDiv.textContent;
            if (eventsDiv.textContent.length > 500) {
                eventsDiv.textContent = eventsDiv.textContent.slice(0, 500);
            }
        }
        document.addEventListener('keydown', e => log('KEY: ' + e.code));
        document.addEventListener('wheel', e => log('WHEEL: dx=' + e.deltaX + ' dy=' + e.deltaY));
    </script>
</body>
</html>
```

- [ ] **Step 5: Install dependencies**

Run: `cd server && pip install -r requirements.txt`

- [ ] **Step 6: Commit**

```bash
git add server/requirements.txt server/__init__.py server/tests/__init__.py server/tests/conftest.py apps/test/index.html
git commit -m "feat: scaffold server project with dependencies and test page"
```

---

### Task 2: FastAPI Static File Server + WebSocket

**Files:**
- Create: `server/server.py`
- Create: `server/tests/test_server.py`

- [ ] **Step 1: Write failing tests for HTTP server**

Create `server/tests/test_server.py`:

```python
import pytest


def test_serves_app_index(client):
    response = client.get("/test/")
    assert response.status_code == 200
    assert "Test App" in response.text


def test_serves_app_index_without_trailing_slash(client):
    response = client.get("/test")
    assert response.status_code in (200, 307)


def test_root_redirects_or_lists(client):
    response = client.get("/")
    assert response.status_code == 200


def test_missing_app_returns_404(client):
    response = client.get("/nonexistent/")
    assert response.status_code == 404


def test_websocket_echo(client):
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "ping", "data": {}})
        response = ws.receive_json()
        assert response["type"] == "pong"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/epatel/Development/claude/carthing && python -m pytest server/tests/test_server.py -v`

Expected: FAIL — `server.server` module does not exist.

- [ ] **Step 3: Implement server.py**

Create `server/server.py`:

```python
import json
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles


def create_app(apps_dir: str = "apps", host: str = "0.0.0.0", port: int = 8080) -> FastAPI:
    app = FastAPI(title="Car Thing Server")
    app.state.host = host
    app.state.port = port
    app.state.apps_dir = apps_dir
    app.state.ws_clients: list[WebSocket] = []

    @app.get("/")
    async def root():
        apps = []
        if os.path.isdir(apps_dir):
            for name in sorted(os.listdir(apps_dir)):
                app_path = os.path.join(apps_dir, name)
                if os.path.isdir(app_path) and os.path.exists(os.path.join(app_path, "index.html")):
                    apps.append(name)
        return JSONResponse({"apps": apps})

    @app.get("/{app_name}/{file_path:path}")
    async def serve_app_file(app_name: str, file_path: str = ""):
        if not file_path or file_path.endswith("/"):
            file_path = "index.html"

        full_path = os.path.join(apps_dir, app_name, file_path)
        # Prevent directory traversal
        real_path = os.path.realpath(full_path)
        real_apps = os.path.realpath(apps_dir)
        if not real_path.startswith(real_apps):
            return JSONResponse({"error": "forbidden"}, status_code=403)

        if not os.path.isfile(full_path):
            return JSONResponse({"error": "not found"}, status_code=404)

        content_types = {
            ".html": "text/html",
            ".js": "application/javascript",
            ".css": "text/css",
            ".wasm": "application/wasm",
            ".json": "application/json",
            ".wad": "application/octet-stream",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
        }
        ext = os.path.splitext(file_path)[1].lower()
        content_type = content_types.get(ext, "application/octet-stream")

        with open(full_path, "rb") as f:
            content = f.read()

        return HTMLResponse(content=content, media_type=content_type)

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await ws.accept()
        app.state.ws_clients.append(ws)
        try:
            while True:
                data = await ws.receive_json()
                if data.get("type") == "ping":
                    await ws.send_json({"type": "pong", "data": {}})
                elif data.get("type") == "input":
                    # Broadcast input events to all other clients
                    for client in app.state.ws_clients:
                        if client != ws:
                            await client.send_json(data)
                else:
                    await ws.send_json({"type": "ack", "data": data})
        except WebSocketDisconnect:
            app.state.ws_clients.remove(ws)

    return app
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/epatel/Development/claude/carthing && python -m pytest server/tests/test_server.py -v`

Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add server/server.py server/tests/test_server.py
git commit -m "feat: add FastAPI server with static file serving and WebSocket"
```

---

### Task 3: ADB Manager

**Files:**
- Create: `server/adb_manager.py`
- Create: `server/tests/test_adb_manager.py`

- [ ] **Step 1: Write failing tests for ADB manager**

Create `server/tests/test_adb_manager.py`:

```python
import subprocess
from unittest.mock import patch, MagicMock

from server.adb_manager import AdbManager


class TestAdbManager:
    def test_init_sets_defaults(self):
        mgr = AdbManager()
        assert mgr.host_ip == "172.16.42.1"
        assert mgr.device_ip == "172.16.42.2"
        assert mgr.server_port == 8080

    def test_check_device_connected_returns_true(self):
        mgr = AdbManager()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="List of devices attached\n12345\tdevice\n"
            )
            assert mgr.check_device_connected() is True

    def test_check_device_connected_returns_false_when_no_device(self):
        mgr = AdbManager()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="List of devices attached\n\n"
            )
            assert mgr.check_device_connected() is False

    def test_check_device_connected_returns_false_on_error(self):
        mgr = AdbManager()
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("adb not found")
            assert mgr.check_device_connected() is False

    def test_shell_runs_command(self):
        mgr = AdbManager()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="OK\n")
            result = mgr.shell("echo OK")
            assert result == "OK\n"
            mock_run.assert_called_once_with(
                ["adb", "shell", "echo OK"],
                capture_output=True, text=True, timeout=30
            )

    def test_launch_browser_constructs_correct_command(self):
        mgr = AdbManager()
        with patch.object(mgr, "shell") as mock_shell:
            mock_shell.return_value = ""
            mgr.launch_browser("doom")
            mock_shell.assert_called_once()
            cmd = mock_shell.call_args[0][0]
            assert "chromium" in cmd.lower() or "browser" in cmd.lower()
            assert "172.16.42.1:8080/doom/" in cmd

    def test_check_network_returns_true(self):
        mgr = AdbManager()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert mgr.check_network() is True

    def test_check_network_returns_false(self):
        mgr = AdbManager()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            assert mgr.check_network() is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/epatel/Development/claude/carthing && python -m pytest server/tests/test_adb_manager.py -v`

Expected: FAIL — `server.adb_manager` module does not exist.

- [ ] **Step 3: Implement adb_manager.py**

Create `server/adb_manager.py`:

```python
import subprocess
import sys


class AdbManager:
    def __init__(
        self,
        host_ip: str = "172.16.42.1",
        device_ip: str = "172.16.42.2",
        server_port: int = 8080,
    ):
        self.host_ip = host_ip
        self.device_ip = device_ip
        self.server_port = server_port

    def check_device_connected(self) -> bool:
        """Check if any ADB device is connected."""
        try:
            result = subprocess.run(
                ["adb", "devices"],
                capture_output=True, text=True, timeout=10,
            )
            lines = result.stdout.strip().split("\n")
            # First line is "List of devices attached", remaining are devices
            devices = [l for l in lines[1:] if l.strip() and "device" in l]
            return len(devices) > 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def shell(self, command: str) -> str:
        """Run a shell command on the device via ADB."""
        result = subprocess.run(
            ["adb", "shell", command],
            capture_output=True, text=True, timeout=30,
        )
        return result.stdout

    def check_network(self) -> bool:
        """Check if the USB network to the Car Thing is up."""
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "2", self.device_ip],
                capture_output=True, text=True, timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def launch_browser(self, app_name: str = "test") -> None:
        """Launch Chromium on the Car Thing pointing to our server."""
        url = f"http://{self.host_ip}:{self.server_port}/{app_name}/"
        # Kill any existing Chromium instances first
        self.shell("pkill -f chromium || true")
        # Launch Chromium in kiosk mode
        cmd = (
            f"chromium-browser"
            f" --kiosk"
            f" --no-first-run"
            f" --disable-infobars"
            f" --disable-session-crashed-bubble"
            f" --noerrdialogs"
            f" --disable-translate"
            f" --window-size=800,480"
            f" --window-position=0,0"
            f" '{url}'"
            f" &"
        )
        self.shell(cmd)

    def wait_for_device(self, timeout: int = 30) -> bool:
        """Wait for a device to be connected."""
        import time

        start = time.time()
        while time.time() - start < timeout:
            if self.check_device_connected():
                return True
            time.sleep(1)
        return False

    def get_device_info(self) -> dict:
        """Get basic device information."""
        info = {}
        try:
            info["model"] = self.shell("getprop ro.product.model").strip()
            info["android_version"] = self.shell("getprop ro.build.version.release").strip()
            info["ip"] = self.device_ip
        except Exception:
            pass
        return info
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/epatel/Development/claude/carthing && python -m pytest server/tests/test_adb_manager.py -v`

Expected: All 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add server/adb_manager.py server/tests/test_adb_manager.py
git commit -m "feat: add ADB manager for device detection and browser launch"
```

---

### Task 4: CLI Entry Point

**Files:**
- Create: `server/main.py`
- Create: `server/tests/test_main.py`

- [ ] **Step 1: Write failing tests for CLI**

Create `server/tests/test_main.py`:

```python
from unittest.mock import patch, MagicMock

from server.main import startup


def test_startup_aborts_when_no_device():
    with patch("server.main.AdbManager") as MockAdb:
        mock_mgr = MockAdb.return_value
        mock_mgr.check_device_connected.return_value = False
        mock_mgr.wait_for_device.return_value = False

        result = startup(app_name="test", no_launch=True)
        assert result is False


def test_startup_succeeds_with_device_and_network():
    with patch("server.main.AdbManager") as MockAdb, \
         patch("server.main.run_server") as mock_run:
        mock_mgr = MockAdb.return_value
        mock_mgr.check_device_connected.return_value = True
        mock_mgr.check_network.return_value = True

        startup(app_name="test", no_launch=False)

        mock_mgr.launch_browser.assert_called_once_with("test")
        mock_run.assert_called_once()


def test_startup_skips_browser_when_no_launch():
    with patch("server.main.AdbManager") as MockAdb, \
         patch("server.main.run_server") as mock_run:
        mock_mgr = MockAdb.return_value
        mock_mgr.check_device_connected.return_value = True
        mock_mgr.check_network.return_value = True

        startup(app_name="doom", no_launch=True)

        mock_mgr.launch_browser.assert_not_called()
        mock_run.assert_called_once()


def test_startup_warns_when_no_network():
    with patch("server.main.AdbManager") as MockAdb, \
         patch("server.main.run_server") as mock_run, \
         patch("builtins.print") as mock_print:
        mock_mgr = MockAdb.return_value
        mock_mgr.check_device_connected.return_value = True
        mock_mgr.check_network.return_value = False

        startup(app_name="test", no_launch=True)

        # Should still start server even without network
        mock_run.assert_called_once()
        # Should print a warning
        calls = [str(c) for c in mock_print.call_args_list]
        assert any("network" in c.lower() or "warning" in c.lower() for c in calls)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/epatel/Development/claude/carthing && python -m pytest server/tests/test_main.py -v`

Expected: FAIL — `server.main` module does not exist.

- [ ] **Step 3: Implement main.py**

Create `server/main.py`:

```python
import argparse
import os
import sys

import uvicorn

from server.adb_manager import AdbManager
from server.server import create_app


def run_server(host: str, port: int, apps_dir: str) -> None:
    app = create_app(apps_dir=apps_dir, host=host, port=port)
    uvicorn.run(app, host=host, port=port, log_level="info")


def startup(
    app_name: str = "test",
    host: str = "0.0.0.0",
    port: int = 8080,
    no_launch: bool = False,
    apps_dir: str = "apps",
) -> bool:
    adb = AdbManager(server_port=port)

    print(f"[carthing] Checking for Car Thing...")

    if not adb.check_device_connected():
        print("[carthing] No device found. Waiting up to 30s...")
        if not adb.wait_for_device(timeout=30):
            print("[carthing] ERROR: No Car Thing detected. Is it plugged in?")
            return False

    print("[carthing] Device connected!")

    if not adb.check_network():
        print(f"[carthing] WARNING: Network to {adb.device_ip} not reachable.")
        print("[carthing] Server will start, but Car Thing may not be able to connect.")
        print("[carthing] Check USB network gadget configuration.")

    if not no_launch:
        print(f"[carthing] Launching {app_name} on Car Thing...")
        adb.launch_browser(app_name)

    print(f"[carthing] Starting server on {host}:{port}")
    print(f"[carthing] Serving apps from: {os.path.abspath(apps_dir)}")
    run_server(host=host, port=port, apps_dir=apps_dir)
    return True


def main():
    parser = argparse.ArgumentParser(description="Car Thing Minimal Server")
    parser.add_argument("--app", default="test", help="App to launch (directory name in apps/)")
    parser.add_argument("--host", default="0.0.0.0", help="Server bind address")
    parser.add_argument("--port", type=int, default=8080, help="Server port")
    parser.add_argument("--no-launch", action="store_true", help="Don't launch browser on device")
    parser.add_argument("--apps-dir", default="apps", help="Directory containing apps")
    args = parser.parse_args()

    startup(
        app_name=args.app,
        host=args.host,
        port=args.port,
        no_launch=args.no_launch,
        apps_dir=args.apps_dir,
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/epatel/Development/claude/carthing && python -m pytest server/tests/test_main.py -v`

Expected: All 4 tests PASS.

- [ ] **Step 5: Run all server tests together**

Run: `cd /Users/epatel/Development/claude/carthing && python -m pytest server/tests/ -v`

Expected: All 16 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add server/main.py server/tests/test_main.py
git commit -m "feat: add CLI entry point with device detection and server startup"
```

---

### Task 5: Integration Smoke Test

**Files:**
- None created — manual verification

- [ ] **Step 1: Start the server without a device (verify graceful handling)**

Run: `cd /Users/epatel/Development/claude/carthing && python -m server.main --no-launch --app test`

Expected: Should print "Checking for Car Thing..." and either detect it or timeout with a clear error.

- [ ] **Step 2: Start the server with --no-launch and test HTTP**

If a device is connected or to test just the HTTP server, use `--host 127.0.0.1`:

Run: `cd /Users/epatel/Development/claude/carthing && python -m server.main --no-launch --host 127.0.0.1 --app test &`

Then: `curl http://127.0.0.1:8080/test/`

Expected: Returns the test HTML page content with "Car Thing Server".

Kill server: `kill %1`

- [ ] **Step 3: Commit any fixes**

If any fixes were needed during smoke testing:

```bash
git add -u
git commit -m "fix: address issues found during integration smoke test"
```
