import subprocess
from unittest.mock import patch, MagicMock

from server.adb_manager import AdbManager


class TestAdbManager:
    def test_init_sets_defaults(self):
        mgr = AdbManager()
        assert mgr.server_port == 8080
        assert "adb" in mgr.adb_path
        assert mgr.devtools_port == 2222

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
                [mgr.adb_path, "shell", "echo OK"],
                capture_output=True, text=True, timeout=30
            )

    def test_setup_reverse_port_returns_true(self):
        mgr = AdbManager()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert mgr.setup_reverse_port() is True

    def test_setup_reverse_port_returns_false_on_error(self):
        mgr = AdbManager()
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("adb not found")
            assert mgr.setup_reverse_port() is False

    def test_setup_devtools_forward_returns_true(self):
        mgr = AdbManager()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert mgr.setup_devtools_forward() is True

    def test_navigate_browser_returns_false_on_error(self):
        mgr = AdbManager()
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = Exception("connection refused")
            assert mgr.navigate_browser("doom") is False
