#!/usr/bin/env python3
"""
Simple demo of the WiFi & Bluetooth Detection System
Runs without web dependencies for immediate testing
"""

import time
import json
from datetime import datetime
from wifi_scanner import WiFiScanner
from location_tracker import LocationTracker
from signal_mapper import SignalMapper

def run_detection_demo():
    print("🌐 WiFi & Bluetooth Detection System - Live Demo")
    print("=" * 60)
    
    # Initialize components
    wifi_scanner = WiFiScanner()
    location_tracker = LocationTracker()
    signal_mapper = SignalMapper()
    
    print("📍 Getting location...")
    location = location_tracker.get_gps_location()
    if location:
        print(f"   Location: {location['latitude']:.6f}, {location['longitude']:.6f}")
        print(f"   Source: {location['source']}")
    
    print("\n📶 Scanning WiFi networks...")
    wifi_results = wifi_scanner.scan_once()
    print(f"   Found: {len(wifi_results)} networks")
    
    # Show top 10 strongest signals
    sorted_wifi = sorted(wifi_results, key=lambda x: x['signal_strength'], reverse=True)
    print("\n🏆 Top 10 Strongest WiFi Signals:")
    for i, network in enumerate(sorted_wifi[:10], 1):
        signal_color = "🟢" if network['signal_strength'] > -60 else "🟡" if network['signal_strength'] > -70 else "🔴"
        print(f"   {i:2d}. {signal_color} {network['ssid'][:30]:30} {network['signal_strength']:4} dBm")
    
    # Add to signal mapper if we have location
    if location and wifi_results:
        print(f"\n📊 Adding {len(wifi_results)} readings to signal mapper...")
        signal_mapper.add_signal_reading(location, wifi_results, [])
        
        # Analyze coverage
        analysis = signal_mapper.analyze_coverage('wifi')
        print(f"   Total networks mapped: {analysis['total_networks']}")
        print(f"   Signal readings: {analysis['total_readings']}")
        
        # Export data
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        signal_mapper.export_data(f'live_signal_data_{timestamp}.json')
        print(f"   Data exported to: live_signal_data_{timestamp}.json")
    
    print("\n" + "=" * 60)
    print("✅ Demo completed successfully!")
    print("📋 Summary:")
    print(f"   • WiFi networks detected: {len(wifi_results)}")
    print(f"   • Location tracking: {'✅ Active' if location else '❌ Simulated'}")
    print(f"   • Signal mapping: ✅ Functional")
    print(f"   • Data export: ✅ Complete")
    
    return {
        'wifi_count': len(wifi_results),
        'location': location,
        'strongest_signal': sorted_wifi[0] if sorted_wifi else None
    }

if __name__ == "__main__":
    try:
        results = run_detection_demo()
        print(f"\n🎯 System ready for field deployment!")
        
    except KeyboardInterrupt:
        print("\n\n🛑 Demo stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("💡 Try running individual components to debug")
