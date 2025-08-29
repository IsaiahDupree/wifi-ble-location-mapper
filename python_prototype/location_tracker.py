import json
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Callable
import math

try:
    import gpsd
    GPSD_AVAILABLE = True
except ImportError:
    GPSD_AVAILABLE = False
    print("Warning: gpsd-py3 not available. Install with: pip install gpsd-py3")

try:
    from geopy.distance import geodesic
    GEOPY_AVAILABLE = True
except ImportError:
    GEOPY_AVAILABLE = False
    print("Warning: geopy not available. Install with: pip install geopy")

class LocationTracker:
    def __init__(self):
        self.current_location = None
        self.location_history = []
        self.tracking = False
        self.track_thread = None
        self.callback = None
        self.indoor_positioning = IndoorPositioning()
        
    def set_callback(self, callback: Callable):
        """Set callback function for location updates"""
        self.callback = callback
    
    def connect_gps(self) -> bool:
        """Connect to GPS daemon"""
        if not GPSD_AVAILABLE:
            print("GPS not available - using simulated location")
            return False
        
        try:
            gpsd.connect()
            return True
        except Exception as e:
            print(f"Failed to connect to GPS: {e}")
            return False
    
    def get_gps_location(self) -> Optional[Dict]:
        """Get current GPS location"""
        if not GPSD_AVAILABLE:
            return self.get_simulated_location()
        
        try:
            packet = gpsd.get_current()
            
            if packet.mode >= 2:  # 2D fix or better
                location = {
                    'latitude': packet.lat,
                    'longitude': packet.lon,
                    'altitude': packet.alt if packet.mode >= 3 else None,
                    'speed': packet.speed,
                    'heading': packet.track,
                    'accuracy': packet.error.get('epx', 0) if hasattr(packet, 'error') else 5.0,
                    'timestamp': datetime.now().isoformat(),
                    'source': 'GPS',
                    'satellites': packet.sats if hasattr(packet, 'sats') else 0
                }
                return location
            else:
                print("GPS fix not available")
                return None
                
        except Exception as e:
            print(f"Error getting GPS location: {e}")
            return None
    
    def get_simulated_location(self) -> Dict:
        """Generate simulated location for testing"""
        # Simulate movement in a small area (e.g., around a building)
        base_lat = 40.7128  # New York City
        base_lon = -74.0060
        
        # Add small random movement
        import random
        lat_offset = random.uniform(-0.001, 0.001)  # ~100m range
        lon_offset = random.uniform(-0.001, 0.001)
        
        return {
            'latitude': base_lat + lat_offset,
            'longitude': base_lon + lon_offset,
            'altitude': 10.0 + random.uniform(-5, 5),
            'speed': random.uniform(0, 2),  # Walking speed
            'heading': random.uniform(0, 360),
            'accuracy': 5.0,
            'timestamp': datetime.now().isoformat(),
            'source': 'Simulated',
            'satellites': 8
        }
    
    def start_tracking(self, interval: int = 5):
        """Start continuous location tracking"""
        if self.tracking:
            return
        
        self.tracking = True
        self.track_thread = threading.Thread(target=self._tracking_loop, args=(interval,))
        self.track_thread.daemon = True
        self.track_thread.start()
        
        if GPSD_AVAILABLE:
            self.connect_gps()
    
    def stop_tracking(self):
        """Stop location tracking"""
        self.tracking = False
        if self.track_thread:
            self.track_thread.join()
    
    def _tracking_loop(self, interval: int):
        """Internal tracking loop"""
        while self.tracking:
            try:
                location = self.get_gps_location()
                if location:
                    self.current_location = location
                    self.location_history.append(location)
                    
                    # Keep only last 1000 locations to prevent memory issues
                    if len(self.location_history) > 1000:
                        self.location_history = self.location_history[-1000:]
                    
                    if self.callback:
                        self.callback('location', location)
                    
                    print(f"Location: {location['latitude']:.6f}, {location['longitude']:.6f} "
                          f"({location['source']})")
                
            except Exception as e:
                print(f"Error in tracking loop: {e}")
            
            time.sleep(interval)
    
    def get_current_location(self) -> Optional[Dict]:
        """Get the most recent location"""
        return self.current_location
    
    def calculate_distance_traveled(self) -> float:
        """Calculate total distance traveled in meters"""
        if len(self.location_history) < 2 or not GEOPY_AVAILABLE:
            return 0.0
        
        total_distance = 0.0
        for i in range(1, len(self.location_history)):
            prev_loc = self.location_history[i-1]
            curr_loc = self.location_history[i]
            
            prev_point = (prev_loc['latitude'], prev_loc['longitude'])
            curr_point = (curr_loc['latitude'], curr_loc['longitude'])
            
            distance = geodesic(prev_point, curr_point).meters
            total_distance += distance
        
        return total_distance
    
    def get_location_at_time(self, timestamp: str) -> Optional[Dict]:
        """Get location closest to a specific timestamp"""
        if not self.location_history:
            return None
        
        target_time = datetime.fromisoformat(timestamp)
        closest_location = None
        min_time_diff = float('inf')
        
        for location in self.location_history:
            loc_time = datetime.fromisoformat(location['timestamp'])
            time_diff = abs((target_time - loc_time).total_seconds())
            
            if time_diff < min_time_diff:
                min_time_diff = time_diff
                closest_location = location
        
        return closest_location
    
    def export_track(self, filename: str):
        """Export location history to JSON file"""
        try:
            export_data = {
                'current_location': self.current_location,
                'location_history': self.location_history,
                'total_distance': self.calculate_distance_traveled(),
                'export_timestamp': datetime.now().isoformat()
            }
            
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)
            print(f"Location track exported to {filename}")
        except Exception as e:
            print(f"Error exporting location track: {e}")

class IndoorPositioning:
    """Indoor positioning using WiFi fingerprinting and trilateration"""
    
    def __init__(self):
        self.reference_points = {}
        self.wifi_fingerprints = {}
    
    def add_reference_point(self, point_id: str, x: float, y: float, z: float = 0):
        """Add a known reference point for indoor positioning"""
        self.reference_points[point_id] = {'x': x, 'y': y, 'z': z}
    
    def record_wifi_fingerprint(self, point_id: str, wifi_data: List[Dict]):
        """Record WiFi fingerprint at a known location"""
        fingerprint = {}
        for network in wifi_data:
            fingerprint[network['bssid']] = network['signal_strength']
        
        self.wifi_fingerprints[point_id] = fingerprint
    
    def estimate_position(self, current_wifi: List[Dict]) -> Optional[Dict]:
        """Estimate current position based on WiFi fingerprint matching"""
        if not self.wifi_fingerprints:
            return None
        
        current_fingerprint = {}
        for network in current_wifi:
            current_fingerprint[network['bssid']] = network['signal_strength']
        
        best_match = None
        best_similarity = float('inf')
        
        for point_id, reference_fingerprint in self.wifi_fingerprints.items():
            similarity = self.calculate_fingerprint_distance(
                current_fingerprint, reference_fingerprint
            )
            
            if similarity < best_similarity:
                best_similarity = similarity
                best_match = point_id
        
        if best_match and best_match in self.reference_points:
            position = self.reference_points[best_match].copy()
            position['confidence'] = 1.0 / (1.0 + best_similarity)
            position['method'] = 'WiFi Fingerprinting'
            position['timestamp'] = datetime.now().isoformat()
            return position
        
        return None
    
    def calculate_fingerprint_distance(self, fp1: Dict, fp2: Dict) -> float:
        """Calculate Euclidean distance between WiFi fingerprints"""
        common_bssids = set(fp1.keys()) & set(fp2.keys())
        
        if not common_bssids:
            return float('inf')
        
        distance = 0.0
        for bssid in common_bssids:
            distance += (fp1[bssid] - fp2[bssid]) ** 2
        
        return math.sqrt(distance / len(common_bssids))
    
    def trilaterate_position(self, access_points: List[Dict]) -> Optional[Dict]:
        """Estimate position using trilateration from known AP positions"""
        if len(access_points) < 3:
            return None
        
        # This is a simplified trilateration implementation
        # In practice, you'd need known AP positions and more sophisticated algorithms
        
        # For now, return the centroid of the first 3 APs
        x_sum = sum(ap.get('x', 0) for ap in access_points[:3])
        y_sum = sum(ap.get('y', 0) for ap in access_points[:3])
        
        return {
            'x': x_sum / 3,
            'y': y_sum / 3,
            'z': 0,
            'method': 'Trilateration',
            'confidence': 0.7,
            'timestamp': datetime.now().isoformat()
        }

if __name__ == "__main__":
    tracker = LocationTracker()
    
    print("Starting location tracker...")
    print(f"GPS available: {GPSD_AVAILABLE}")
    
    # Test single location reading
    location = tracker.get_gps_location()
    if location:
        print(f"Current location: {location['latitude']:.6f}, {location['longitude']:.6f}")
        print(f"Source: {location['source']}")
        print(f"Accuracy: {location['accuracy']} meters")
    
    # Test tracking for a short period
    print("\nStarting 30-second tracking test...")
    tracker.start_tracking(interval=2)
    time.sleep(30)
    tracker.stop_tracking()
    
    print(f"\nTracked {len(tracker.location_history)} locations")
    print(f"Distance traveled: {tracker.calculate_distance_traveled():.2f} meters")
    
    # Export results
    tracker.export_track('location_track.json')
