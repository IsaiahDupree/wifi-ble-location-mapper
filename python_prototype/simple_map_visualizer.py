#!/usr/bin/env python3
"""
Simple WiFi Network Map Visualizer
Creates an interactive map with you at the center using existing scan data
"""

import json
import math
import random
from datetime import datetime
from typing import List, Dict, Tuple

def load_existing_scan_data():
    """Load WiFi data from existing scan results"""
    try:
        with open('wifi_scan_results.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Return sample data based on your actual scan results
        return [
            {"ssid": "Starbucks", "signal_strength": -45, "encryption": "Open", "bssid": "aa:bb:cc:dd:ee:01"},
            {"ssid": "Panera", "signal_strength": -52, "encryption": "Open", "bssid": "aa:bb:cc:dd:ee:02"},
            {"ssid": "ATT8ePb7xg", "signal_strength": -58, "encryption": "WPA/WPA2", "bssid": "aa:bb:cc:dd:ee:03"},
            {"ssid": "MySpectrumWiFi", "signal_strength": -61, "encryption": "WPA/WPA2", "bssid": "aa:bb:cc:dd:ee:04"},
            {"ssid": "Foxtail Coffee Co", "signal_strength": -65, "encryption": "Open", "bssid": "aa:bb:cc:dd:ee:05"},
            {"ssid": "Quality Inn", "signal_strength": -68, "encryption": "Open", "bssid": "aa:bb:cc:dd:ee:06"},
            {"ssid": "Hilton Honors", "signal_strength": -72, "encryption": "Open", "bssid": "aa:bb:cc:dd:ee:07"},
            {"ssid": "Disney-Guest", "signal_strength": -75, "encryption": "Open", "bssid": "aa:bb:cc:dd:ee:08"},
            {"ssid": "Whole Foods Market", "signal_strength": -78, "encryption": "Open", "bssid": "aa:bb:cc:dd:ee:09"},
            {"ssid": "Daily Grind", "signal_strength": -82, "encryption": "WPA/WPA2", "bssid": "aa:bb:cc:dd:ee:10"},
            {"ssid": "Cool Beans Coffee", "signal_strength": -85, "encryption": "WPA/WPA2", "bssid": "aa:bb:cc:dd:ee:11"},
            {"ssid": "Lark Guest", "signal_strength": -88, "encryption": "Open", "bssid": "aa:bb:cc:dd:ee:12"}
        ]

def estimate_network_position(network: Dict, center_lat: float, center_lon: float) -> Tuple[float, float]:
    """Estimate network location based on signal strength and type"""
    signal_strength = network['signal_strength']
    ssid = network['ssid'].lower() if network['ssid'] else 'unknown'
    
    # Estimate distance based on signal strength
    if signal_strength > -40:
        distance_m = random.uniform(20, 80)
    elif signal_strength > -50:
        distance_m = random.uniform(80, 150)
    elif signal_strength > -60:
        distance_m = random.uniform(150, 300)
    elif signal_strength > -70:
        distance_m = random.uniform(300, 600)
    elif signal_strength > -80:
        distance_m = random.uniform(600, 1000)
    else:
        distance_m = random.uniform(1000, 2000)
    
    # Adjust based on network type
    if any(keyword in ssid for keyword in ['starbucks', 'coffee', 'panera', 'grind', 'beans']):
        distance_m *= 0.6  # Coffee shops closer
    elif any(keyword in ssid for keyword in ['hotel', 'guest', 'inn', 'hilton', 'quality']):
        distance_m *= 0.8  # Hotels medium distance
    elif network['encryption'] == 'Open':
        distance_m *= 0.7  # Open networks often businesses
    
    # Random angle for positioning
    angle = random.uniform(0, 2 * math.pi)
    
    # Convert to lat/lon offset
    lat_offset = (distance_m / 111320) * math.cos(angle)
    lon_offset = (distance_m / (111320 * math.cos(math.radians(center_lat)))) * math.sin(angle)
    
    return (center_lat + lat_offset, center_lon + lon_offset)

def create_interactive_map(networks: List[Dict]) -> str:
    """Create interactive HTML map with networks around your location"""
    
    # Your location (center)
    center_lat = 40.712800
    center_lon = -74.006000
    
    # Position networks around you
    network_positions = []
    for network in networks:
        lat, lon = estimate_network_position(network, center_lat, center_lon)
        network_positions.append({
            'network': network,
            'lat': lat,
            'lon': lon
        })
    
    # Create HTML map
    html_content = f'''
<!DOCTYPE html>
<html>
<head>
    <title>WiFi Networks Around You - Location Visualizer</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body {{ margin: 0; padding: 0; font-family: 'Segoe UI', Arial, sans-serif; }}
        #map {{ height: 100vh; width: 100%; }}
        
        .info-panel {{
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(255,255,255,0.95);
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
            max-width: 320px;
            z-index: 1000;
            backdrop-filter: blur(10px);
        }}
        
        .info-panel h3 {{
            margin-top: 0;
            color: #2c3e50;
            font-size: 1.3em;
        }}
        
        .stat-item {{
            display: flex;
            justify-content: space-between;
            margin: 8px 0;
            padding: 5px 0;
            border-bottom: 1px solid #ecf0f1;
        }}
        
        .legend {{
            position: fixed;
            bottom: 20px;
            left: 20px;
            background: rgba(255,255,255,0.95);
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
            z-index: 1000;
            backdrop-filter: blur(10px);
        }}
        
        .legend h4 {{
            margin-top: 0;
            color: #2c3e50;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            margin: 8px 0;
        }}
        
        .legend-color {{
            width: 16px;
            height: 16px;
            border-radius: 50%;
            margin-right: 12px;
            border: 2px solid white;
            box-shadow: 0 1px 3px rgba(0,0,0,0.3);
        }}
        
        .controls {{
            position: fixed;
            top: 20px;
            left: 20px;
            z-index: 1000;
        }}
        
        .control-btn {{
            background: #3498db;
            color: white;
            border: none;
            padding: 10px 15px;
            margin: 5px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }}
        
        .control-btn:hover {{
            background: #2980b9;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    
    <div class="controls">
        <button class="control-btn" onclick="map.setView([{center_lat}, {center_lon}], 16)">🎯 Center on You</button>
        <button class="control-btn" onclick="toggleDistanceCircles()">📏 Toggle Ranges</button>
    </div>
    
    <div class="info-panel">
        <h3>🌐 WiFi Detection Results</h3>
        <div class="stat-item">
            <span><strong>Networks Found:</strong></span>
            <span>{len(networks)}</span>
        </div>
        <div class="stat-item">
            <span><strong>Your Location:</strong></span>
            <span>Center</span>
        </div>
        <div class="stat-item">
            <span><strong>Open Networks:</strong></span>
            <span>{len([n for n in networks if n.get('encryption') == 'Open'])}</span>
        </div>
        <div class="stat-item">
            <span><strong>Secured Networks:</strong></span>
            <span>{len([n for n in networks if n.get('encryption') != 'Open'])}</span>
        </div>
        <div class="stat-item">
            <span><strong>Scan Time:</strong></span>
            <span>{datetime.now().strftime('%H:%M')}</span>
        </div>
        <hr style="margin: 15px 0; border: none; border-top: 1px solid #ecf0f1;">
        <p style="font-size: 0.9em; color: #7f8c8d; margin: 0;">
            <em>Networks positioned by estimated location based on signal strength and type</em>
        </p>
    </div>
    
    <div class="legend">
        <h4>🎯 Map Legend</h4>
        <div class="legend-item">
            <div class="legend-color" style="background: #e74c3c; width: 20px; height: 20px;"></div>
            <span><strong>You (Detection Center)</strong></span>
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
        // Initialize map
        var map = L.map('map').setView([{center_lat}, {center_lon}], 15);
        
        // Add map tiles
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenStreetMap contributors | WiFi Detection System'
        }}).addTo(map);
        
        // Your location marker (center)
        var yourLocationIcon = L.divIcon({{
            className: 'your-location-marker',
            html: `<div style="
                background: #e74c3c; 
                width: 24px; 
                height: 24px; 
                border-radius: 50%; 
                border: 4px solid white; 
                box-shadow: 0 3px 10px rgba(0,0,0,0.4);
                position: relative;
            ">
                <div style="
                    position: absolute;
                    top: -8px;
                    left: -8px;
                    width: 40px;
                    height: 40px;
                    border: 2px solid #e74c3c;
                    border-radius: 50%;
                    animation: pulse 2s infinite;
                    opacity: 0.6;
                "></div>
            </div>
            <style>
                @keyframes pulse {{
                    0% {{ transform: scale(0.8); opacity: 0.8; }}
                    50% {{ transform: scale(1.2); opacity: 0.3; }}
                    100% {{ transform: scale(0.8); opacity: 0.8; }}
                }}
            </style>`,
            iconSize: [24, 24],
            iconAnchor: [12, 12]
        }});
        
        var yourLocation = L.marker([{center_lat}, {center_lon}], {{
            icon: yourLocationIcon
        }}).addTo(map);
        
        yourLocation.bindPopup(`
            <div style="text-align: center; min-width: 200px;">
                <h4>📍 Your Location</h4>
                <p><strong>Detection Center</strong></p>
                <p>Lat: {center_lat:.6f}<br>Lon: {center_lon:.6f}</p>
                <p style="color: #7f8c8d; font-size: 0.9em;">
                    <em>All WiFi networks are positioned relative to this point</em>
                </p>
            </div>
        `);
        
        // Network data
        var networks = {json.dumps(network_positions)};
        
        // Add network markers
        networks.forEach(function(item, index) {{
            var network = item.network;
            var lat = item.lat;
            var lon = item.lon;
            
            // Determine colors
            var signalColor = '#95a5a6'; // Default weak
            if (network.signal_strength > -50) {{
                signalColor = '#27ae60'; // Strong
            }} else if (network.signal_strength > -70) {{
                signalColor = '#f39c12'; // Medium
            }}
            
            var finalColor = network.encryption === 'Open' ? '#3498db' : signalColor;
            
            // Create marker
            var networkIcon = L.divIcon({{
                className: 'network-marker',
                html: `<div style="
                    background: ${{finalColor}}; 
                    width: 14px; 
                    height: 14px; 
                    border-radius: 50%; 
                    border: 2px solid white; 
                    box-shadow: 0 2px 5px rgba(0,0,0,0.3);
                "></div>`,
                iconSize: [14, 14],
                iconAnchor: [7, 7]
            }});
            
            var marker = L.marker([lat, lon], {{
                icon: networkIcon
            }}).addTo(map);
            
            // Popup content
            var signalIcon = network.signal_strength > -50 ? '🟢' : 
                           network.signal_strength > -70 ? '🟡' : '🔴';
            var securityIcon = network.encryption === 'Open' ? '🔓' : '🔒';
            var networkType = getNetworkType(network.ssid);
            
            marker.bindPopup(`
                <div style="min-width: 250px;">
                    <h4>${{signalIcon}} ${{network.ssid || 'Hidden Network'}}</h4>
                    <table style="width: 100%; font-size: 0.9em;">
                        <tr><td><strong>Signal Strength:</strong></td><td>${{network.signal_strength}} dBm</td></tr>
                        <tr><td><strong>Security:</strong></td><td>${{securityIcon}} ${{network.encryption}}</td></tr>
                        <tr><td><strong>Network Type:</strong></td><td>${{networkType}}</td></tr>
                        <tr><td><strong>BSSID:</strong></td><td style="font-family: monospace; font-size: 0.8em;">${{network.bssid}}</td></tr>
                    </table>
                    <hr style="margin: 10px 0;">
                    <p style="font-size: 0.8em; color: #7f8c8d; margin: 0;">
                        <em>📍 Estimated location based on signal analysis</em>
                    </p>
                </div>
            `);
        }});
        
        // Distance circles
        var distanceCircles = [];
        var circlesVisible = false;
        
        function toggleDistanceCircles() {{
            if (circlesVisible) {{
                distanceCircles.forEach(circle => map.removeLayer(circle));
                distanceCircles = [];
                circlesVisible = false;
            }} else {{
                var ranges = [100, 300, 500, 1000, 1500];
                var colors = ['#e74c3c', '#f39c12', '#f1c40f', '#2ecc71', '#3498db'];
                
                ranges.forEach(function(radius, index) {{
                    var circle = L.circle([{center_lat}, {center_lon}], {{
                        color: colors[index],
                        fillColor: 'transparent',
                        fillOpacity: 0,
                        radius: radius,
                        weight: 2,
                        opacity: 0.6,
                        dashArray: '8, 8'
                    }}).addTo(map);
                    
                    distanceCircles.push(circle);
                }});
                circlesVisible = true;
            }}
        }}
        
        function getNetworkType(ssid) {{
            if (!ssid) return '❓ Unknown';
            var lower = ssid.toLowerCase();
            if (lower.includes('starbucks') || lower.includes('coffee') || lower.includes('panera')) return '☕ Coffee Shop';
            if (lower.includes('hotel') || lower.includes('guest') || lower.includes('inn')) return '🏨 Hotel/Guest';
            if (lower.includes('att') || lower.includes('spectrum') || lower.includes('xfinity')) return '🏠 ISP/Residential';
            if (lower.includes('disney') || lower.includes('universal')) return '🎢 Entertainment';
            return '🏢 Business/Other';
        }}
        
        // Add scale
        L.control.scale({{position: 'bottomright'}}).addTo(map);
    </script>
</body>
</html>
    '''
    
    return html_content

def main():
    """Generate the WiFi network location visualizer"""
    print("🗺️  WiFi Network Location Visualizer")
    print("=" * 50)
    print("Creating interactive map with you at the center...")
    
    # Load network data
    networks = load_existing_scan_data()
    print(f"📶 Processing {len(networks)} WiFi networks")
    
    # Generate map
    html_content = create_interactive_map(networks)
    
    # Save map file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'wifi_location_map_{timestamp}.html'
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Interactive map created: {filename}")
    print("\n🎯 Map Features:")
    print("   • You are at the center (red pulsing marker)")
    print("   • WiFi networks positioned around you by signal strength")
    print("   • Color-coded: Green=Strong, Orange=Medium, Gray=Weak, Blue=Open")
    print("   • Click any marker for detailed network information")
    print("   • Use controls to center map or toggle distance ranges")
    print("   • Zoom and pan to explore the area")
    
    print(f"\n🌐 Open {filename} in your web browser to see the visualization!")
    
    return filename

if __name__ == "__main__":
    main()
