# /backend/api_main.py (FULL WORKING VERSION WITH BINARY+TEXT FIX)

from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List
import json
import asyncio

from .data_schema import get_db, Hazard, HazardCreate

# Initialize FastAPI application
app = FastAPI(title="Hazard Detection Backend (60% Milestone: Live Stream)")

# --- WebSocket Connection Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"WS CONNECTED: Total active clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"WS DISCONNECTED: Total active clients: {len(self.active_connections)}")

manager = ConnectionManager()


# --- ASYNCHRONOUS DATABASE PERSISTENCE FUNCTION ---
async def persist_hazard_to_db(hazard: HazardCreate):
    """Creates a temporary session to save hazard data from the WebSocket."""
    db = next(get_db())
    try:
        db_hazard = Hazard(
            hazard_type=hazard.hazard_type,
            location_data=hazard.location_data,
            severity=hazard.severity
        )
        db.add(db_hazard)
        db.commit()
        db.refresh(db_hazard)
        print(f"WS HAZARD PERSISTED: Type={db_hazard.hazard_type}, ID={db_hazard.id}")
    except Exception as e:
        print(f"ERROR during WS persistence: {e}")
    finally:
        db.close()


# --- ✅ FIXED WEBSOCKET ENDPOINT: Handles BYTES + TEXT ---
@app.websocket("/ws/video")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        while True:

            # Receive ANY type of WebSocket message
            message = await websocket.receive()

            # --- 1. If message contains binary data (video frame)
            if "bytes" in message and message["bytes"] is not None:
                # For now, we just ignore video bytes on backend
                # FRONTEND directly uses these frames from detection script
                continue

            # --- 2. If message contains text (hazard JSON)
            if "text" in message and message["text"]:

                raw_text = message["text"]

                try:
                    hazard_json = json.loads(raw_text)

                    # Only process valid hazard objects
                    if "type" in hazard_json:
                        log_entry = HazardCreate(
                            hazard_type=hazard_json["type"],
                            location_data=f"Frame {hazard_json.get('frame_id', 'N/A')}",
                            severity=int(hazard_json["severity"])
                        )

                        await persist_hazard_to_db(log_entry)

                except json.JSONDecodeError:
                    # Ignore plain text or non-JSON messages
                    pass

    except WebSocketDisconnect:
        manager.disconnect(websocket)

    except Exception as e:
        print(f"WebSocket Error: {e}")
        manager.disconnect(websocket)


# --- REST API Endpoint (For manual testing) ---
@app.post("/log-hazard", status_code=201)
def log_hazard(hazard: HazardCreate, db: Session = Depends(get_db)):
    db_hazard = Hazard(
        hazard_type=hazard.hazard_type,
        location_data=hazard.location_data,
        severity=hazard.severity
    )
    db.add(db_hazard)
    db.commit()
    db.refresh(db_hazard)

    print(f"HAZARD LOGGED: Type={db_hazard.hazard_type}, ID={db_hazard.id}")
    return {"message": "Hazard successfully logged", "hazard_id": db_hazard.id}


# --- Health Check Endpoint ---
@app.get("/")
def read_root():
    return {"status": "Backend running", "milestone": "60% complete"}
