"""
FastAPI gateway with REST endpoints and WebSocket streaming.
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
import json
import logging
from datetime import datetime
import asyncio

from libs.core import Observation, Transmitter, LocationEstimate
from storage import LocalStorage

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections for real-time streaming."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        if not self.active_connections:
            return
            
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send message to WebSocket: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

# Initialize FastAPI app
app = FastAPI(title="RF Mapper Gateway", version="0.1.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize storage and connection manager
storage = LocalStorage()
manager = ConnectionManager()

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "RF Mapper Gateway", "version": "0.1.0", "status": "running"}

@app.post("/observations")
async def create_observations(observations: List[Observation]):
    """Store new observations."""
    try:
        storage.store_observations(observations)
        
        # Broadcast to WebSocket clients
        await manager.broadcast({
            "type": "observations",
            "data": [obs.model_dump() for obs in observations],
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return {"message": f"Stored {len(observations)} observations", "count": len(observations)}
    except Exception as e:
        logger.error(f"Failed to store observations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/observations")
async def get_observations(
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    radio: Optional[str] = Query(None, description="Radio type (wifi/ble)"),
    signal_id: Optional[str] = Query(None, description="Signal ID filter"),
    limit: Optional[int] = Query(1000, description="Maximum number of results")
):
    """Retrieve observations with optional filtering."""
    try:
        df = storage.get_observations(start_date, end_date, radio, signal_id, limit)
        return {
            "observations": df.to_dict('records'),
            "count": len(df),
            "filters": {
                "start_date": start_date,
                "end_date": end_date,
                "radio": radio,
                "signal_id": signal_id,
                "limit": limit
            }
        }
    except Exception as e:
        logger.error(f"Failed to retrieve observations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/transmitters")
async def get_transmitters(radio: Optional[str] = Query(None, description="Radio type filter")):
    """Get all discovered transmitters."""
    try:
        transmitters = storage.get_transmitters(radio)
        return {
            "transmitters": transmitters,
            "count": len(transmitters),
            "radio_filter": radio
        }
    except Exception as e:
        logger.error(f"Failed to retrieve transmitters: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/transmitters/{signal_id}")
async def get_transmitter(signal_id: str):
    """Get specific transmitter details."""
    try:
        transmitters = storage.get_transmitters()
        transmitter = next((t for t in transmitters if t['signal_id'] == signal_id), None)
        
        if not transmitter:
            raise HTTPException(status_code=404, detail="Transmitter not found")
        
        # Get related observations
        df = storage.get_observations(signal_id=signal_id, limit=100)
        observations = df.to_dict('records') if not df.empty else []
        
        # Get location estimates
        estimates = storage.get_location_estimates(signal_id)
        
        return {
            "transmitter": transmitter,
            "recent_observations": observations,
            "location_estimates": estimates
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve transmitter {signal_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/estimates")
async def create_location_estimate(estimate: LocationEstimate):
    """Store a new location estimate."""
    try:
        storage.store_location_estimate(estimate)
        
        # Broadcast to WebSocket clients
        await manager.broadcast({
            "type": "location_estimate",
            "data": estimate.model_dump(),
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return {"message": "Location estimate stored", "estimate_id": estimate.id}
    except Exception as e:
        logger.error(f"Failed to store location estimate: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/estimates")
async def get_location_estimates(signal_id: Optional[str] = Query(None)):
    """Get location estimates."""
    try:
        estimates = storage.get_location_estimates(signal_id)
        return {
            "estimates": estimates,
            "count": len(estimates),
            "signal_id_filter": signal_id
        }
    except Exception as e:
        logger.error(f"Failed to retrieve location estimates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    """Get system statistics."""
    try:
        stats = storage.get_stats()
        stats["timestamp"] = datetime.utcnow().isoformat()
        return stats
    except Exception as e:
        logger.error(f"Failed to retrieve stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time data streaming."""
    await manager.connect(websocket)
    try:
        # Send initial stats
        stats = storage.get_stats()
        await websocket.send_json({
            "type": "stats",
            "data": stats,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep connection alive
        while True:
            # Wait for client messages (ping/pong, subscriptions, etc.)
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
                logger.debug(f"Received WebSocket message: {data}")
            except asyncio.TimeoutError:
                # Send periodic heartbeat
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.warning(f"WebSocket receive error: {e}")
                break
                
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
