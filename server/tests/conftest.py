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
