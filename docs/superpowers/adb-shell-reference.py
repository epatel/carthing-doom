"""
adb-shell Python Library Reference
===================================
Library: adb-shell 0.4.4 (PyPI)
License: Apache 2.0
GitHub: https://github.com/JeffLIrion/adb_shell
Docs: https://adb-shell.readthedocs.io/

KEY FACT: adb-shell is a pure Python ADB implementation.
It does NOT require the `adb` binary. It speaks the ADB protocol
directly over TCP or USB.

Installation:
    pip install adb-shell          # TCP only
    pip install adb-shell[usb]     # + USB support (libusb via usb1)
    pip install adb-shell[async]   # + async support (Python 3.7+)
"""

# ============================================================
# 1. IMPORTS
# ============================================================
from adb_shell.adb_device import AdbDeviceTcp, AdbDeviceUsb
from adb_shell.auth.sign_pythonrsa import PythonRSASigner
from adb_shell.auth.keygen import keygen


# ============================================================
# 2. GENERATE ADB KEYS (one-time setup)
# ============================================================
def generate_keys(path="~/.android/adbkey"):
    """Generate RSA key pair for ADB authentication."""
    import os
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        keygen(path)  # creates path and path.pub


# ============================================================
# 3. LOAD KEYS & CREATE SIGNER
# ============================================================
def make_signer(adbkey_path="~/.android/adbkey"):
    import os
    adbkey = os.path.expanduser(adbkey_path)
    with open(adbkey) as f:
        priv = f.read()
    with open(adbkey + ".pub") as f:
        pub = f.read()
    return PythonRSASigner(pub, priv)


# ============================================================
# 4. CONNECT VIA TCP (e.g., WiFi ADB or forwarded port)
# ============================================================
def connect_tcp(host, port=5555, timeout=9.0):
    signer = make_signer()
    device = AdbDeviceTcp(host, port, default_transport_timeout_s=timeout)
    device.connect(rsa_keys=[signer], auth_timeout_s=0.1)
    return device


# ============================================================
# 5. CONNECT VIA USB (requires pip install adb-shell[usb])
# ============================================================
def connect_usb(serial=None):
    """Connect to USB device. serial=None connects to first available."""
    signer = make_signer()
    device = AdbDeviceUsb(serial=serial)
    device.connect(rsa_keys=[signer], auth_timeout_s=0.1)
    return device


# ============================================================
# 6. CHECK CONNECTION STATUS
# ============================================================
def is_connected(device):
    """device.available is a bool property: True if connected."""
    return device.available


# ============================================================
# 7. RUN SHELL COMMANDS
# ============================================================
def run_shell(device, cmd):
    """Run a shell command, return output as string."""
    return device.shell(cmd)
    # Examples:
    #   device.shell("echo hello")       -> "hello\n"
    #   device.shell("getprop ro.build.display.id")
    #   device.shell("ls /tmp")
    #   device.shell("ps aux")


def run_shell_streaming(device, cmd):
    """Stream output line-by-line (generator)."""
    for line in device.streaming_shell(cmd):
        yield line


# ============================================================
# 8. PUSH FILES TO DEVICE
# ============================================================
def push_file(device, local_path, device_path, progress=None):
    """
    Push a local file to device.
    local_path: str or BytesIO
    device_path: str (destination path on device)
    progress: callback(device_path, bytes_written, total_bytes)
    """
    device.push(local_path, device_path, progress_callback=progress)


def push_bytes(device, data: bytes, device_path: str):
    """Push raw bytes to a file on the device."""
    from io import BytesIO
    stream = BytesIO(data)
    device.push(stream, device_path)


# ============================================================
# 9. PULL FILES FROM DEVICE
# ============================================================
def pull_file(device, device_path, local_path):
    """Pull a file from device to local filesystem."""
    device.pull(device_path, local_path)


def pull_to_bytes(device, device_path) -> bytes:
    """Pull a file into memory."""
    from io import BytesIO
    stream = BytesIO()
    device.pull(device_path, stream)
    stream.seek(0)
    return stream.read()


# ============================================================
# 10. LIST / STAT FILES ON DEVICE
# ============================================================
def list_dir(device, device_path):
    """List files in a directory on the device.
    Returns list of DeviceFile(filename, mode, size, mtime)."""
    return device.list(device_path)


def stat_file(device, device_path):
    """Stat a file. Returns (mode, size, mtime)."""
    return device.stat(device_path)


# ============================================================
# 11. OTHER DEVICE OPERATIONS
# ============================================================
def reboot_device(device):
    device.reboot()

def root_device(device):
    """Restart adbd as root (device must be rooted)."""
    device.root()


# ============================================================
# 12. DEVICE DETECTION (USB)
#     adb-shell does NOT have a built-in "list devices" command.
#     For USB discovery, use the usb1/libusb layer directly.
# ============================================================
def find_usb_devices():
    """
    Find ADB-capable USB devices using libusb.
    Requires: pip install adb-shell[usb]

    ADB USB devices have:
      interface class 0xFF, subclass 0x42, protocol 0x01
    """
    try:
        import usb1
    except ImportError:
        raise ImportError("Install with: pip install adb-shell[usb]")

    ADB_CLASS = 0xFF
    ADB_SUBCLASS = 0x42
    ADB_PROTOCOL = 0x01

    devices = []
    with usb1.USBContext() as ctx:
        for usb_device in ctx.getDeviceList(skip_on_error=True):
            for setting in usb_device.iterSettings():
                if (setting.getClass() == ADB_CLASS and
                    setting.getSubClass() == ADB_SUBCLASS and
                    setting.getProtocol() == ADB_PROTOCOL):
                    devices.append({
                        "serial": usb_device.getSerialNumber(),
                        "vendor_id": hex(usb_device.getVendorID()),
                        "product_id": hex(usb_device.getProductID()),
                    })
                    break
    return devices


# ============================================================
# 13. LAUNCHING CHROMIUM / URLs ON CAR THING
#     The Car Thing runs a custom Linux, not standard Android.
#     These are the common approaches:
# ============================================================

# --- Standard Android (for reference) ---
ANDROID_LAUNCH_URL = 'am start -a android.intent.action.VIEW -d "{url}"'
ANDROID_LAUNCH_CHROME = 'am start -n com.android.chrome/com.google.android.apps.chrome.Main -d "{url}"'

# --- Car Thing / Custom Linux with Chromium ---
# Chromium in kiosk mode (typical for embedded devices):
CHROMIUM_KIOSK = (
    'chromium-browser --kiosk --no-first-run --disable-infobars '
    '--disable-session-crashed-bubble --noerrdialogs '
    '--disable-translate --disable-features=TranslateUI '
    '--window-size=800,480 --window-position=0,0 '
    '"{url}"'
)

# Kill existing Chromium and relaunch:
CHROMIUM_RESTART = (
    'killall chromium-browser 2>/dev/null; sleep 0.5; '
    'DISPLAY=:0 chromium-browser --kiosk --no-first-run '
    '--disable-infobars "{url}" &'
)

# Navigate existing Chromium via remote debugging:
# (If Chromium was started with --remote-debugging-port=9222)
CHROMIUM_NAVIGATE_VIA_DEVTOOLS = (
    "curl -s http://localhost:9222/json/list | "
    "python3 -c \"import sys,json; t=json.load(sys.stdin); "
    "print(t[0]['webSocketDebuggerUrl'] if t else 'none')\""
)

# Check what's running:
CHECK_PROCESSES = "ps aux | grep -i chrom"
CHECK_DISPLAY = "echo $DISPLAY"
CHECK_FRAMEBUFFER = "cat /proc/fb"

# For Car Thing specifically, the webapp is typically served locally:
# device.shell("curl -s http://localhost:8080/health")
# device.shell("cat /etc/superbird/version")  # Check Car Thing version


# ============================================================
# 14. COMPLETE USAGE EXAMPLE
# ============================================================
def example_car_thing_workflow():
    """Full workflow for Car Thing communication."""

    # Connect (USB is most common for Car Thing)
    signer = make_signer()

    # Try USB first
    try:
        device = AdbDeviceUsb()
        device.connect(rsa_keys=[signer], auth_timeout_s=0.1)
    except Exception:
        # Fall back to TCP if USB fails
        device = AdbDeviceTcp("192.168.7.2", 5555)  # Common Car Thing IP
        device.connect(rsa_keys=[signer], auth_timeout_s=0.1)

    if not device.available:
        raise ConnectionError("Failed to connect to Car Thing")

    # Check device info
    print(device.shell("uname -a"))
    print(device.shell("cat /etc/hostname"))

    # Push a web app
    device.push("./dist/index.html", "/usr/share/webapp/index.html")
    device.push("./dist/bundle.js", "/usr/share/webapp/bundle.js")

    # Restart Chromium with new content
    device.shell("killall chromium-browser 2>/dev/null")
    device.shell(
        "DISPLAY=:0 chromium-browser --kiosk --no-first-run "
        "--disable-infobars http://localhost:8080 &"
    )

    # Verify
    print(device.shell("ps aux | grep chromium"))

    return device
