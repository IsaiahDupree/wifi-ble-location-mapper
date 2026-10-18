from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Dict
from uuid import uuid4
from datetime import datetime, timezone

class GeoPoint(BaseModel):
    lat: float
    lon: float
    alt: Optional[float] = None
    accuracy_m: Optional[float] = None

class Observation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    ts: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    observer_id: str
    radio: Literal["wifi", "ble"]
    signal_id: str            # Wi-Fi BSSID or BLE MAC
    ssid: Optional[str] = None
    service_uuids: Optional[List[str]] = None
    freq_mhz: Optional[int] = None
    channel: Optional[int] = None
    rssi_dbm: int
    tx_power_dbm: Optional[int] = None
    observer_location: GeoPoint
    raw: Optional[Dict] = None
