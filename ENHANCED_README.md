# Enhanced WiFi & Bluetooth RF Radar

An advanced radar-style visualization system for WiFi and Bluetooth Low Energy (BLE) signal detection and analysis, combining the best features from multiple RF mapping projects.

## Features

### 🎯 **Radar Visualization**
- **Real-time radar sweep animation** with distance-based positioning
- **Signal strength visualization** using RSSI-to-distance conversion
- **Color-coded device types** (WiFi in green, BLE in blue)
- **Interactive device selection** with detailed information panels
- **Dynamic filtering** by signal strength, time window, and search queries

### 📡 **Advanced Scanning**
- **Native Windows WiFi scanning** using netsh commands
- **Cross-platform BLE scanning** with Bleak library
- **Enhanced data models** with Pydantic schemas
- **Privacy protection** with MAC address hashing capabilities
- **Comprehensive metadata extraction** (channels, bands, security, services)

### 🔧 **Smart Filtering & Analysis**
- **RSSI threshold filtering** (-100 to -20 dBm range)
- **Time-based filtering** (1 minute to 1 hour windows)
- **Text search** across SSIDs, device names, and MAC addresses
- **Path loss modeling** for accurate distance estimation
- **Real-time device counting** and statistics

### 💾 **Data Management**
- **JSON export functionality** for analysis and archival
- **Observation store** with automatic deduplication
- **Thread-safe data handling** for concurrent operations
- **Configurable data retention** (default: 2000 observations)

## Installation

### Prerequisites
```bash
# Python 3.8+ required
pip install -r requirements.txt
```

### Dependencies
- **Core**: `tkinter`, `asyncio`, `threading`
- **Data**: `pydantic`, `json`, `datetime`
- **Networking**: `bleak` (for BLE), `subprocess` (for WiFi)
- **UI**: `ttk`, `filedialog`, `messagebox`

### Optional Dependencies
- **Bleak**: For BLE device scanning and battery level reading
- **GPSD**: For GPS location tracking (future enhancement)

## Usage

### Quick Start
```bash
cd wifi-ble-location-mapper
python apps/desktop_py/enhanced_radar.py
```

### Interface Overview

#### **Main Radar Display**
- **Left Panel**: Animated radar with device dots positioned by distance
- **Sweep Line**: Rotating green line for radar effect
- **Range Rings**: Concentric circles showing distance (10m, 20m, 30m, 40m, 50m)
- **Device Dots**: Colored circles representing detected devices

#### **Control Panel**
- **Radio Toggles**: Enable/disable WiFi and BLE scanning
- **RSSI Filter**: Slider to set minimum signal strength
- **Time Window**: Dropdown to select observation age limit
- **Search Box**: Filter devices by name or MAC address

#### **Device Information**
- **Selection**: Click any device dot to view details
- **Details Panel**: Shows RSSI, distance, channel, security, services
- **Export Button**: Save all observations to JSON file

### Advanced Features

#### **Distance Estimation**
The application uses a path loss model to estimate device distance:
```
Distance = 10^((Reference_RSSI - Measured_RSSI) / (10 * Path_Loss_Exponent))
```

Default values:
- **WiFi Reference RSSI**: -45 dBm at 1 meter
- **BLE Reference RSSI**: -59 dBm at 1 meter
- **Path Loss Exponent**: 2.5 (typical indoor environment)

#### **Data Schema**
Each observation includes:
```json
{
  "id": "unique-uuid",
  "ts": "2024-01-01T12:00:00Z",
  "observer_id": "desktop-hostname",
  "radio": "wifi|ble",
  "signal_id": "MAC-address",
  "ssid": "network-name",
  "rssi_dbm": -65,
  "channel": 6,
  "observer_location": {"lat": 0.0, "lon": 0.0},
  "wifi_info": {...},
  "ble_info": {...}
}
```

## Architecture

### **Core Components**

#### **EnhancedRadarDisplay**
- Canvas-based radar visualization
- Real-time animation and device positioning
- Interactive device selection and highlighting
- Filtering and search capabilities

#### **ObservationStore**
- Thread-safe data storage with automatic deduplication
- Configurable size limits and retention policies
- Fast filtering and querying operations

#### **EnhancedRFRadarApp**
- Main application controller
- UI management and event handling
- Background scanning coordination
- Data export and import functionality

### **Scanning Modules**

#### **WiFi Scanning**
- **Windows**: Uses `netsh wlan show networks mode=bssid`
- **macOS**: Airport utility integration (planned)
- **Linux**: NetworkManager CLI integration (planned)

#### **BLE Scanning**
- **Bleak Library**: Cross-platform BLE discovery
- **Service UUID Detection**: Identifies device capabilities
- **Advertisement Data**: Extracts manufacturer and service information

## Configuration

### **Environment Variables**
```bash
# Optional: Set custom scan intervals
export RF_SCAN_INTERVAL=10  # seconds between scans
export RF_MAX_DISTANCE=50   # maximum radar range in meters
export RF_MAX_OBSERVATIONS=2000  # observation storage limit
```

### **Customization Options**
- **Colors**: Modify `WIFI_COLOR`, `BLE_COLOR`, `SELECTED_COLOR` constants
- **Timing**: Adjust `SCAN_INTERVAL` and radar sweep speed
- **Distance Model**: Tune path loss parameters for your environment

## Troubleshooting

### **Common Issues**

#### **BLE Scanning Not Working**
```bash
# Install Bleak library
pip install bleak

# On Windows, ensure Bluetooth is enabled
# On Linux, may require additional permissions
sudo setcap cap_net_raw+eip $(readlink -f $(which python))
```

#### **WiFi Scanning Permissions**
- **Windows**: Run as Administrator if needed
- **macOS**: Grant Terminal location permissions
- **Linux**: Ensure NetworkManager is accessible

#### **Performance Issues**
- Reduce `RF_MAX_OBSERVATIONS` for lower memory usage
- Increase `RF_SCAN_INTERVAL` for less CPU usage
- Disable unused radio types (WiFi or BLE)

### **Debug Mode**
Enable verbose logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Development

### **Project Structure**
```
wifi-ble-location-mapper/
├── apps/desktop_py/
│   ├── enhanced_radar.py      # Main application
│   ├── visualize.py           # Original visualizer
│   └── visualizer.py          # Legacy radar
├── libs/core/
│   ├── schema.py              # Data models
│   └── observation.py         # Observation handling
├── scanners/
│   ├── desktop_wifi_ble.py    # Cross-platform scanning
│   ├── wifi_scanner.py        # WiFi-specific scanning
│   └── ble_scanner.py         # BLE-specific scanning
└── requirements.txt           # Dependencies
```

### **Contributing**
1. Fork the repository
2. Create a feature branch
3. Implement changes with tests
4. Submit a pull request

### **Future Enhancements**
- **GPS Integration**: Real-world positioning
- **3D Visualization**: Height-based positioning
- **Machine Learning**: Device classification and tracking
- **Web Interface**: Browser-based visualization
- **Mobile Apps**: iOS/Android companions
- **Database Storage**: PostgreSQL/InfluxDB backends

## License

This project combines features from multiple open-source RF mapping projects. Please respect the original licenses and contribute back to the community.

## Acknowledgments

- **Original wifi-ble-location-mapper**: Base architecture and data models
- **WifiBluetoothMap**: Radar visualization and UI components
- **Bleak Library**: Cross-platform BLE scanning capabilities
- **Community Contributors**: Bug reports, feature requests, and improvements

---

**Happy RF Hunting! 📡🎯**
