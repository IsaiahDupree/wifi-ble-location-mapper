"""
Core data models for RF signal observations and location estimates.
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal, List
from datetime import datetime
import uuid

class GeoPoint(BaseModel):
    """Geographic point with optional altitude and accuracy."""
    lat: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    lon: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")
    alt: Optional[float] = Field(None, description="Altitude in meters")
    accuracy_m: Optional[float] = Field(None, description="GPS accuracy in meters")

class Observation(BaseModel):
    """A single RF signal observation with location and metadata."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ts: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    observer_id: str = Field(..., description="Unique ID of the scanning device")
    radio: Literal["wifi", "ble"] = Field(..., description="Radio type")
    signal_id: str = Field(..., description="Signal identifier (MAC, BSSID, etc.)")
    
    # WiFi specific
    ssid: Optional[str] = Field(None, description="WiFi network name")
    bssid: Optional[str] = Field(None, description="WiFi access point MAC")
    
    # BLE specific
    service_uuids: Optional[List[str]] = Field(None, description="BLE service UUIDs")
    device_name: Optional[str] = Field(None, description="BLE device name")
    
    # Signal properties
    freq_mhz: Optional[int] = Field(None, description="Frequency in MHz")
    channel: Optional[int] = Field(None, description="Channel number")
    rssi_dbm: int = Field(..., description="Received signal strength in dBm")
    tx_power_dbm: Optional[int] = Field(None, description="Transmit power in dBm")
    
    # Location context
    observer_location: GeoPoint = Field(..., description="Observer's location")
    observer_heading_deg: Optional[float] = Field(None, ge=0, le=360)
    speed_mps: Optional[float] = Field(None, ge=0, description="Observer speed in m/s")
    
    # Privacy and raw data
    privacy_hash_salt_id: Optional[str] = Field(None, description="Salt ID for MAC hashing")
    raw: Optional[dict] = Field(None, description="Raw scan data for advanced analysis")

class Transmitter(BaseModel):
    """A clustered signal source derived from observations."""
    signal_id: str = Field(..., description="Unique signal identifier")
    radio: Literal["wifi", "ble"]
    last_seen: str = Field(..., description="Last observation timestamp")
    first_seen: str = Field(..., description="First observation timestamp")
    observation_count: int = Field(default=0, description="Total observations")
    label: Optional[str] = Field(None, description="Human-readable label")
    type: Optional[str] = Field(None, description="Device type classification")
    
    # Aggregated signal properties
    avg_rssi_dbm: Optional[float] = None
    max_rssi_dbm: Optional[int] = None
    min_rssi_dbm: Optional[int] = None

class LocationEstimate(BaseModel):
    """Estimated location of a transmitter."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    signal_id: str = Field(..., description="Associated transmitter signal ID")
    method: str = Field(..., description="Estimation method used")
    
    # Location estimate
    estimated_location: GeoPoint = Field(..., description="Estimated transmitter location")
    uncertainty_radius_m: Optional[float] = Field(None, description="Uncertainty radius in meters")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="Confidence score 0-1")
    
    # Supporting data
    support_count: int = Field(..., description="Number of observations used")
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Quality metrics
    residual_error: Optional[float] = Field(None, description="RMS error of fit")
    geometric_dilution: Optional[float] = Field(None, description="GDOP metric")

class ScanSession(BaseModel):
    """A scanning session with metadata."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    observer_id: str
    start_time: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    end_time: Optional[str] = None
    scan_mode: Literal["walk_mapper", "fixed_node", "mobile"] = "walk_mapper"
    notes: Optional[str] = None
    
    # Session statistics
    total_observations: int = 0
    unique_signals: int = 0
    area_covered_m2: Optional[float] = None
