import time
import json
import threading
from datetime import datetime
from typing import Dict, List, Optional
import subprocess
import platform
import re

class WiFiScanner:
    def __init__(self):
        self.scanning = False
        self.scan_results = []
        self.scan_thread = None
        self.callback = None
        
    def set_callback(self, callback):
        """Set callback function for real-time updates"""
        self.callback = callback
    
    def scan_networks_windows(self) -> List[Dict]:
        """Scan WiFi networks on Windows using netsh"""
        try:
            # Get available networks
            result = subprocess.run(['netsh', 'wlan', 'show', 'profiles'], 
                                  capture_output=True, text=True, encoding='utf-8')
            
            networks = []
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'All User Profile' in line:
                        ssid = line.split(':')[1].strip()
                        networks.append(ssid)
            
            # Get detailed info for each network
            detailed_networks = []
            for ssid in networks:
                try:
                    detail_result = subprocess.run(['netsh', 'wlan', 'show', 'profile', ssid, 'key=clear'], 
                                                 capture_output=True, text=True, encoding='utf-8')
                    if detail_result.returncode == 0:
                        network_info = self.parse_network_details(detail_result.stdout, ssid)
                        if network_info:
                            detailed_networks.append(network_info)
                except Exception as e:
                    print(f"Error getting details for {ssid}: {e}")
            
            # Get current signal strengths
            signal_result = subprocess.run(['netsh', 'wlan', 'show', 'interface'], 
                                         capture_output=True, text=True, encoding='utf-8')
            
            if signal_result.returncode == 0:
                self.update_signal_strengths(detailed_networks, signal_result.stdout)
            
            return detailed_networks
            
        except Exception as e:
            print(f"Error scanning WiFi networks: {e}")
            return []
    
    def parse_network_details(self, output: str, ssid: str) -> Optional[Dict]:
        """Parse network details from netsh output"""
        try:
            network = {
                'ssid': ssid,
                'bssid': 'Unknown',
                'signal_strength': -100,
                'frequency': 'Unknown',
                'channel': 'Unknown',
                'encryption': 'Unknown',
                'timestamp': datetime.now().isoformat()
            }
            
            lines = output.split('\n')
            for line in lines:
                line = line.strip()
                if 'Security key' in line:
                    network['encryption'] = 'WPA/WPA2' if 'Present' in line else 'Open'
                elif 'Authentication' in line:
                    auth = line.split(':')[1].strip() if ':' in line else 'Unknown'
                    network['authentication'] = auth
            
            return network
        except Exception as e:
            print(f"Error parsing network details: {e}")
            return None
    
    def update_signal_strengths(self, networks: List[Dict], interface_output: str):
        """Update signal strengths from interface output"""
        try:
            lines = interface_output.split('\n')
            current_ssid = None
            
            for line in lines:
                line = line.strip()
                if 'SSID' in line and ':' in line:
                    current_ssid = line.split(':')[1].strip()
                elif 'Signal' in line and current_ssid:
                    signal_match = re.search(r'(\d+)%', line)
                    if signal_match:
                        signal_percent = int(signal_match.group(1))
                        # Convert percentage to dBm (approximate)
                        signal_dbm = -100 + (signal_percent * 70 / 100)
                        
                        # Update matching network
                        for network in networks:
                            if network['ssid'] == current_ssid:
                                network['signal_strength'] = round(signal_dbm, 1)
                                break
        except Exception as e:
            print(f"Error updating signal strengths: {e}")
    
    def scan_networks_linux(self) -> List[Dict]:
        """Scan WiFi networks on Linux using iwlist"""
        try:
            result = subprocess.run(['iwlist', 'scan'], capture_output=True, text=True)
            if result.returncode != 0:
                # Try with sudo
                result = subprocess.run(['sudo', 'iwlist', 'scan'], capture_output=True, text=True)
            
            if result.returncode == 0:
                return self.parse_iwlist_output(result.stdout)
            else:
                print("Error: Unable to scan WiFi networks. Make sure you have proper permissions.")
                return []
        except Exception as e:
            print(f"Error scanning WiFi networks on Linux: {e}")
            return []
    
    def parse_iwlist_output(self, output: str) -> List[Dict]:
        """Parse iwlist scan output"""
        networks = []
        current_network = None
        
        for line in output.split('\n'):
            line = line.strip()
            
            if 'Cell' in line and 'Address:' in line:
                if current_network:
                    networks.append(current_network)
                current_network = {
                    'bssid': line.split('Address: ')[1],
                    'ssid': 'Unknown',
                    'signal_strength': -100,
                    'frequency': 'Unknown',
                    'channel': 'Unknown',
                    'encryption': 'Unknown',
                    'timestamp': datetime.now().isoformat()
                }
            elif current_network:
                if 'ESSID:' in line:
                    ssid = line.split('ESSID:')[1].strip('"')
                    current_network['ssid'] = ssid if ssid != '""' else 'Hidden'
                elif 'Signal level=' in line:
                    signal_match = re.search(r'Signal level=(-?\d+)', line)
                    if signal_match:
                        current_network['signal_strength'] = int(signal_match.group(1))
                elif 'Frequency:' in line:
                    freq_match = re.search(r'Frequency:(\d+\.?\d*)', line)
                    if freq_match:
                        current_network['frequency'] = f"{freq_match.group(1)} GHz"
                elif 'Encryption key:' in line:
                    current_network['encryption'] = 'WPA/WPA2' if 'on' in line else 'Open'
        
        if current_network:
            networks.append(current_network)
        
        return networks
    
    def scan_once(self) -> List[Dict]:
        """Perform a single WiFi scan"""
        system = platform.system().lower()
        
        if system == 'windows':
            return self.scan_networks_windows()
        elif system == 'linux':
            return self.scan_networks_linux()
        else:
            print(f"Unsupported operating system: {system}")
            return []
    
    def start_continuous_scan(self, interval: int = 5):
        """Start continuous WiFi scanning"""
        if self.scanning:
            return
        
        self.scanning = True
        self.scan_thread = threading.Thread(target=self._scan_loop, args=(interval,))
        self.scan_thread.daemon = True
        self.scan_thread.start()
    
    def stop_scanning(self):
        """Stop continuous scanning"""
        self.scanning = False
        if self.scan_thread:
            self.scan_thread.join()
    
    def _scan_loop(self, interval: int):
        """Internal scanning loop"""
        while self.scanning:
            try:
                results = self.scan_once()
                self.scan_results = results
                
                if self.callback and results:
                    self.callback('wifi', results)
                
                print(f"Found {len(results)} WiFi networks")
                for network in results[:5]:  # Show first 5
                    print(f"  {network['ssid']}: {network['signal_strength']} dBm")
                
            except Exception as e:
                print(f"Error in scan loop: {e}")
            
            time.sleep(interval)
    
    def get_latest_results(self) -> List[Dict]:
        """Get the latest scan results"""
        return self.scan_results.copy()
    
    def export_results(self, filename: str):
        """Export scan results to JSON file"""
        try:
            with open(filename, 'w') as f:
                json.dump(self.scan_results, f, indent=2)
            print(f"Results exported to {filename}")
        except Exception as e:
            print(f"Error exporting results: {e}")

if __name__ == "__main__":
    scanner = WiFiScanner()
    
    print("Starting WiFi scanner...")
    print("Performing single scan...")
    
    results = scanner.scan_once()
    print(f"\nFound {len(results)} networks:")
    
    for network in results:
        print(f"SSID: {network['ssid']}")
        print(f"  Signal: {network['signal_strength']} dBm")
        print(f"  Encryption: {network['encryption']}")
        print(f"  BSSID: {network['bssid']}")
        print()
    
    # Export results
    scanner.scan_results = results
    scanner.export_results('wifi_scan_results.json')
