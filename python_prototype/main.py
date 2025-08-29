#!/usr/bin/env python3
"""
WiFi & Bluetooth Location Detection System - Main Application
Integrates WiFi scanning, Bluetooth detection, location tracking, and signal mapping
"""

import time
import json
import threading
import signal
import sys
from datetime import datetime
from typing import Dict, List, Optional

from wifi_scanner import WiFiScanner
from bluetooth_scanner import BluetoothScanner
from location_tracker import LocationTracker
from signal_mapper import SignalMapper

class CommunicationDetectionSystem:
    def __init__(self):
        self.wifi_scanner = WiFiScanner()
        self.bluetooth_scanner = BluetoothScanner()
        self.location_tracker = LocationTracker()
        self.signal_mapper = SignalMapper()
        
        self.running = False
        self.data_lock = threading.Lock()
        self.latest_data = {
            'wifi': [],
            'bluetooth': [],
            'location': None,
            'timestamp': None
        }
        
        # Set up callbacks for real-time data processing
        self.wifi_scanner.set_callback(self._on_data_update)
        self.bluetooth_scanner.set_callback(self._on_data_update)
        self.location_tracker.set_callback(self._on_data_update)
        
        # Configuration
        self.config = {
            'wifi_scan_interval': 10,
            'bluetooth_scan_interval': 30,
            'location_update_interval': 5,
            'data_export_interval': 300,  # 5 minutes
            'auto_export': True
        }
    
    def _on_data_update(self, data_type: str, data):
        """Callback for real-time data updates"""
        with self.data_lock:
            self.latest_data[data_type] = data
            self.latest_data['timestamp'] = datetime.now().isoformat()
            
            # If we have location and signal data, add to signal mapper
            if (data_type in ['wifi', 'bluetooth'] and 
                self.latest_data['location'] is not None):
                
                self.signal_mapper.add_signal_reading(
                    self.latest_data['location'],
                    self.latest_data['wifi'],
                    self.latest_data['bluetooth']
                )
    
    def start_system(self):
        """Start all detection systems"""
        print("🚀 Starting Communication Detection System...")
        print("=" * 50)
        
        self.running = True
        
        # Start location tracking first
        print("📍 Starting location tracking...")
        self.location_tracker.start_tracking(self.config['location_update_interval'])
        time.sleep(2)  # Give GPS time to initialize
        
        # Start WiFi scanning
        print("📶 Starting WiFi scanning...")
        self.wifi_scanner.start_continuous_scan(self.config['wifi_scan_interval'])
        
        # Start Bluetooth scanning
        print("🔵 Starting Bluetooth scanning...")
        self.bluetooth_scanner.start_continuous_scan(
            self.config['bluetooth_scan_interval'],
            ble_duration=10,
            classic_duration=5
        )
        
        print("✅ All systems started successfully!")
        print("\nReal-time monitoring active...")
        print("Press Ctrl+C to stop and export data")
        print("-" * 50)
        
        # Start monitoring loop
        self._monitoring_loop()
    
    def _monitoring_loop(self):
        """Main monitoring and status loop"""
        last_export = time.time()
        status_counter = 0
        
        try:
            while self.running:
                time.sleep(5)  # Update every 5 seconds
                status_counter += 1
                
                # Show status every 6 iterations (30 seconds)
                if status_counter % 6 == 0:
                    self._print_status()
                
                # Auto-export data periodically
                if (self.config['auto_export'] and 
                    time.time() - last_export > self.config['data_export_interval']):
                    self._export_all_data()
                    last_export = time.time()
                
        except KeyboardInterrupt:
            print("\n\n🛑 Shutdown requested by user")
            self.stop_system()
    
    def _print_status(self):
        """Print current system status"""
        with self.data_lock:
            wifi_count = len(self.latest_data['wifi'])
            bluetooth_count = len(self.latest_data['bluetooth'])
            location = self.latest_data['location']
            
        print(f"\n📊 Status Update - {datetime.now().strftime('%H:%M:%S')}")
        print(f"   WiFi Networks: {wifi_count}")
        print(f"   Bluetooth Devices: {bluetooth_count}")
        
        if location:
            if 'latitude' in location:
                print(f"   Location: {location['latitude']:.6f}, {location['longitude']:.6f}")
                print(f"   GPS Source: {location['source']} ({location.get('satellites', 0)} sats)")
            else:
                print(f"   Location: Indoor positioning")
        else:
            print("   Location: Not available")
        
        # Signal mapping stats
        total_readings = len(self.signal_mapper.signal_data)
        print(f"   Total Signal Readings: {total_readings}")
        
        # Show top WiFi networks by signal strength
        if self.latest_data['wifi']:
            strongest_wifi = max(self.latest_data['wifi'], 
                               key=lambda x: x['signal_strength'])
            print(f"   Strongest WiFi: {strongest_wifi['ssid']} ({strongest_wifi['signal_strength']} dBm)")
        
        # Show Bluetooth devices
        if self.latest_data['bluetooth']:
            for device in self.latest_data['bluetooth'][:2]:  # Show first 2
                rssi = device.get('rssi', 'N/A')
                print(f"   Bluetooth: {device['name']} ({rssi} dBm)")
    
    def stop_system(self):
        """Stop all detection systems"""
        print("\n🔄 Stopping all systems...")
        
        self.running = False
        
        # Stop all scanners
        self.wifi_scanner.stop_scanning()
        self.bluetooth_scanner.stop_scanning()
        self.location_tracker.stop_tracking()
        
        print("✅ All systems stopped")
        
        # Export final data
        self._export_all_data()
        self._generate_summary_report()
    
    def _export_all_data(self):
        """Export data from all systems"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        print(f"\n💾 Exporting data ({timestamp})...")
        
        try:
            # Export individual system data
            self.wifi_scanner.export_results(f'wifi_data_{timestamp}.json')
            self.bluetooth_scanner.export_results(f'bluetooth_data_{timestamp}.json')
            self.location_tracker.export_track(f'location_track_{timestamp}.json')
            self.signal_mapper.export_data(f'signal_mapping_{timestamp}.json')
            
            # Export combined data
            combined_data = {
                'export_timestamp': datetime.now().isoformat(),
                'config': self.config,
                'latest_data': self.latest_data,
                'summary': {
                    'wifi_networks_found': len(set(
                        network['bssid'] for reading in self.signal_mapper.signal_data
                        for network in reading['wifi_networks']
                    )),
                    'bluetooth_devices_found': len(set(
                        device['address'] for reading in self.signal_mapper.signal_data
                        for device in reading['bluetooth_devices']
                    )),
                    'total_signal_readings': len(self.signal_mapper.signal_data),
                    'distance_traveled': self.location_tracker.calculate_distance_traveled(),
                    'session_duration': time.time() - getattr(self, 'start_time', time.time())
                }
            }
            
            with open(f'combined_data_{timestamp}.json', 'w') as f:
                json.dump(combined_data, f, indent=2, default=str)
            
            print(f"✅ Data exported successfully")
            
        except Exception as e:
            print(f"❌ Error exporting data: {e}")
    
    def _generate_summary_report(self):
        """Generate a summary report of the detection session"""
        print("\n" + "=" * 60)
        print("📋 SESSION SUMMARY REPORT")
        print("=" * 60)
        
        # WiFi Analysis
        wifi_analysis = self.signal_mapper.analyze_coverage('wifi')
        print(f"\n📶 WiFi Detection:")
        print(f"   Unique Networks: {wifi_analysis['total_networks']}")
        print(f"   Scan Locations: {wifi_analysis['total_locations']}")
        print(f"   Total Readings: {wifi_analysis['total_readings']}")
        
        if wifi_analysis['network_stats']:
            strongest_network = max(
                wifi_analysis['network_stats'].items(),
                key=lambda x: x[1]['max_signal']
            )
            print(f"   Strongest Signal: {strongest_network[1]['max_signal']:.1f} dBm")
        
        # Bluetooth Analysis
        bt_analysis = self.signal_mapper.analyze_coverage('bluetooth')
        print(f"\n🔵 Bluetooth Detection:")
        print(f"   Unique Devices: {bt_analysis['total_networks']}")
        print(f"   Scan Locations: {bt_analysis['total_locations']}")
        print(f"   Total Readings: {bt_analysis['total_readings']}")
        
        # Location Analysis
        distance = self.location_tracker.calculate_distance_traveled()
        print(f"\n📍 Location Tracking:")
        print(f"   Distance Traveled: {distance:.1f} meters")
        print(f"   Location Points: {len(self.location_tracker.location_history)}")
        
        current_location = self.location_tracker.get_current_location()
        if current_location:
            print(f"   Final Location: {current_location['latitude']:.6f}, {current_location['longitude']:.6f}")
            print(f"   Location Source: {current_location['source']}")
        
        print("\n" + "=" * 60)
        print("🎯 Next Steps:")
        print("   1. Review exported JSON files for detailed data")
        print("   2. Use signal mapping data for VR visualization")
        print("   3. Deploy to ESP32/Raspberry Pi for field use")
        print("=" * 60)

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print("\n\n🛑 Interrupt received, shutting down...")
    sys.exit(0)

def main():
    """Main application entry point"""
    print("🌐 WiFi & Bluetooth Location Detection System")
    print("Version 1.0 - Python Prototype")
    print("=" * 50)
    
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create and start the detection system
    system = CommunicationDetectionSystem()
    system.start_time = time.time()
    
    try:
        system.start_system()
    except KeyboardInterrupt:
        system.stop_system()
    except Exception as e:
        print(f"❌ System error: {e}")
        system.stop_system()
    
    print("\n👋 System shutdown complete")

if __name__ == "__main__":
    main()
