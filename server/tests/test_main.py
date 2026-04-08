from unittest.mock import patch, MagicMock

from server.main import startup


def test_startup_aborts_when_no_device():
    with patch("server.main.AdbManager") as MockAdb:
        mock_mgr = MockAdb.return_value
        mock_mgr.check_device_connected.return_value = False
        mock_mgr.wait_for_device.return_value = False

        result = startup(app_name="test", no_launch=True)
        assert result is False


def test_startup_succeeds_and_navigates():
    with patch("server.main.AdbManager") as MockAdb, \
         patch("server.main.run_server") as mock_run:
        mock_mgr = MockAdb.return_value
        mock_mgr.check_device_connected.return_value = True
        mock_mgr.setup_reverse_port.return_value = True
        mock_mgr.setup_devtools_forward.return_value = True
        mock_mgr.navigate_browser.return_value = True

        startup(app_name="test", no_launch=False)

        mock_mgr.navigate_browser.assert_called_once_with("test")
        mock_run.assert_called_once()


def test_startup_skips_navigation_when_no_launch():
    with patch("server.main.AdbManager") as MockAdb, \
         patch("server.main.run_server") as mock_run:
        mock_mgr = MockAdb.return_value
        mock_mgr.check_device_connected.return_value = True
        mock_mgr.setup_reverse_port.return_value = True
        mock_mgr.setup_devtools_forward.return_value = True

        startup(app_name="doom", no_launch=True)

        mock_mgr.navigate_browser.assert_not_called()
        mock_run.assert_called_once()


def test_startup_warns_when_reverse_port_fails():
    with patch("server.main.AdbManager") as MockAdb, \
         patch("server.main.run_server") as mock_run, \
         patch("builtins.print") as mock_print:
        mock_mgr = MockAdb.return_value
        mock_mgr.check_device_connected.return_value = True
        mock_mgr.setup_reverse_port.return_value = False
        mock_mgr.setup_devtools_forward.return_value = True

        startup(app_name="test", no_launch=True)

        mock_run.assert_called_once()
        calls = [str(c) for c in mock_print.call_args_list]
        assert any("warning" in c.lower() or "reverse" in c.lower() for c in calls)
