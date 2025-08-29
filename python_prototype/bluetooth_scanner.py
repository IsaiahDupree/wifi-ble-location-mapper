import asyncio
import json
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable
import platform

try:
    from bleak import BleakScanner, BleakError
    BLEAK_AVAILABLE = True
except ImportError:
    BLEAK_AVAILABLE = False
    print("Warning: bleak not available. Install with: pip install bleak")

try:
    import bluetooth
    PYBLUEZ_AVAILABLE = True
except ImportError:
    PYBLUEZ_AVAILABLE = False
    print("Warning: pybluez not available. Install with: pip install pybluez")

class BluetoothScanner:
    def __init__(self):
        self.scanning = False
        self.scan_results = []
        self.scan_thread = None
        self.callback = None
        self.ble_devices = {}
        self.classic_devices = {}
        
    def set_callback(self, callback: Callable):
        """Set callback function for real-time updates"""
        self.callback = callback
    
    async def scan_ble_devices(self, duration: int = 10) -> List[Dict]:
        """Scan for BLE devices using bleak"""
        if not BLEAK_AVAILABLE:
            return []
        
        devices = []
        try:
            print(f"Scanning for BLE devices for {duration} seconds...")
            discovered_devices = await BleakScanner.discover(timeout=duration)
            
            for device in discovered_devices:
                device_info = {
                    'name': device.name or 'Unknown',
                    'address': device.address,
                    'rssi': device.rssi,
                    'type': 'BLE',
                    'manufacturer_data': dict(device.metadata.get('manufacturer_data', {})),
                    'service_uuids': list(device.metadata.get('uuids', [])),
                    'timestamp': datetime.now().isoformat()
                }
                devices.append(device_info)
                self.ble_devices[device.address] = device_info
            
        except Exception as e:
            print(f"Error scanning BLE devices: {e}")
        
        return devices
    
    def scan_classic_bluetooth(self, duration: int = 10) -> List[Dict]:
        """Scan for classic Bluetooth devices using pybluez"""
        if not PYBLUEZ_AVAILABLE:
            return []
        
        devices = []
        try:
            print(f"Scanning for classic Bluetooth devices for {duration} seconds...")
            nearby_devices = bluetooth.discover_devices(duration=duration, lookup_names=True, lookup_class=True)
            
            for addr, name, device_class in nearby_devices:
                device_info = {
                    'name': name or 'Unknown',
                    'address': addr,
                    'device_class': device_class,
                    'type': 'Classic',
                    'rssi': self.get_rssi_estimate(addr),
                    'timestamp': datetime.now().isoformat()
                }
                devices.append(device_info)
                self.classic_devices[addr] = device_info
                
        except Exception as e:
            print(f"Error scanning classic Bluetooth devices: {e}")
        
        return devices
    
    def get_rssi_estimate(self, address: str) -> int:
        """Estimate RSSI for classic Bluetooth (not directly available in pybluez)"""
        # This is a placeholder - actual RSSI requires lower-level access
        # For now, return a default value
        return -50
    
    def scan_once(self, ble_duration: int = 10, classic_duration: int = 10) -> List[Dict]:
        """Perform a single Bluetooth scan (both BLE and Classic)"""
        all_devices = []
        
        # Scan BLE devices
        if BLEAK_AVAILABLE:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                ble_devices = loop.run_until_complete(self.scan_ble_devices(ble_duration))
                all_devices.extend(ble_devices)
                loop.close()
            except Exception as e:
                print(f"Error in BLE scan: {e}")
        
        # Scan Classic Bluetooth devices
        if PYBLUEZ_AVAILABLE and platform.system().lower() != 'windows':
            # pybluez classic scanning works better on Linux
            classic_devices = self.scan_classic_bluetooth(classic_duration)
            all_devices.extend(classic_devices)
        
        return all_devices
    
    def start_continuous_scan(self, interval: int = 30, ble_duration: int = 10, classic_duration: int = 10):
        """Start continuous Bluetooth scanning"""
        if self.scanning:
            return
        
        self.scanning = True
        self.scan_thread = threading.Thread(
            target=self._scan_loop, 
            args=(interval, ble_duration, classic_duration)
        )
        self.scan_thread.daemon = True
        self.scan_thread.start()
    
    def stop_scanning(self):
        """Stop continuous scanning"""
        self.scanning = False
        if self.scan_thread:
            self.scan_thread.join()
    
    def _scan_loop(self, interval: int, ble_duration: int, classic_duration: int):
        """Internal scanning loop"""
        while self.scanning:
            try:
                results = self.scan_once(ble_duration, classic_duration)
                self.scan_results = results
                
                if self.callback and results:
                    self.callback('bluetooth', results)
                
                print(f"Found {len(results)} Bluetooth devices")
                for device in results[:5]:  # Show first 5
                    print(f"  {device['name']} ({device['type']}): {device.get('rssi', 'N/A')} dBm")
                
            except Exception as e:
                print(f"Error in Bluetooth scan loop: {e}")
            
            time.sleep(interval)
    
    def get_latest_results(self) -> List[Dict]:
        """Get the latest scan results"""
        return self.scan_results.copy()
    
    def get_device_details(self, address: str) -> Optional[Dict]:
        """Get detailed information about a specific device"""
        if address in self.ble_devices:
            return self.ble_devices[address]
        elif address in self.classic_devices:
            return self.classic_devices[address]
        return None
    
    def export_results(self, filename: str):
        """Export scan results to JSON file"""
        try:
            export_data = {
                'scan_results': self.scan_results,
                'ble_devices': self.ble_devices,
                'classic_devices': self.classic_devices,
                'export_timestamp': datetime.now().isoformat()
            }
            
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)
            print(f"Bluetooth results exported to {filename}")
        except Exception as e:
            print(f"Error exporting Bluetooth results: {e}")
    
    def analyze_device_types(self) -> Dict[str, int]:
        """Analyze and categorize discovered devices"""
        analysis = {
            'total_devices': len(self.scan_results),
            'ble_devices': 0,
            'classic_devices': 0,
            'named_devices': 0,
            'unknown_devices': 0
        }
        
        for device in self.scan_results:
            if device['type'] == 'BLE':
                analysis['ble_devices'] += 1
            else:
                analysis['classic_devices'] += 1
            
            if device['name'] and device['name'] != 'Unknown':
                analysis['named_devices'] += 1
            else:
                analysis['unknown_devices'] += 1
        
        return analysis

if __name__ == "__main__":
    scanner = BluetoothScanner()
    
    print("Starting Bluetooth scanner...")
    print("This may take a while as Bluetooth scanning is slower than WiFi...")
    
    # Check available libraries
    print(f"BLE scanning available: {BLEAK_AVAILABLE}")
    print(f"Classic Bluetooth scanning available: {PYBLUEZ_AVAILABLE}")
    
    if not BLEAK_AVAILABLE and not PYBLUEZ_AVAILABLE:
        print("No Bluetooth libraries available. Please install bleak and/or pybluez.")
        exit(1)
    
    print("\nPerforming single scan...")
    results = scanner.scan_once(ble_duration=15, classic_duration=10)
    
    print(f"\nFound {len(results)} Bluetooth devices:")
    for device in results:
        print(f"Name: {device['name']}")
        print(f"  Address: {device['address']}")
        print(f"  Type: {device['type']}")
        print(f"  RSSI: {device.get('rssi', 'N/A')} dBm")
        if device['type'] == 'BLE' and device.get('service_uuids'):
            print(f"  Services: {', '.join(device['service_uuids'][:3])}...")
        print()
    
    # Analyze results
    analysis = scanner.analyze_device_types()
    print("Device Analysis:")
    for key, value in analysis.items():
        print(f"  {key.replace('_', ' ').title()}: {value}")
    
    # Export results
    scanner.scan_results = results
    scanner.export_results('bluetooth_scan_results.json')
