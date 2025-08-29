# WiFi & Bluetooth Location Detection System

A comprehensive system for detecting and mapping WiFi, Bluetooth, and other line-of-sight communications with location tracking and VR/AR visualization.

## Project Structure

### Phase 1: Python Prototype
- `python_prototype/` - Initial Python implementation
- Real-time WiFi and Bluetooth scanning
- GPS/location integration
- Signal strength mapping
- Data logging and visualization

### Phase 2: Embedded Implementation
- `cpp_embedded/` - C++ version for ESP32/Raspberry Pi
- Optimized for low-power operation
- Real-time data transmission
- Hardware-specific optimizations

### Phase 3: VR/AR Visualization
- `vr_app/` - Unity-based VR/AR application
- 3D visualization of signal strengths
- Real-time location-based AR overlays
- Interactive signal analysis

## Hardware Requirements

### ESP32 Version
- ESP32 development board
- GPS module (optional)
- External antenna for better range

### Raspberry Pi Version
- Raspberry Pi 4B+ recommended
- USB WiFi adapter (for dual-band scanning)
- Bluetooth 5.0+ adapter
- GPS HAT or USB GPS module

## Features

- **WiFi Detection**: SSID, BSSID, signal strength, channel, encryption
- **Bluetooth Detection**: Device names, MAC addresses, signal strength, device types
- **Location Tracking**: GPS coordinates, indoor positioning
- **Signal Mapping**: Real-time heatmaps and 3D visualization
- **Data Export**: JSON, CSV, KML formats
- **VR Integration**: Immersive signal strength visualization

## Installation

```bash
# Python prototype
cd python_prototype
pip install -r requirements.txt
python main.py

# C++ embedded (after setup)
cd cpp_embedded
make flash
```

## Usage

1. Start the detection system
2. Move around the area to scan
3. View real-time data in web interface
4. Export data for VR visualization
5. Load in VR app for immersive analysis
