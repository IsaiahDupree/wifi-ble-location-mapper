import json
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import math

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    print("Warning: numpy not available. Install with: pip install numpy")

try:
    import matplotlib.pyplot as plt
    import matplotlib.colors as colors
    from matplotlib.patches import Circle
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: matplotlib not available. Install with: pip install matplotlib")

class SignalMapper:
    def __init__(self):
        self.signal_data = []
        self.wifi_heatmap = {}
        self.bluetooth_heatmap = {}
        self.location_signals = {}
        
    def add_signal_reading(self, location: Dict, wifi_data: List[Dict], bluetooth_data: List[Dict]):
        """Add a signal reading at a specific location"""
        reading = {
            'timestamp': datetime.now().isoformat(),
            'location': location,
            'wifi_networks': wifi_data,
            'bluetooth_devices': bluetooth_data
        }
        
        self.signal_data.append(reading)
        self._update_heatmaps(reading)
        
        # Store by location key for quick lookup
        loc_key = self._get_location_key(location)
        if loc_key not in self.location_signals:
            self.location_signals[loc_key] = []
        self.location_signals[loc_key].append(reading)
    
    def _get_location_key(self, location: Dict) -> str:
        """Generate a location key for grouping nearby readings"""
        if 'latitude' in location and 'longitude' in location:
            # Round to ~10m precision
            lat = round(location['latitude'], 4)
            lon = round(location['longitude'], 4)
            return f"{lat},{lon}"
        elif 'x' in location and 'y' in location:
            # Indoor coordinates
            x = round(location['x'], 1)
            y = round(location['y'], 1)
            return f"{x},{y}"
        else:
            return "unknown"
    
    def _update_heatmaps(self, reading: Dict):
        """Update signal strength heatmaps"""
        location = reading['location']
        loc_key = self._get_location_key(location)
        
        # Update WiFi heatmap
        for network in reading['wifi_networks']:
            bssid = network['bssid']
            signal = network['signal_strength']
            
            if bssid not in self.wifi_heatmap:
                self.wifi_heatmap[bssid] = {}
            
            if loc_key not in self.wifi_heatmap[bssid]:
                self.wifi_heatmap[bssid][loc_key] = []
            
            self.wifi_heatmap[bssid][loc_key].append({
                'signal': signal,
                'timestamp': reading['timestamp'],
                'location': location
            })
        
        # Update Bluetooth heatmap
        for device in reading['bluetooth_devices']:
            address = device['address']
            signal = device.get('rssi', -100)
            
            if address not in self.bluetooth_heatmap:
                self.bluetooth_heatmap[address] = {}
            
            if loc_key not in self.bluetooth_heatmap[address]:
                self.bluetooth_heatmap[address][loc_key] = []
            
            self.bluetooth_heatmap[address][loc_key].append({
                'signal': signal,
                'timestamp': reading['timestamp'],
                'location': location
            })
    
    def get_signal_strength_at_location(self, location: Dict, signal_type: str = 'wifi') -> Dict:
        """Get average signal strengths at a specific location"""
        loc_key = self._get_location_key(location)
        
        if loc_key not in self.location_signals:
            return {}
        
        readings = self.location_signals[loc_key]
        signal_strengths = {}
        
        for reading in readings:
            if signal_type == 'wifi':
                for network in reading['wifi_networks']:
                    bssid = network['bssid']
                    signal = network['signal_strength']
                    
                    if bssid not in signal_strengths:
                        signal_strengths[bssid] = []
                    signal_strengths[bssid].append(signal)
            
            elif signal_type == 'bluetooth':
                for device in reading['bluetooth_devices']:
                    address = device['address']
                    signal = device.get('rssi', -100)
                    
                    if address not in signal_strengths:
                        signal_strengths[address] = []
                    signal_strengths[address].append(signal)
        
        # Calculate averages
        avg_signals = {}
        for identifier, signals in signal_strengths.items():
            avg_signals[identifier] = {
                'average': sum(signals) / len(signals),
                'min': min(signals),
                'max': max(signals),
                'count': len(signals)
            }
        
        return avg_signals
    
    def interpolate_signal_strength(self, target_location: Dict, bssid: str, signal_type: str = 'wifi') -> Optional[float]:
        """Interpolate signal strength at a target location using inverse distance weighting"""
        if not NUMPY_AVAILABLE:
            return None
        
        heatmap = self.wifi_heatmap if signal_type == 'wifi' else self.bluetooth_heatmap
        
        if bssid not in heatmap:
            return None
        
        locations = heatmap[bssid]
        if not locations:
            return None
        
        # Collect known signal strengths and their locations
        known_points = []
        for loc_key, readings in locations.items():
            if readings:
                avg_signal = sum(r['signal'] for r in readings) / len(readings)
                location = readings[0]['location']  # Use first reading's location
                known_points.append((location, avg_signal))
        
        if not known_points:
            return None
        
        # Inverse distance weighting
        weights = []
        values = []
        
        for location, signal in known_points:
            distance = self._calculate_distance(target_location, location)
            if distance < 0.001:  # Very close, return exact value
                return signal
            
            weight = 1.0 / (distance ** 2)
            weights.append(weight)
            values.append(signal)
        
        if not weights:
            return None
        
        # Weighted average
        weighted_sum = sum(w * v for w, v in zip(weights, values))
        weight_sum = sum(weights)
        
        return weighted_sum / weight_sum
    
    def _calculate_distance(self, loc1: Dict, loc2: Dict) -> float:
        """Calculate distance between two locations"""
        if 'latitude' in loc1 and 'latitude' in loc2:
            # Geographic distance (simplified)
            lat1, lon1 = loc1['latitude'], loc1['longitude']
            lat2, lon2 = loc2['latitude'], loc2['longitude']
            
            # Haversine formula (simplified for small distances)
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            
            a = (math.sin(dlat/2) ** 2 + 
                 math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
                 math.sin(dlon/2) ** 2)
            
            c = 2 * math.asin(math.sqrt(a))
            return 6371000 * c  # Earth radius in meters
        
        elif 'x' in loc1 and 'x' in loc2:
            # Euclidean distance for indoor coordinates
            dx = loc1['x'] - loc2['x']
            dy = loc1['y'] - loc2['y']
            dz = loc1.get('z', 0) - loc2.get('z', 0)
            
            return math.sqrt(dx**2 + dy**2 + dz**2)
        
        return float('inf')
    
    def generate_heatmap_data(self, signal_type: str = 'wifi', identifier: str = None) -> Dict:
        """Generate heatmap data for visualization"""
        heatmap = self.wifi_heatmap if signal_type == 'wifi' else self.bluetooth_heatmap
        
        if identifier and identifier in heatmap:
            # Generate data for specific network/device
            locations = heatmap[identifier]
            heatmap_data = []
            
            for loc_key, readings in locations.items():
                if readings:
                    location = readings[0]['location']
                    avg_signal = sum(r['signal'] for r in readings) / len(readings)
                    
                    heatmap_data.append({
                        'location': location,
                        'signal_strength': avg_signal,
                        'readings_count': len(readings)
                    })
            
            return {
                'identifier': identifier,
                'type': signal_type,
                'data': heatmap_data
            }
        
        else:
            # Generate combined heatmap data
            all_data = []
            
            for identifier, locations in heatmap.items():
                for loc_key, readings in locations.items():
                    if readings:
                        location = readings[0]['location']
                        avg_signal = sum(r['signal'] for r in readings) / len(readings)
                        
                        all_data.append({
                            'identifier': identifier,
                            'location': location,
                            'signal_strength': avg_signal,
                            'readings_count': len(readings)
                        })
            
            return {
                'type': signal_type,
                'data': all_data
            }
    
    def plot_heatmap(self, signal_type: str = 'wifi', identifier: str = None, save_path: str = None):
        """Plot signal strength heatmap"""
        if not MATPLOTLIB_AVAILABLE:
            print("Matplotlib not available for plotting")
            return
        
        heatmap_data = self.generate_heatmap_data(signal_type, identifier)
        data_points = heatmap_data['data']
        
        if not data_points:
            print("No data available for plotting")
            return
        
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Extract coordinates and signal strengths
        x_coords = []
        y_coords = []
        signals = []
        
        for point in data_points:
            location = point['location']
            if 'latitude' in location:
                x_coords.append(location['longitude'])
                y_coords.append(location['latitude'])
            elif 'x' in location:
                x_coords.append(location['x'])
                y_coords.append(location['y'])
            
            signals.append(point['signal_strength'])
        
        if not x_coords:
            print("No valid coordinates for plotting")
            return
        
        # Create scatter plot with color mapping
        scatter = ax.scatter(x_coords, y_coords, c=signals, 
                           cmap='RdYlGn', s=100, alpha=0.7)
        
        # Add colorbar
        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label('Signal Strength (dBm)')
        
        # Set labels and title
        if 'latitude' in data_points[0]['location']:
            ax.set_xlabel('Longitude')
            ax.set_ylabel('Latitude')
        else:
            ax.set_xlabel('X Coordinate')
            ax.set_ylabel('Y Coordinate')
        
        title = f"{signal_type.title()} Signal Strength Heatmap"
        if identifier:
            title += f" - {identifier}"
        ax.set_title(title)
        
        # Add grid
        ax.grid(True, alpha=0.3)
        
        # Save or show
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Heatmap saved to {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    def analyze_coverage(self, signal_type: str = 'wifi') -> Dict:
        """Analyze signal coverage statistics"""
        heatmap = self.wifi_heatmap if signal_type == 'wifi' else self.bluetooth_heatmap
        
        analysis = {
            'total_networks': len(heatmap),
            'total_locations': len(set(
                loc_key for locations in heatmap.values() 
                for loc_key in locations.keys()
            )),
            'total_readings': len(self.signal_data),
            'network_stats': {}
        }
        
        for identifier, locations in heatmap.items():
            readings_count = sum(len(readings) for readings in locations.values())
            all_signals = [
                reading['signal'] 
                for readings in locations.values() 
                for reading in readings
            ]
            
            if all_signals:
                analysis['network_stats'][identifier] = {
                    'locations_count': len(locations),
                    'readings_count': readings_count,
                    'avg_signal': sum(all_signals) / len(all_signals),
                    'min_signal': min(all_signals),
                    'max_signal': max(all_signals),
                    'signal_range': max(all_signals) - min(all_signals)
                }
        
        return analysis
    
    def export_data(self, filename: str):
        """Export all signal mapping data"""
        try:
            export_data = {
                'signal_data': self.signal_data,
                'wifi_heatmap': self.wifi_heatmap,
                'bluetooth_heatmap': self.bluetooth_heatmap,
                'wifi_analysis': self.analyze_coverage('wifi'),
                'bluetooth_analysis': self.analyze_coverage('bluetooth'),
                'export_timestamp': datetime.now().isoformat()
            }
            
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            print(f"Signal mapping data exported to {filename}")
        except Exception as e:
            print(f"Error exporting signal mapping data: {e}")

if __name__ == "__main__":
    # Test signal mapper with simulated data
    mapper = SignalMapper()
    
    print("Testing Signal Mapper with simulated data...")
    
    # Simulate some readings
    for i in range(10):
        location = {
            'latitude': 40.7128 + i * 0.0001,
            'longitude': -74.0060 + i * 0.0001,
            'timestamp': datetime.now().isoformat()
        }
        
        wifi_data = [
            {'ssid': 'TestNetwork1', 'bssid': 'aa:bb:cc:dd:ee:01', 'signal_strength': -50 - i * 2},
            {'ssid': 'TestNetwork2', 'bssid': 'aa:bb:cc:dd:ee:02', 'signal_strength': -60 - i * 3}
        ]
        
        bluetooth_data = [
            {'name': 'TestDevice1', 'address': '11:22:33:44:55:01', 'rssi': -40 - i * 2}
        ]
        
        mapper.add_signal_reading(location, wifi_data, bluetooth_data)
    
    print(f"Added {len(mapper.signal_data)} signal readings")
    
    # Analyze coverage
    wifi_analysis = mapper.analyze_coverage('wifi')
    print(f"\nWiFi Analysis:")
    print(f"  Networks: {wifi_analysis['total_networks']}")
    print(f"  Locations: {wifi_analysis['total_locations']}")
    print(f"  Readings: {wifi_analysis['total_readings']}")
    
    # Test interpolation
    test_location = {'latitude': 40.7130, 'longitude': -74.0058}
    interpolated = mapper.interpolate_signal_strength(test_location, 'aa:bb:cc:dd:ee:01')
    if interpolated:
        print(f"\nInterpolated signal strength: {interpolated:.1f} dBm")
    
    # Export data
    mapper.export_data('signal_mapping_data.json')
    
    # Try to plot if matplotlib is available
    if MATPLOTLIB_AVAILABLE:
        mapper.plot_heatmap('wifi', save_path='wifi_heatmap.png')
        print("Heatmap visualization saved")
