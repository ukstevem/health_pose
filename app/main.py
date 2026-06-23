"""FastAPI entry point.

Two channels to the browser:
  * /video_feed  -> MJPEG (annotated frames) for <img src=...>
  * /ws          -> WebSocket pushing live rep/form state as JSON

Localhost single-user PoC; no auth, no concurrency handling beyond one client.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .camera import pipeline

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="health_pose")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/video_feed")
def video_feed():
    return StreamingResponse(
        pipeline.frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.post("/reset")
def reset():
    pipeline.reset()
    return {"ok": True}


@app.post("/exercise/{name}")
def set_exercise(name: str):
    pipeline.set_exercise(name)
    return {"ok": True, "exercise": name}


@app.websocket("/ws")
async def ws(socket: WebSocket):
    await socket.accept()
    try:
        while True:
            await socket.send_json(pipeline.state())
            await asyncio.sleep(0.1)  # ~10 Hz
    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    # Convenience launcher: `python -m app.main`. Port defaults to 8077 to dodge
    # the common 8000 clash; override with HP_PORT / HP_HOST.
    import uvicorn

    uvicorn.run(
        app,
        host=os.environ.get("HP_HOST", "127.0.0.1"),
        port=int(os.environ.get("HP_PORT", "8077")),
    )
