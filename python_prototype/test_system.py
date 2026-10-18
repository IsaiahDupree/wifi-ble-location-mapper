#!/usr/bin/env python3
"""
Test script for the WiFi & Bluetooth Detection System
Tests core functionality without requiring all external dependencies
"""

import sys
import time
from datetime import datetime

def test_wifi_scanner():
    """Test WiFi scanner functionality"""
    print("🔍 Testing WiFi Scanner...")
    try:
        from wifi_scanner import WiFiScanner
        scanner = WiFiScanner()
        
        # Test single scan
        results = scanner.scan_once()
        print(f"   ✅ WiFi scan completed: {len(results)} networks found")
        
        # Show sample results
        for i, network in enumerate(results[:3]):
            print(f"   📶 {network['ssid']}: {network['signal_strength']} dBm")
        
        return True
    except Exception as e:
        print(f"   ❌ WiFi scanner error: {e}")
        return False

def test_location_tracker():
    """Test location tracker functionality"""
    print("\n📍 Testing Location Tracker...")
    try:
        from location_tracker import LocationTracker
        tracker = LocationTracker()
        
        # Test simulated location
        location = tracker.get_simulated_location()
        print(f"   ✅ Location tracking works: {location['latitude']:.6f}, {location['longitude']:.6f}")
        print(f"   📡 Source: {location['source']}")
        
        return True
    except Exception as e:
        print(f"   ❌ Location tracker error: {e}")
        return False

def test_signal_mapper():
    """Test signal mapper functionality"""
    print("\n📊 Testing Signal Mapper...")
    try:
        from signal_mapper import SignalMapper
        mapper = SignalMapper()
        
        # Add test data
        test_location = {'latitude': 40.7128, 'longitude': -74.0060}
        test_wifi = [{'ssid': 'TestNet', 'bssid': 'aa:bb:cc:dd:ee:ff', 'signal_strength': -50}]
        test_bluetooth = [{'name': 'TestDevice', 'address': '11:22:33:44:55:66', 'rssi': -60}]
        
        mapper.add_signal_reading(test_location, test_wifi, test_bluetooth)
        
        analysis = mapper.analyze_coverage('wifi')
        print(f"   ✅ Signal mapping works: {analysis['total_networks']} networks mapped")
        
        return True
    except Exception as e:
        print(f"   ❌ Signal mapper error: {e}")
        return False

def test_web_interface():
    """Test web interface imports"""
    print("\n🌐 Testing Web Interface...")
    try:
        # Test Flask import
        import flask
        print("   ✅ Flask available")
        
        # Test SocketIO import
        import flask_socketio
        print("   ✅ Flask-SocketIO available")
        
        return True
    except ImportError as e:
        print(f"   ⚠️  Web interface dependencies missing: {e}")
        print("   💡 Install with: pip install flask flask-socketio")
        return False

def main():
    """Run all tests"""
    print("🧪 WiFi & Bluetooth Detection System - Component Tests")
    print("=" * 60)
    
    tests = [
        test_location_tracker,
        test_signal_mapper,
        test_wifi_scanner,
        test_web_interface
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"   ❌ Test failed with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"📋 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! System is ready to use.")
        print("\n🚀 Next steps:")
        print("   1. Install missing dependencies: pip install flask flask-socketio")
        print("   2. Run main system: python main.py")
        print("   3. Or start web interface: python web_interface.py")
    else:
        print("⚠️  Some tests failed. Check error messages above.")
        print("\n💡 Common solutions:")
        print("   - Install Python packages: pip install -r requirements.txt")
        print("   - Run as administrator for WiFi scanning")
        print("   - Check Windows WiFi service is running")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
