from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from libs.core.schema import Observation
from pathlib import Path
import asyncio, json, os
from datetime import datetime

DATA_DIR = Path(os.environ.get("DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
OBS_FILE = DATA_DIR / "observations.jsonl"

app = FastAPI(title="RF Mapper - Phase 0 Gateway")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Templates for live web interface
templates = Jinja2Templates(directory="services/gateway/templates")

class WSManager:
    def __init__(self):
        self.active = []
        self.lock = asyncio.Lock()
    
    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self.lock:
            self.active.append(ws)
    
    async def disconnect(self, ws: WebSocket):
        async with self.lock:
            if ws in self.active:
                self.active.remove(ws)
    
    async def broadcast(self, message: str):
        async with self.lock:
            dead = []
            for ws in self.active:
                try:
                    await ws.send_text(message)
                except:
                    dead.append(ws)
            for ws in dead:
                if ws in self.active:
                    self.active.remove(ws)

manager = WSManager()

@app.get("/")
def root():
    return RedirectResponse(url="/live/")

@app.get("/health")
def health(): return {"ok": True, "time": datetime.utcnow().isoformat()}

@app.post("/observation")
async def ingest_observation(obs: Observation):
    with OBS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obs.model_dump()) + "\n")
    await manager.broadcast(json.dumps({"type":"observation","data":obs.model_dump()}))
    return {"status":"ok","id":obs.id}

@app.get("/observations")
def get_observations(limit: int = Query(500, ge=1, le=5000)):
    if not OBS_FILE.exists(): 
        return []
    # read last N lines
    lines = []
    with OBS_FILE.open("rb") as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        block = 1024
        data = b""
        while len(lines) <= limit and size > 0:
            step = min(block, size)
            size -= step
            f.seek(size)
            data = f.read(step) + data
            lines = data.splitlines()
    out = []
    for line in lines[-limit:]:
        try:
            out.append(json.loads(line.decode("utf-8")))
        except:
            pass
    return out

@app.get("/live/", response_class=HTMLResponse)
async def live_map(request: Request):
    return templates.TemplateResponse("live_map.html", {"request": request})

@app.websocket("/stream")
async def ws_stream(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(ws)
    except Exception:
        await manager.disconnect(ws)
