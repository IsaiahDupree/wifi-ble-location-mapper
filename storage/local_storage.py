"""
Local storage implementation using Parquet and SQLite.
"""
import sqlite3
import pandas as pd
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from libs.core import Observation, Transmitter, LocationEstimate, ScanSession

logger = logging.getLogger(__name__)

class LocalStorage:
    """Local storage manager using Parquet for observations and SQLite for indices."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # File paths
        self.observations_dir = self.data_dir / "observations"
        self.observations_dir.mkdir(exist_ok=True)
        self.db_path = self.data_dir / "rf_mapper.db"
        
        # Initialize SQLite database
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize SQLite database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS transmitters (
                    signal_id TEXT PRIMARY KEY,
                    radio TEXT NOT NULL,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    observation_count INTEGER DEFAULT 0,
                    label TEXT,
                    type TEXT,
                    avg_rssi_dbm REAL,
                    max_rssi_dbm INTEGER,
                    min_rssi_dbm INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS location_estimates (
                    id TEXT PRIMARY KEY,
                    signal_id TEXT NOT NULL,
                    method TEXT NOT NULL,
                    lat REAL NOT NULL,
                    lon REAL NOT NULL,
                    alt REAL,
                    uncertainty_radius_m REAL,
                    confidence REAL,
                    support_count INTEGER NOT NULL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    residual_error REAL,
                    geometric_dilution REAL,
                    FOREIGN KEY (signal_id) REFERENCES transmitters (signal_id)
                );
                
                CREATE TABLE IF NOT EXISTS scan_sessions (
                    id TEXT PRIMARY KEY,
                    observer_id TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    scan_mode TEXT DEFAULT 'walk_mapper',
                    notes TEXT,
                    total_observations INTEGER DEFAULT 0,
                    unique_signals INTEGER DEFAULT 0,
                    area_covered_m2 REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_transmitters_radio ON transmitters(radio);
                CREATE INDEX IF NOT EXISTS idx_transmitters_last_seen ON transmitters(last_seen);
                CREATE INDEX IF NOT EXISTS idx_estimates_signal_id ON location_estimates(signal_id);
                CREATE INDEX IF NOT EXISTS idx_estimates_updated_at ON location_estimates(updated_at);
            """)
    
    def store_observations(self, observations: List[Observation]) -> None:
        """Store observations in Parquet format partitioned by date."""
        if not observations:
            return
            
        # Convert to DataFrame
        obs_data = []
        for obs in observations:
            obs_dict = obs.model_dump()
            # Flatten nested GeoPoint
            location = obs_dict.pop('observer_location')
            obs_dict.update({
                'observer_lat': location['lat'],
                'observer_lon': location['lon'],
                'observer_alt': location.get('alt'),
                'observer_accuracy_m': location.get('accuracy_m')
            })
            obs_data.append(obs_dict)
        
        df = pd.DataFrame(obs_data)
        
        # Partition by date
        df['date'] = pd.to_datetime(df['ts']).dt.date
        
        for date, group in df.groupby('date'):
            date_dir = self.observations_dir / str(date)
            date_dir.mkdir(exist_ok=True)
            
            # Append to daily parquet file
            parquet_path = date_dir / f"observations_{date}.parquet"
            
            if parquet_path.exists():
                existing_df = pd.read_parquet(parquet_path)
                combined_df = pd.concat([existing_df, group], ignore_index=True)
                combined_df.to_parquet(parquet_path, index=False)
            else:
                group.to_parquet(parquet_path, index=False)
        
        logger.info(f"Stored {len(observations)} observations")
    
    def store_transmitter(self, transmitter: Transmitter) -> None:
        """Store or update transmitter information."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO transmitters 
                (signal_id, radio, first_seen, last_seen, observation_count, 
                 label, type, avg_rssi_dbm, max_rssi_dbm, min_rssi_dbm, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                transmitter.signal_id,
                transmitter.radio,
                transmitter.first_seen,
                transmitter.last_seen,
                transmitter.observation_count,
                transmitter.label,
                transmitter.type,
                transmitter.avg_rssi_dbm,
                transmitter.max_rssi_dbm,
                transmitter.min_rssi_dbm,
                datetime.utcnow().isoformat()
            ))
    
    def store_location_estimate(self, estimate: LocationEstimate) -> None:
        """Store location estimate."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO location_estimates
                (id, signal_id, method, lat, lon, alt, uncertainty_radius_m,
                 confidence, support_count, updated_at, residual_error, geometric_dilution)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                estimate.id,
                estimate.signal_id,
                estimate.method,
                estimate.estimated_location.lat,
                estimate.estimated_location.lon,
                estimate.estimated_location.alt,
                estimate.uncertainty_radius_m,
                estimate.confidence,
                estimate.support_count,
                estimate.updated_at,
                estimate.residual_error,
                estimate.geometric_dilution
            ))
    
    def get_observations(self, 
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None,
                        radio: Optional[str] = None,
                        signal_id: Optional[str] = None,
                        limit: Optional[int] = None) -> pd.DataFrame:
        """Retrieve observations with optional filtering."""
        
        # Find relevant parquet files
        parquet_files = []
        for date_dir in self.observations_dir.iterdir():
            if date_dir.is_dir():
                for parquet_file in date_dir.glob("*.parquet"):
                    parquet_files.append(parquet_file)
        
        if not parquet_files:
            return pd.DataFrame()
        
        # Read and combine parquet files
        dfs = []
        for file_path in parquet_files:
            try:
                df = pd.read_parquet(file_path)
                dfs.append(df)
            except Exception as e:
                logger.warning(f"Failed to read {file_path}: {e}")
        
        if not dfs:
            return pd.DataFrame()
        
        combined_df = pd.concat(dfs, ignore_index=True)
        
        # Apply filters
        if start_date:
            combined_df = combined_df[combined_df['ts'] >= start_date]
        if end_date:
            combined_df = combined_df[combined_df['ts'] <= end_date]
        if radio:
            combined_df = combined_df[combined_df['radio'] == radio]
        if signal_id:
            combined_df = combined_df[combined_df['signal_id'] == signal_id]
        
        # Apply limit
        if limit:
            combined_df = combined_df.head(limit)
        
        return combined_df
    
    def get_transmitters(self, radio: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all transmitters with optional radio filter."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = "SELECT * FROM transmitters"
            params = []
            
            if radio:
                query += " WHERE radio = ?"
                params.append(radio)
            
            query += " ORDER BY last_seen DESC"
            
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_location_estimates(self, signal_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get location estimates with optional signal filter."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = "SELECT * FROM location_estimates"
            params = []
            
            if signal_id:
                query += " WHERE signal_id = ?"
                params.append(signal_id)
            
            query += " ORDER BY updated_at DESC"
            
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_transmitters,
                    COUNT(CASE WHEN radio = 'wifi' THEN 1 END) as wifi_transmitters,
                    COUNT(CASE WHEN radio = 'ble' THEN 1 END) as ble_transmitters
                FROM transmitters
            """)
            transmitter_stats = cursor.fetchone()
            
            cursor = conn.execute("SELECT COUNT(*) FROM location_estimates")
            estimate_count = cursor.fetchone()[0]
        
        # Count observations from parquet files
        total_observations = 0
        for date_dir in self.observations_dir.iterdir():
            if date_dir.is_dir():
                for parquet_file in date_dir.glob("*.parquet"):
                    try:
                        df = pd.read_parquet(parquet_file)
                        total_observations += len(df)
                    except Exception:
                        pass
        
        return {
            "total_observations": total_observations,
            "total_transmitters": transmitter_stats[0],
            "wifi_transmitters": transmitter_stats[1],
            "ble_transmitters": transmitter_stats[2],
            "location_estimates": estimate_count
        }
