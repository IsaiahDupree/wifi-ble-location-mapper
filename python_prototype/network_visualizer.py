#!/usr/bin/env python3
"""
WiFi Network Location Visualizer
Creates an interactive map with you at the center and WiFi networks positioned around you
"""

import math
import random
import json
from datetime import datetime
from typing import List, Dict, Tuple
from wifi_scanner import WiFiScanner
from location_tracker import LocationTracker

class NetworkVisualizer:
    def __init__(self):
        self.center_lat = 40.712800  # Your location (center)
        self.center_lon = -74.006000
        self.wifi_scanner = WiFiScanner()
        self.location_tracker = LocationTracker()
        
    def estimate_network_location(self, network: Dict, base_lat: float, base_lon: float) -> Tuple[float, float]:
        """
        Estimate network location based on signal strength and network type
        Places networks in a realistic pattern around your location
        """
        signal_strength = network['signal_strength']
        ssid = network['ssid'].lower() if network['ssid'] else 'unknown'
        
        # Estimate distance based on signal strength (rough approximation)
        # Stronger signal = closer distance
        if signal_strength > -40:
            distance_m = random.uniform(10, 50)      # Very close
        elif signal_strength > -50:
            distance_m = random.uniform(50, 100)     # Close
        elif signal_strength > -60:
            distance_m = random.uniform(100, 200)    # Medium
        elif signal_strength > -70:
            distance_m = random.uniform(200, 400)    # Far
        elif signal_strength > -80:
            distance_m = random.uniform(400, 800)    # Very far
        else:
            distance_m = random.uniform(800, 1500)   # Distant
        
        # Adjust distance based on network type
        if any(keyword in ssid for keyword in ['starbucks', 'coffee', 'panera', 'restaurant']):
            # Commercial locations - typically closer and in specific directions
            distance_m *= 0.7
        elif any(keyword in ssid for keyword in ['hotel', 'guest', 'inn', 'hilton']):
            # Hotels - medium distance
            distance_m *= 0.8
        elif any(keyword in ssid for keyword in ['att', 'spectrum', 'xfinity', 'verizon']):
            # ISP networks - residential areas, varied distances
            distance_m *= random.uniform(0.5, 1.5)
        elif network['encryption'] == 'Open':
            # Open networks often businesses - closer
            distance_m *= 0.6
        
        # Generate random angle for positioning
        angle = random.uniform(0, 2 * math.pi)
        
        # Convert distance to lat/lon offset (rough approximation)
        lat_offset = (distance_m / 111320) * math.cos(angle)  # 1 degree lat ≈ 111320m
        lon_offset = (distance_m / (111320 * math.cos(math.radians(base_lat)))) * math.sin(angle)
        
        return (base_lat + lat_offset, base_lon + lon_offset)
    
    def create_html_map(self, networks: List[Dict]) -> str:
        """Create an interactive HTML map with networks positioned around you"""
        
        # Get your current location
        location = self.location_tracker.get_gps_location()
        if location:
            self.center_lat = location['latitude']
            self.center_lon = location['longitude']
        
        # Estimate positions for each network
        network_positions = []
        for network in networks:
            lat, lon = self.estimate_network_location(network, self.center_lat, self.center_lon)
            network_positions.append({
                'network': network,
                'lat': lat,
                'lon': lon
            })
        
        # Create HTML with Leaflet map
        html_content = f'''
<!DOCTYPE html>
<html>
<head>
    <title>WiFi Networks Around You</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body {{ margin: 0; padding: 0; font-family: Arial, sans-serif; }}
        #map {{ height: 100vh; width: 100%; }}
        .info-panel {{
            position: fixed;
            top: 10px;
            right: 10px;
            background: rgba(255,255,255,0.95);
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            max-width: 300px;
            z-index: 1000;
        }}
        .network-info {{
            margin-bottom: 10px;
            padding: 8px;
            border-left: 4px solid #3498db;
            background: #f8f9fa;
        }}
        .signal-excellent {{ border-left-color: #27ae60; }}
        .signal-good {{ border-left-color: #f39c12; }}
        .signal-poor {{ border-left-color: #e74c3c; }}
        .legend {{
            position: fixed;
            bottom: 10px;
            left: 10px;
            background: rgba(255,255,255,0.95);
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            z-index: 1000;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            margin-bottom: 5px;
        }}
        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 50%;
            margin-right: 10px;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    
    <div class="info-panel">
        <h3>🌐 WiFi Networks Detected</h3>
        <p><strong>Total Networks:</strong> {len(networks)}</p>
        <p><strong>Your Location:</strong><br>
           {self.center_lat:.6f}, {self.center_lon:.6f}</p>
        <p><strong>Scan Time:</strong><br>
           {datetime.now().strftime('%H:%M:%S')}</p>
    </div>
    
    <div class="legend">
        <h4>🎯 Legend</h4>
        <div class="legend-item">
            <div class="legend-color" style="background: #e74c3c;"></div>
            <span>You (Center)</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #27ae60;"></div>
            <span>Strong Signal (-50+ dBm)</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #f39c12;"></div>
            <span>Medium Signal (-50 to -70 dBm)</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #95a5a6;"></div>
            <span>Weak Signal (-70+ dBm)</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #3498db;"></div>
            <span>Open Network</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #9b59b6;"></div>
            <span>Secured Network</span>
        </div>
    </div>

    <script>
        // Initialize map centered on your location
        var map = L.map('map').setView([{self.center_lat}, {self.center_lon}], 16);
        
        // Add OpenStreetMap tiles
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenStreetMap contributors'
        }}).addTo(map);
        
        // Add your location marker (center)
        var yourLocation = L.marker([{self.center_lat}, {self.center_lon}], {{
            icon: L.divIcon({{
                className: 'your-location',
                html: '<div style="background: #e74c3c; width: 20px; height: 20px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 5px rgba(0,0,0,0.3);"></div>',
                iconSize: [20, 20],
                iconAnchor: [10, 10]
            }})
        }}).addTo(map);
        
        yourLocation.bindPopup(`
            <div style="text-align: center;">
                <h4>📍 Your Location</h4>
                <p>Lat: {self.center_lat:.6f}<br>
                   Lon: {self.center_lon:.6f}</p>
                <p><em>WiFi Detection Center</em></p>
            </div>
        `);
        
        // Add network markers
        var networks = {json.dumps(network_positions)};
        
        networks.forEach(function(item) {{
            var network = item.network;
            var lat = item.lat;
            var lon = item.lon;
            
            // Determine marker color based on signal strength
            var color = '#95a5a6'; // Default gray for weak
            if (network.signal_strength > -50) {{
                color = '#27ae60'; // Green for strong
            }} else if (network.signal_strength > -70) {{
                color = '#f39c12'; // Orange for medium
            }}
            
            // Adjust color for open networks
            if (network.encryption === 'Open') {{
                color = '#3498db'; // Blue for open
            }}
            
            // Create marker
            var marker = L.marker([lat, lon], {{
                icon: L.divIcon({{
                    className: 'network-marker',
                    html: `<div style="background: ${{color}}; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white; box-shadow: 0 1px 3px rgba(0,0,0,0.3);"></div>`,
                    iconSize: [12, 12],
                    iconAnchor: [6, 6]
                }})
            }}).addTo(map);
            
            // Create popup content
            var signalIcon = network.signal_strength > -50 ? '🟢' : 
                           network.signal_strength > -70 ? '🟡' : '🔴';
            var securityIcon = network.encryption === 'Open' ? '🔓' : '🔒';
            
            marker.bindPopup(`
                <div style="min-width: 200px;">
                    <h4>${{signalIcon}} ${{network.ssid || 'Hidden Network'}}</h4>
                    <p><strong>Signal:</strong> ${{network.signal_strength}} dBm</p>
                    <p><strong>Security:</strong> ${{securityIcon}} ${{network.encryption}}</p>
                    <p><strong>BSSID:</strong> ${{network.bssid}}</p>
                    <p><em>Estimated location based on signal strength</em></p>
                </div>
            `);
        }});
        
        // Add distance circles
        var circles = [100, 300, 500, 1000]; // meters
        circles.forEach(function(radius) {{
            L.circle([{self.center_lat}, {self.center_lon}], {{
                color: '#3498db',
                fillColor: 'transparent',
                fillOpacity: 0,
                radius: radius,
                weight: 1,
                opacity: 0.3,
                dashArray: '5, 5'
            }}).addTo(map);
        }});
        
        // Add scale control
        L.control.scale().addTo(map);
    </script>
</body>
</html>
        '''
        
        return html_content
    
    def generate_visualization(self) -> str:
        """Generate the complete visualization"""
        print("🗺️  Generating WiFi network location visualization...")
        
        # Scan for networks
        print("📡 Scanning for WiFi networks...")
        networks = self.wifi_scanner.scan_once()
        
        if not networks:
            print("❌ No networks detected")
            return None
        
        print(f"📶 Found {len(networks)} networks")
        
        # Create HTML map
        html_content = self.create_html_map(networks)
        
        # Save to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'wifi_network_map_{timestamp}.html'
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"🎯 Interactive map saved as: {filename}")
        print("🌐 Open the HTML file in your browser to see the visualization")
        
        # Also save raw data
        data_filename = f'network_positions_{timestamp}.json'
        export_data = {
            'center_location': {
                'latitude': self.center_lat,
                'longitude': self.center_lon
            },
            'networks': networks,
            'scan_timestamp': datetime.now().isoformat(),
            'total_networks': len(networks)
        }
        
        with open(data_filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"📊 Raw data saved as: {data_filename}")
        
        return filename

def main():
    """Main function to run the visualizer"""
    print("🌐 WiFi Network Location Visualizer")
    print("=" * 50)
    print("Creating interactive map with you at the center...")
    print()
    
    visualizer = NetworkVisualizer()
    map_file = visualizer.generate_visualization()
    
    if map_file:
        print("\n✅ Visualization complete!")
        print(f"📁 Open {map_file} in your web browser")
        print("\n🎯 Features:")
        print("   • You are at the center (red marker)")
        print("   • WiFi networks positioned by estimated location")
        print("   • Color-coded by signal strength")
        print("   • Click markers for network details")
        print("   • Distance circles show range")
        print("   • Interactive zoom and pan")

if __name__ == "__main__":
    main()
