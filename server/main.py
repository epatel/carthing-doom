import argparse
import os

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

    print("[carthing] Checking for Car Thing...")

    if not adb.check_device_connected():
        print("[carthing] No device found. Waiting up to 30s...")
        if not adb.wait_for_device(timeout=30):
            print("[carthing] ERROR: No Car Thing detected. Is it plugged in?")
            return False

    print("[carthing] Device connected!")

    if not adb.setup_reverse_port():
        print(f"[carthing] WARNING: Could not set up ADB reverse port forwarding.")
        print("[carthing] Server will start, but Car Thing may not be able to connect.")
    else:
        print(f"[carthing] ADB reverse port forwarding: device:{port} -> host:{port}")

    # Forward Chrome DevTools port for navigation
    if not adb.setup_devtools_forward():
        print("[carthing] WARNING: Could not forward DevTools port.")

    if not no_launch:
        print(f"[carthing] Navigating Car Thing to {app_name}...")
        if adb.navigate_browser(app_name):
            print(f"[carthing] Car Thing now showing: {app_name}")
        else:
            print("[carthing] WARNING: Could not navigate browser. Try manually.")

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
