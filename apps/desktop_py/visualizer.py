"""
Pydeck-based visualization for RF signal mapping and heatmaps.
"""
import pydeck as pdk
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List
import logging
from pathlib import Path

from libs.core import GeoPoint
from storage import LocalStorage

logger = logging.getLogger(__name__)

class RFVisualizer:
    """RF signal visualizer using pydeck for interactive maps."""
    
    def __init__(self, storage: LocalStorage):
        self.storage = storage
        self.default_view_state = pdk.ViewState(
            latitude=40.7128,  # Default to NYC
            longitude=-74.0060,
            zoom=12,
            pitch=0
        )
    
    def create_observation_map(self, 
                             radio_filter: Optional[str] = None,
                             hours_back: int = 24) -> pdk.Deck:
        """Create a map showing individual observations as scatter points."""
        
        # Get recent observations
        df = self.storage.get_observations(radio=radio_filter, limit=5000)
        
        if df.empty:
            logger.warning("No observations found for visualization")
            return self._create_empty_map()
        
        # Prepare data for visualization
        df['color'] = df['radio'].map({
            'wifi': [255, 100, 100, 160],  # Red for WiFi
            'ble': [100, 100, 255, 160]    # Blue for BLE
        })
        
        # Size based on RSSI (stronger signal = larger point)
        df['size'] = np.clip((df['rssi_dbm'] + 100) * 2, 10, 100)
        
        # Create scatter layer
        scatter_layer = pdk.Layer(
            "ScatterplotLayer",
            data=df,
            get_position=['observer_lon', 'observer_lat'],
            get_color='color',
            get_radius='size',
            radius_scale=1,
            radius_min_pixels=3,
            radius_max_pixels=50,
            pickable=True
        )
        
        # Auto-center view on data
        view_state = self._calculate_view_state(df, 'observer_lat', 'observer_lon')
        
        return pdk.Deck(
            layers=[scatter_layer],
            initial_view_state=view_state,
            tooltip={
                "html": "<b>Signal:</b> {signal_id}<br/>"
                       "<b>RSSI:</b> {rssi_dbm} dBm<br/>"
                       "<b>Radio:</b> {radio}<br/>"
                       "<b>Time:</b> {ts}",
                "style": {"backgroundColor": "steelblue", "color": "white"}
            }
        )
    
    def create_heatmap(self, 
                      radio_filter: Optional[str] = None,
                      grid_size: int = 100) -> pdk.Deck:
        """Create a heatmap showing signal density."""
        
        df = self.storage.get_observations(radio=radio_filter, limit=10000)
        
        if df.empty:
            return self._create_empty_map()
        
        # Weight by signal strength (convert RSSI to positive weight)
        df['weight'] = np.clip(df['rssi_dbm'] + 100, 1, 100)
        
        heatmap_layer = pdk.Layer(
            "HeatmapLayer",
            data=df,
            get_position=['observer_lon', 'observer_lat'],
            get_weight='weight',
            radius_pixels=grid_size,
            intensity=1,
            threshold=0.03,
            pickable=False
        )
        
        view_state = self._calculate_view_state(df, 'observer_lat', 'observer_lon')
        
        return pdk.Deck(
            layers=[heatmap_layer],
            initial_view_state=view_state
        )
    
    def create_transmitter_map(self) -> pdk.Deck:
        """Create a map showing estimated transmitter locations."""
        
        estimates = self.storage.get_location_estimates()
        
        if not estimates:
            logger.warning("No location estimates found")
            return self._create_empty_map()
        
        # Convert to DataFrame
        df = pd.DataFrame(estimates)
        
        # Color by radio type
        df['color'] = df.apply(lambda row: 
            [255, 100, 100, 200] if self._get_transmitter_radio(row['signal_id']) == 'wifi' 
            else [100, 100, 255, 200], axis=1)
        
        # Size by confidence
        df['size'] = df['confidence'].fillna(0.5) * 100
        
        scatter_layer = pdk.Layer(
            "ScatterplotLayer",
            data=df,
            get_position=['lon', 'lat'],
            get_color='color',
            get_radius='size',
            radius_scale=1,
            radius_min_pixels=10,
            radius_max_pixels=100,
            pickable=True
        )
        
        # Add uncertainty circles if available
        uncertainty_layer = None
        if 'uncertainty_radius_m' in df.columns:
            df_with_uncertainty = df[df['uncertainty_radius_m'].notna()]
            if not df_with_uncertainty.empty:
                uncertainty_layer = pdk.Layer(
                    "ScatterplotLayer",
                    data=df_with_uncertainty,
                    get_position=['lon', 'lat'],
                    get_radius='uncertainty_radius_m',
                    get_color=[100, 100, 100, 50],
                    radius_scale=1,
                    filled=False,
                    stroked=True,
                    line_width_min_pixels=2
                )
        
        layers = [scatter_layer]
        if uncertainty_layer:
            layers.append(uncertainty_layer)
        
        view_state = self._calculate_view_state(df, 'lat', 'lon')
        
        return pdk.Deck(
            layers=layers,
            initial_view_state=view_state,
            tooltip={
                "html": "<b>Signal:</b> {signal_id}<br/>"
                       "<b>Method:</b> {method}<br/>"
                       "<b>Confidence:</b> {confidence:.2f}<br/>"
                       "<b>Support:</b> {support_count} observations",
                "style": {"backgroundColor": "steelblue", "color": "white"}
            }
        )
    
    def create_3d_signal_map(self, radio_filter: Optional[str] = None) -> pdk.Deck:
        """Create a 3D visualization with signal strength as height."""
        
        df = self.storage.get_observations(radio=radio_filter, limit=5000)
        
        if df.empty:
            return self._create_empty_map()
        
        # Group by location and calculate average RSSI
        location_groups = df.groupby(['observer_lat', 'observer_lon']).agg({
            'rssi_dbm': ['mean', 'count'],
            'radio': 'first'
        }).reset_index()
        
        location_groups.columns = ['lat', 'lon', 'avg_rssi', 'count', 'radio']
        
        # Convert RSSI to positive height (stronger signal = taller)
        location_groups['height'] = np.clip((location_groups['avg_rssi'] + 100) * 10, 10, 500)
        
        # Color by radio type
        location_groups['color'] = location_groups['radio'].map({
            'wifi': [255, 100, 100, 200],
            'ble': [100, 100, 255, 200]
        })
        
        column_layer = pdk.Layer(
            "ColumnLayer",
            data=location_groups,
            get_position=['lon', 'lat'],
            get_elevation='height',
            get_color='color',
            radius=20,
            elevation_scale=1,
            pickable=True
        )
        
        view_state = self._calculate_view_state(location_groups, 'lat', 'lon')
        view_state.pitch = 45  # Tilt for 3D view
        
        return pdk.Deck(
            layers=[column_layer],
            initial_view_state=view_state,
            tooltip={
                "html": "<b>Location:</b> {lat:.6f}, {lon:.6f}<br/>"
                       "<b>Avg RSSI:</b> {avg_rssi:.1f} dBm<br/>"
                       "<b>Observations:</b> {count}",
                "style": {"backgroundColor": "steelblue", "color": "white"}
            }
        )
    
    def _calculate_view_state(self, df: pd.DataFrame, lat_col: str, lon_col: str) -> pdk.ViewState:
        """Calculate optimal view state for the given data."""
        if df.empty:
            return self.default_view_state
        
        lat_center = df[lat_col].mean()
        lon_center = df[lon_col].mean()
        
        # Calculate zoom based on data spread
        lat_range = df[lat_col].max() - df[lat_col].min()
        lon_range = df[lon_col].max() - df[lon_col].min()
        max_range = max(lat_range, lon_range)
        
        # Rough zoom calculation
        if max_range > 1:
            zoom = 8
        elif max_range > 0.1:
            zoom = 11
        elif max_range > 0.01:
            zoom = 14
        else:
            zoom = 16
        
        return pdk.ViewState(
            latitude=lat_center,
            longitude=lon_center,
            zoom=zoom,
            pitch=0
        )
    
    def _create_empty_map(self) -> pdk.Deck:
        """Create an empty map when no data is available."""
        return pdk.Deck(
            layers=[],
            initial_view_state=self.default_view_state
        )
    
    def _get_transmitter_radio(self, signal_id: str) -> str:
        """Get radio type for a transmitter signal ID."""
        transmitters = self.storage.get_transmitters()
        for t in transmitters:
            if t['signal_id'] == signal_id:
                return t['radio']
        return 'unknown'
    
    def export_html(self, deck: pdk.Deck, filename: str) -> str:
        """Export visualization to HTML file."""
        output_path = Path(filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        html_content = deck.to_html(as_string=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Visualization exported to {output_path}")
        return str(output_path)
