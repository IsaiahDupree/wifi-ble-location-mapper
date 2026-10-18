"""
Location estimation algorithms for RF signals.
"""
import numpy as np
import pandas as pd
from typing import List, Tuple, Optional, Dict, Any
from sklearn.cluster import DBSCAN
from scipy.optimize import least_squares
import logging

from libs.core import Observation, LocationEstimate, GeoPoint

logger = logging.getLogger(__name__)

class WalkMapperLocalizer:
    """Walk-mapper localization using clustering and weighted centroid."""
    
    def __init__(self, 
                 eps_meters: float = 50.0,
                 min_samples: int = 3,
                 rssi_weight_exp: float = 2.0):
        """
        Initialize walk-mapper localizer.
        
        Args:
            eps_meters: DBSCAN clustering radius in meters
            min_samples: Minimum samples for a cluster
            rssi_weight_exp: Exponent for RSSI-based weighting
        """
        self.eps_meters = eps_meters
        self.min_samples = min_samples
        self.rssi_weight_exp = rssi_weight_exp
    
    def estimate_location(self, observations: List[Observation]) -> Optional[LocationEstimate]:
        """
        Estimate transmitter location from walk-mapper observations.
        
        Args:
            observations: List of observations for the same signal
            
        Returns:
            LocationEstimate or None if insufficient data
        """
        if len(observations) < self.min_samples:
            logger.debug(f"Insufficient observations: {len(observations)} < {self.min_samples}")
            return None
        
        # Convert to DataFrame for easier processing
        obs_data = []
        for obs in observations:
            obs_data.append({
                'lat': obs.observer_location.lat,
                'lon': obs.observer_location.lon,
                'rssi_dbm': obs.rssi_dbm,
                'ts': obs.ts
            })
        
        df = pd.DataFrame(obs_data)
        
        # Convert to approximate meters for clustering
        coords_m = self._latlon_to_meters(df[['lat', 'lon']].values)
        
        # Cluster observations using DBSCAN
        clustering = DBSCAN(eps=self.eps_meters, min_samples=self.min_samples)
        cluster_labels = clustering.fit_predict(coords_m)
        
        # Find the largest cluster (most observations)
        unique_labels, counts = np.unique(cluster_labels[cluster_labels >= 0], return_counts=True)
        
        if len(unique_labels) == 0:
            logger.debug("No valid clusters found")
            return None
        
        # Use the largest cluster
        main_cluster_label = unique_labels[np.argmax(counts)]
        cluster_mask = cluster_labels == main_cluster_label
        cluster_df = df[cluster_mask].copy()
        
        if len(cluster_df) < self.min_samples:
            return None
        
        # Calculate weighted centroid
        estimated_location = self._calculate_weighted_centroid(cluster_df)
        
        # Calculate uncertainty
        uncertainty_radius = self._calculate_uncertainty(cluster_df, estimated_location)
        
        # Calculate confidence based on cluster quality
        confidence = self._calculate_confidence(cluster_df, len(observations))
        
        return LocationEstimate(
            signal_id=observations[0].signal_id,
            method="walk_mapper_clustering",
            estimated_location=estimated_location,
            uncertainty_radius_m=uncertainty_radius,
            confidence=confidence,
            support_count=len(cluster_df)
        )
    
    def _latlon_to_meters(self, coords: np.ndarray) -> np.ndarray:
        """
        Convert lat/lon coordinates to approximate meters.
        Uses simple equirectangular projection for local areas.
        """
        # Reference point (center of data)
        lat_center = np.mean(coords[:, 0])
        lon_center = np.mean(coords[:, 1])
        
        # Approximate meters per degree
        lat_m_per_deg = 111320.0  # meters per degree latitude
        lon_m_per_deg = 111320.0 * np.cos(np.radians(lat_center))  # varies with latitude
        
        # Convert to meters relative to center
        coords_m = np.zeros_like(coords)
        coords_m[:, 0] = (coords[:, 0] - lat_center) * lat_m_per_deg  # y (north)
        coords_m[:, 1] = (coords[:, 1] - lon_center) * lon_m_per_deg  # x (east)
        
        return coords_m
    
    def _calculate_weighted_centroid(self, cluster_df: pd.DataFrame) -> GeoPoint:
        """Calculate RSSI-weighted centroid of cluster."""
        # Convert RSSI to positive weights (stronger signal = higher weight)
        weights = np.power(cluster_df['rssi_dbm'] + 100, self.rssi_weight_exp)
        weights = np.clip(weights, 0.1, None)  # Avoid zero weights
        
        # Calculate weighted average
        weighted_lat = np.average(cluster_df['lat'], weights=weights)
        weighted_lon = np.average(cluster_df['lon'], weights=weights)
        
        return GeoPoint(lat=weighted_lat, lon=weighted_lon)
    
    def _calculate_uncertainty(self, cluster_df: pd.DataFrame, center: GeoPoint) -> float:
        """Calculate uncertainty radius based on cluster spread."""
        # Calculate distances from center
        distances = []
        for _, row in cluster_df.iterrows():
            dist = self._haversine_distance(
                center.lat, center.lon,
                row['lat'], row['lon']
            )
            distances.append(dist)
        
        # Use 95th percentile as uncertainty radius
        return float(np.percentile(distances, 95))
    
    def _calculate_confidence(self, cluster_df: pd.DataFrame, total_obs: int) -> float:
        """Calculate confidence score based on cluster quality."""
        cluster_size = len(cluster_df)
        cluster_ratio = cluster_size / total_obs
        
        # RSSI consistency (lower std = higher confidence)
        rssi_std = cluster_df['rssi_dbm'].std()
        rssi_consistency = np.exp(-rssi_std / 10.0)  # Normalize
        
        # Combine factors
        confidence = cluster_ratio * rssi_consistency * min(cluster_size / 10.0, 1.0)
        
        return float(np.clip(confidence, 0.0, 1.0))
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula."""
        R = 6371000  # Earth radius in meters
        
        lat1_rad = np.radians(lat1)
        lat2_rad = np.radians(lat2)
        dlat = np.radians(lat2 - lat1)
        dlon = np.radians(lon2 - lon1)
        
        a = (np.sin(dlat/2)**2 + 
             np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon/2)**2)
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
        
        return R * c

class MultiNodeLocalizer:
    """Multi-node triangulation using least squares optimization."""
    
    def __init__(self, path_loss_exp: float = 2.0, ref_distance: float = 1.0):
        """
        Initialize multi-node localizer.
        
        Args:
            path_loss_exp: Path loss exponent (2.0 for free space)
            ref_distance: Reference distance for path loss model
        """
        self.path_loss_exp = path_loss_exp
        self.ref_distance = ref_distance
    
    def estimate_location(self, 
                         synchronized_observations: List[List[Observation]],
                         initial_guess: Optional[Tuple[float, float]] = None) -> Optional[LocationEstimate]:
        """
        Estimate transmitter location using multi-node triangulation.
        
        Args:
            synchronized_observations: List of observation lists, one per observer
            initial_guess: Initial guess for optimization (lat, lon)
            
        Returns:
            LocationEstimate or None if insufficient data
        """
        if len(synchronized_observations) < 3:
            logger.debug("Need at least 3 observers for triangulation")
            return None
        
        # Extract observer positions and RSSI values
        observers = []
        rssi_values = []
        
        for obs_list in synchronized_observations:
            if not obs_list:
                continue
            
            # Use average RSSI if multiple observations from same observer
            avg_rssi = np.mean([obs.rssi_dbm for obs in obs_list])
            observer_pos = obs_list[0].observer_location
            
            observers.append((observer_pos.lat, observer_pos.lon))
            rssi_values.append(avg_rssi)
        
        if len(observers) < 3:
            return None
        
        observers = np.array(observers)
        rssi_values = np.array(rssi_values)
        
        # Initial guess (center of observers if not provided)
        if initial_guess is None:
            initial_guess = (np.mean(observers[:, 0]), np.mean(observers[:, 1]))
        
        # Optimize using least squares
        try:
            result = least_squares(
                self._residual_function,
                initial_guess,
                args=(observers, rssi_values),
                method='lm'
            )
            
            if not result.success:
                logger.warning("Optimization failed")
                return None
            
            estimated_lat, estimated_lon = result.x
            
            # Calculate uncertainty from residuals
            residuals = self._residual_function(result.x, observers, rssi_values)
            rms_error = np.sqrt(np.mean(residuals**2))
            
            # Rough uncertainty estimate
            uncertainty_radius = rms_error * 10  # Convert to meters (rough)
            
            # Calculate confidence
            confidence = self._calculate_triangulation_confidence(
                observers, rssi_values, result.x, rms_error
            )
            
            return LocationEstimate(
                signal_id=synchronized_observations[0][0].signal_id,
                method="multi_node_triangulation",
                estimated_location=GeoPoint(lat=estimated_lat, lon=estimated_lon),
                uncertainty_radius_m=uncertainty_radius,
                confidence=confidence,
                support_count=len(observers),
                residual_error=rms_error
            )
            
        except Exception as e:
            logger.error(f"Triangulation failed: {e}")
            return None
    
    def _residual_function(self, 
                          pos: Tuple[float, float], 
                          observers: np.ndarray, 
                          rssi_values: np.ndarray) -> np.ndarray:
        """Calculate residuals for least squares optimization."""
        tx_lat, tx_lon = pos
        
        residuals = []
        for i, (obs_lat, obs_lon) in enumerate(observers):
            # Calculate distance
            distance = self._haversine_distance(tx_lat, tx_lon, obs_lat, obs_lon)
            
            # Convert RSSI to expected distance using path loss model
            # RSSI = RSSI_0 - 10*n*log10(d/d_0)
            # Assuming RSSI_0 = -30 dBm at 1m for typical devices
            rssi_0 = -30
            expected_rssi = rssi_0 - 10 * self.path_loss_exp * np.log10(
                max(distance, self.ref_distance) / self.ref_distance
            )
            
            residuals.append(rssi_values[i] - expected_rssi)
        
        return np.array(residuals)
    
    def _calculate_triangulation_confidence(self, 
                                          observers: np.ndarray,
                                          rssi_values: np.ndarray,
                                          estimated_pos: Tuple[float, float],
                                          rms_error: float) -> float:
        """Calculate confidence for triangulation result."""
        # Geometric dilution of precision (GDOP)
        gdop = self._calculate_gdop(observers, estimated_pos)
        
        # RSSI consistency
        rssi_std = np.std(rssi_values)
        rssi_consistency = np.exp(-rssi_std / 10.0)
        
        # Error-based confidence
        error_confidence = np.exp(-rms_error / 5.0)
        
        # Combine factors
        confidence = rssi_consistency * error_confidence / (1 + gdop)
        
        return float(np.clip(confidence, 0.0, 1.0))
    
    def _calculate_gdop(self, observers: np.ndarray, estimated_pos: Tuple[float, float]) -> float:
        """Calculate geometric dilution of precision."""
        # Simplified GDOP calculation
        tx_lat, tx_lon = estimated_pos
        
        # Calculate unit vectors from transmitter to observers
        unit_vectors = []
        for obs_lat, obs_lon in observers:
            dx = obs_lon - tx_lon
            dy = obs_lat - tx_lat
            distance = np.sqrt(dx**2 + dy**2)
            
            if distance > 0:
                unit_vectors.append([dx/distance, dy/distance])
        
        if len(unit_vectors) < 3:
            return float('inf')
        
        # Calculate condition number of geometry matrix
        G = np.array(unit_vectors)
        try:
            gdop = np.linalg.cond(G.T @ G)
        except:
            gdop = float('inf')
        
        return float(gdop)
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula."""
        R = 6371000  # Earth radius in meters
        
        lat1_rad = np.radians(lat1)
        lat2_rad = np.radians(lat2)
        dlat = np.radians(lat2 - lat1)
        dlon = np.radians(lon2 - lon1)
        
        a = (np.sin(dlat/2)**2 + 
             np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon/2)**2)
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
        
        return R * c
