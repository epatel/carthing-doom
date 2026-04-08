import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse


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
