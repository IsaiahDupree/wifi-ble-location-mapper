#!/usr/bin/env python3
"""
Simple web demo without external dependencies
Uses built-in Python HTTP server with basic HTML interface
"""

import http.server
import socketserver
import json
import threading
import time
from urllib.parse import urlparse, parse_qs
from wifi_scanner import WiFiScanner
from location_tracker import LocationTracker
from signal_mapper import SignalMapper

# Global instances to avoid initialization issues
wifi_scanner = WiFiScanner()
location_tracker = LocationTracker()
signal_mapper = SignalMapper()

class DetectionHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/':
            self.serve_dashboard()
        elif parsed_path.path == '/api/scan':
            self.serve_scan_data()
        elif parsed_path.path == '/api/status':
            self.serve_status()
        else:
            super().do_GET()
    
    def serve_dashboard(self):
        html_content = '''
<!DOCTYPE html>
<html>
<head>
    <title>WiFi Detection System</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; background: #2c3e50; color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; }
        .stat-value { font-size: 2em; font-weight: bold; color: #3498db; }
        .networks { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .network-item { padding: 10px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }
        .signal-strength { padding: 4px 8px; border-radius: 4px; color: white; font-weight: bold; }
        .signal-excellent { background: #27ae60; }
        .signal-good { background: #f39c12; }
        .signal-poor { background: #e74c3c; }
        .scan-btn { background: #3498db; color: white; border: none; padding: 15px 30px; font-size: 16px; border-radius: 5px; cursor: pointer; margin: 10px; }
        .scan-btn:hover { background: #2980b9; }
        .loading { display: none; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌐 WiFi Detection System</h1>
            <p>Real-time WiFi Network Scanner</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value" id="networkCount">0</div>
                <div>Networks Found</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="strongestSignal">-100</div>
                <div>Strongest Signal (dBm)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="openNetworks">0</div>
                <div>Open Networks</div>
            </div>
        </div>
        
        <div style="text-align: center; margin-bottom: 20px;">
            <button class="scan-btn" onclick="scanNetworks()">🔍 Scan WiFi Networks</button>
            <div class="loading" id="loading">Scanning... Please wait</div>
        </div>
        
        <div class="networks">
            <h3>📶 Detected Networks</h3>
            <div id="networkList">
                <p style="text-align: center; color: #666;">Click "Scan WiFi Networks" to start detection</p>
            </div>
        </div>
    </div>

    <script>
        function scanNetworks() {
            document.getElementById('loading').style.display = 'block';
            document.querySelector('.scan-btn').disabled = true;
            
            fetch('/api/scan')
                .then(response => response.json())
                .then(data => {
                    updateDisplay(data);
                    document.getElementById('loading').style.display = 'none';
                    document.querySelector('.scan-btn').disabled = false;
                })
                .catch(error => {
                    console.error('Error:', error);
                    document.getElementById('loading').style.display = 'none';
                    document.querySelector('.scan-btn').disabled = false;
                });
        }
        
        function updateDisplay(networks) {
            // Update stats
            document.getElementById('networkCount').textContent = networks.length;
            
            const signals = networks.map(n => n.signal_strength);
            const strongest = Math.max(...signals);
            document.getElementById('strongestSignal').textContent = strongest > -100 ? strongest : 'N/A';
            
            const openCount = networks.filter(n => n.encryption === 'Open').length;
            document.getElementById('openNetworks').textContent = openCount;
            
            // Update network list
            const networkList = document.getElementById('networkList');
            if (networks.length === 0) {
                networkList.innerHTML = '<p style="text-align: center; color: #666;">No networks detected</p>';
                return;
            }
            
            const sortedNetworks = networks.sort((a, b) => b.signal_strength - a.signal_strength);
            
            networkList.innerHTML = sortedNetworks.map(network => {
                const signalClass = network.signal_strength > -60 ? 'signal-excellent' : 
                                  network.signal_strength > -70 ? 'signal-good' : 'signal-poor';
                
                return `
                    <div class="network-item">
                        <div>
                            <strong>${network.ssid || 'Hidden Network'}</strong><br>
                            <small style="color: #666;">${network.encryption} • ${network.bssid}</small>
                        </div>
                        <div class="signal-strength ${signalClass}">
                            ${network.signal_strength} dBm
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        // Auto-refresh every 30 seconds
        setInterval(() => {
            if (!document.querySelector('.scan-btn').disabled) {
                scanNetworks();
            }
        }, 30000);
    </script>
</body>
</html>
        '''
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html_content.encode())
    
    def serve_scan_data(self):
        try:
            # Perform WiFi scan
            networks = wifi_scanner.scan_once()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = json.dumps(networks, indent=2)
            self.wfile.write(response.encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            error_response = json.dumps({'error': str(e)})
            self.wfile.write(error_response.encode())
    
    def serve_status(self):
        status = {
            'status': 'running',
            'timestamp': time.time(),
            'system': 'WiFi Detection System v1.0'
        }
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = json.dumps(status)
        self.wfile.write(response.encode())

def start_server():
    PORT = 8082
    
    with socketserver.TCPServer(("", PORT), DetectionHandler) as httpd:
        print(f"🌐 WiFi Detection System running at http://localhost:{PORT}")
        print("🔍 Open the URL in your browser to see the live interface")
        print("Press Ctrl+C to stop the server")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Server stopped")

if __name__ == "__main__":
    start_server()
