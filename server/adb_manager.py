import json
import os
import subprocess
import time
import urllib.request

# ADB binary path — update if your adb is elsewhere
ADB_PATH = os.path.expanduser("~/Library/Android/sdk/platform-tools/adb")

# Chrome DevTools Protocol port on the Car Thing
DEVTOOLS_PORT = 2222


class AdbManager:
    def __init__(
        self,
        server_port: int = 8080,
        adb_path: str = ADB_PATH,
        devtools_port: int = DEVTOOLS_PORT,
    ):
        self.server_port = server_port
        self.adb_path = adb_path
        self.devtools_port = devtools_port

    def _adb(self, *args: str, timeout: int = 10) -> subprocess.CompletedProcess:
        """Run an adb command."""
        return subprocess.run(
            [self.adb_path, *args],
            capture_output=True, text=True, timeout=timeout,
        )

    def check_device_connected(self) -> bool:
        """Check if any ADB device is connected."""
        try:
            result = self._adb("devices")
            lines = result.stdout.strip().split("\n")
            devices = [l for l in lines[1:] if l.strip() and "device" in l]
            return len(devices) > 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def shell(self, command: str) -> str:
        """Run a shell command on the device via ADB."""
        result = self._adb("shell", command, timeout=30)
        return result.stdout

    def setup_reverse_port(self) -> bool:
        """Set up ADB reverse port forwarding so device can reach host server."""
        try:
            result = self._adb("reverse", f"tcp:{self.server_port}", f"tcp:{self.server_port}")
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def setup_devtools_forward(self) -> bool:
        """Forward Chrome DevTools port from device to host."""
        try:
            result = self._adb("forward", f"tcp:{self.devtools_port}", f"tcp:{self.devtools_port}")
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def navigate_browser(self, app_name: str = "test") -> bool:
        """Navigate the Car Thing's Chromium to our app via Chrome DevTools Protocol.

        The Car Thing runs Chromium under supervisord with --remote-debugging-port=2222.
        Instead of killing/relaunching (supervisord restarts it), we navigate the
        existing instance using the Chrome DevTools Protocol.
        """
        url = f"http://127.0.0.1:{self.server_port}/{app_name}/"
        try:
            # Get the debuggable page's WebSocket URL
            r = urllib.request.urlopen(f"http://127.0.0.1:{self.devtools_port}/json", timeout=5)
            pages = json.loads(r.read())
            if not pages:
                return False

            ws_url = pages[0].get("webSocketDebuggerUrl")
            if not ws_url:
                return False

            # Use asyncio + websockets to send navigate command
            import asyncio
            try:
                import websockets
            except ImportError:
                # Fallback: use the /json/navigate endpoint (simpler, no websockets needed)
                nav_url = f"http://127.0.0.1:{self.devtools_port}/json/navigate?{url}"
                urllib.request.urlopen(nav_url, timeout=5)
                return True

            async def _navigate():
                async with websockets.connect(ws_url) as ws:
                    await ws.send(json.dumps({
                        "id": 1,
                        "method": "Page.navigate",
                        "params": {"url": url}
                    }))
                    resp = json.loads(await ws.recv())
                    return "result" in resp

            return asyncio.run(_navigate())
        except Exception:
            return False

    def wait_for_device(self, timeout: int = 30) -> bool:
        """Wait for a device to be connected."""
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
            info["kernel"] = self.shell("uname -r").strip()
        except Exception:
            pass
        return info
