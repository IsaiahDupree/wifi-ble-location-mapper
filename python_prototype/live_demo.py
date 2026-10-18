#!/usr/bin/env python3
"""
Live WiFi Detection Demo - Real-time console output
Shows the system in action with continuous scanning
"""

import time
import os
import json
from datetime import datetime
from wifi_scanner import WiFiScanner
from location_tracker import LocationTracker
from signal_mapper import SignalMapper

def clear_screen():
    """Clear the console screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Print the demo header"""
    print("🌐" + "="*70 + "🌐")
    print("    WiFi & Bluetooth Location Detection System - LIVE DEMO")
    print("🌐" + "="*70 + "🌐")
    print()

def print_signal_bar(signal_strength):
    """Create a visual signal strength bar"""
    # Convert dBm to percentage (rough approximation)
    if signal_strength > -30:
        bars = "████████████"  # Excellent
        color = "🟢"
    elif signal_strength > -50:
        bars = "█████████░░░"  # Very Good
        color = "🟢"
    elif signal_strength > -60:
        bars = "███████░░░░░"  # Good
        color = "🟡"
    elif signal_strength > -70:
        bars = "█████░░░░░░░"  # Fair
        color = "🟡"
    elif signal_strength > -80:
        bars = "███░░░░░░░░░"  # Poor
        color = "🟠"
    else:
        bars = "█░░░░░░░░░░░"  # Very Poor
        color = "🔴"
    
    return f"{color} {bars} {signal_strength:4} dBm"

def run_live_demo():
    """Run the live WiFi detection demo"""
    print_header()
    print("🚀 Initializing WiFi Detection System...")
    
    # Initialize components
    wifi_scanner = WiFiScanner()
    location_tracker = LocationTracker()
    signal_mapper = SignalMapper()
    
    print("✅ System initialized successfully!")
    print("📍 Getting location...")
    
    location = location_tracker.get_gps_location()
    if location:
        print(f"   📍 Location: {location['latitude']:.6f}, {location['longitude']:.6f}")
        print(f"   🛰️  Source: {location['source']}")
    
    print("\n⏳ Starting continuous WiFi scanning...")
    print("   Press Ctrl+C to stop\n")
    
    scan_count = 0
    total_networks = set()
    
    try:
        while True:
            scan_count += 1
            
            # Clear screen and show header
            clear_screen()
            print_header()
            
            # Show scan info
            current_time = datetime.now().strftime("%H:%M:%S")
            print(f"🕐 Scan #{scan_count} at {current_time}")
            print(f"📊 Total unique networks discovered: {len(total_networks)}")
            
            if location:
                print(f"📍 Location: {location['latitude']:.6f}, {location['longitude']:.6f} ({location['source']})")
            
            print("\n🔍 Scanning WiFi networks...")
            
            # Perform WiFi scan
            networks = wifi_scanner.scan_once()
            
            if networks:
                # Add to total networks set
                for network in networks:
                    total_networks.add(network['bssid'])
                
                # Sort by signal strength
                sorted_networks = sorted(networks, key=lambda x: x['signal_strength'], reverse=True)
                
                print(f"📶 Found {len(networks)} networks:")
                print("─" * 80)
                
                # Show top 15 networks
                for i, network in enumerate(sorted_networks[:15], 1):
                    ssid = network['ssid'][:25] if network['ssid'] else 'Hidden Network'
                    signal_bar = print_signal_bar(network['signal_strength'])
                    encryption = network['encryption'][:10]
                    
                    print(f"{i:2d}. {ssid:25} │ {signal_bar} │ {encryption}")
                
                if len(networks) > 15:
                    print(f"    ... and {len(networks) - 15} more networks")
                
                print("─" * 80)
                
                # Show statistics
                strongest = max(networks, key=lambda x: x['signal_strength'])
                open_networks = [n for n in networks if n['encryption'] == 'Open']
                
                print(f"\n📈 Statistics:")
                print(f"   🏆 Strongest: {strongest['ssid']} ({strongest['signal_strength']} dBm)")
                print(f"   🔓 Open networks: {len(open_networks)}")
                print(f"   🔒 Secured networks: {len(networks) - len(open_networks)}")
                
                # Add to signal mapper if we have location
                if location:
                    signal_mapper.add_signal_reading(location, networks, [])
                    print(f"   📊 Signal readings stored: {len(signal_mapper.signal_data)}")
                
                # Export data periodically
                if scan_count % 5 == 0:  # Every 5 scans
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f'live_scan_{timestamp}.json'
                    
                    export_data = {
                        'scan_count': scan_count,
                        'timestamp': timestamp,
                        'location': location,
                        'networks': networks,
                        'total_unique_networks': len(total_networks)
                    }
                    
                    with open(filename, 'w') as f:
                        json.dump(export_data, f, indent=2, default=str)
                    
                    print(f"   💾 Data exported to: {filename}")
            
            else:
                print("❌ No networks detected in this scan")
            
            print(f"\n⏳ Next scan in 10 seconds... (Scan #{scan_count + 1})")
            print("   Press Ctrl+C to stop and export final data")
            
            # Wait for next scan
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping live demo...")
        
        # Export final data
        final_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        final_filename = f'final_scan_data_{final_timestamp}.json'
        
        final_data = {
            'total_scans': scan_count,
            'total_unique_networks': len(total_networks),
            'signal_mapper_data': signal_mapper.signal_data,
            'session_end': final_timestamp
        }
        
        with open(final_filename, 'w') as f:
            json.dump(final_data, f, indent=2, default=str)
        
        print(f"💾 Final data exported to: {final_filename}")
        print(f"📊 Session summary: {scan_count} scans, {len(total_networks)} unique networks")
        print("✅ Demo completed successfully!")

if __name__ == "__main__":
    run_live_demo()
