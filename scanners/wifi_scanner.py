"""
WiFi scanner implementation for Windows/Linux/macOS.
"""
import subprocess
import json
import re
import platform
import logging
from typing import Iterator, Dict, Any, Optional
from datetime import datetime

from .base import Scanner, ScannerError, ScannerNotAvailableError
from libs.core import Observation, GeoPoint

logger = logging.getLogger(__name__)

class WiFiScanner(Scanner):
    """Cross-platform WiFi scanner using OS-specific tools."""
    
    def __init__(self, observer_id: str, observer_location: Optional[GeoPoint] = None):
        super().__init__(observer_id, observer_location)
        self.system = platform.system().lower()
        self._validate_system()
        
    def _validate_system(self) -> None:
        """Check if WiFi scanning is available on this system."""
        try:
            if self.system == "windows":
                subprocess.run(["netsh", "wlan", "show", "profiles"], 
                             capture_output=True, check=True, timeout=5)
            elif self.system == "linux":
                subprocess.run(["which", "iwlist"], 
                             capture_output=True, check=True, timeout=5)
            elif self.system == "darwin":  # macOS
                subprocess.run(["which", "airport"], 
                             capture_output=True, check=True, timeout=5)
            else:
                raise ScannerNotAvailableError(f"Unsupported system: {self.system}")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            raise ScannerNotAvailableError(f"WiFi scanning tools not available on {self.system}")
    
    def start(self) -> None:
        """Start WiFi scanning."""
        self._running = True
        logger.info(f"Started WiFi scanner on {self.system}")
    
    def stop(self) -> None:
        """Stop WiFi scanning."""
        self._running = False
        logger.info("Stopped WiFi scanner")
    
    def observations(self) -> Iterator[Observation]:
        """Scan for WiFi networks and yield observations."""
        if not self._running:
            return
            
        try:
            if self.system == "windows":
                yield from self._scan_windows()
            elif self.system == "linux":
                yield from self._scan_linux()
            elif self.system == "darwin":
                yield from self._scan_macos()
        except Exception as e:
            logger.error(f"WiFi scan failed: {e}")
            raise ScannerError(f"WiFi scan failed: {e}")
    
    def _scan_windows(self) -> Iterator[Observation]:
        """Scan WiFi on Windows using netsh."""
        try:
            result = subprocess.run(
                ["netsh", "wlan", "show", "networks", "mode=bssid"],
                capture_output=True, text=True, check=True, timeout=30
            )
            
            networks = self._parse_windows_output(result.stdout)
            for network in networks:
                if self.observer_location:
                    yield self._create_observation(network)
                    
        except subprocess.CalledProcessError as e:
            logger.error(f"Windows WiFi scan failed: {e}")
    
    def _scan_linux(self) -> Iterator[Observation]:
        """Scan WiFi on Linux using iwlist."""
        try:
            # Try to find wireless interface
            interfaces_result = subprocess.run(
                ["iwconfig"], capture_output=True, text=True, timeout=10
            )
            
            # Extract wireless interface name
            interface_match = re.search(r'(\w+)\s+IEEE 802.11', interfaces_result.stdout)
            if not interface_match:
                logger.warning("No wireless interface found")
                return
                
            interface = interface_match.group(1)
            
            result = subprocess.run(
                ["sudo", "iwlist", interface, "scan"],
                capture_output=True, text=True, check=True, timeout=30
            )
            
            networks = self._parse_linux_output(result.stdout)
            for network in networks:
                if self.observer_location:
                    yield self._create_observation(network)
                    
        except subprocess.CalledProcessError as e:
            logger.error(f"Linux WiFi scan failed: {e}")
    
    def _scan_macos(self) -> Iterator[Observation]:
        """Scan WiFi on macOS using airport."""
        try:
            result = subprocess.run([
                "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport",
                "-s"
            ], capture_output=True, text=True, check=True, timeout=30)
            
            networks = self._parse_macos_output(result.stdout)
            for network in networks:
                if self.observer_location:
                    yield self._create_observation(network)
                    
        except subprocess.CalledProcessError as e:
            logger.error(f"macOS WiFi scan failed: {e}")
    
    def _parse_windows_output(self, output: str) -> list[Dict[str, Any]]:
        """Parse Windows netsh output."""
        networks = []
        current_network = {}
        
        for line in output.split('\n'):
            line = line.strip()
            
            if line.startswith('SSID'):
                if current_network:
                    networks.append(current_network)
                current_network = {'ssid': line.split(':', 1)[1].strip()}
            elif line.startswith('BSSID'):
                current_network['bssid'] = line.split(':', 1)[1].strip()
            elif line.startswith('Signal'):
                # Extract signal percentage and convert to approximate dBm
                signal_match = re.search(r'(\d+)%', line)
                if signal_match:
                    percentage = int(signal_match.group(1))
                    # Rough conversion: 100% = -30dBm, 0% = -90dBm
                    rssi = -90 + (percentage * 0.6)
                    current_network['rssi_dbm'] = int(rssi)
            elif line.startswith('Channel'):
                channel_match = re.search(r'(\d+)', line)
                if channel_match:
                    current_network['channel'] = int(channel_match.group(1))
        
        if current_network:
            networks.append(current_network)
            
        return networks
    
    def _parse_linux_output(self, output: str) -> list[Dict[str, Any]]:
        """Parse Linux iwlist output."""
        networks = []
        current_network = {}
        
        for line in output.split('\n'):
            line = line.strip()
            
            if 'Address:' in line:
                if current_network:
                    networks.append(current_network)
                current_network = {'bssid': line.split('Address: ')[1]}
            elif 'ESSID:' in line:
                essid_match = re.search(r'ESSID:"([^"]*)"', line)
                if essid_match:
                    current_network['ssid'] = essid_match.group(1)
            elif 'Signal level=' in line:
                signal_match = re.search(r'Signal level=(-?\d+)', line)
                if signal_match:
                    current_network['rssi_dbm'] = int(signal_match.group(1))
            elif 'Channel:' in line:
                channel_match = re.search(r'Channel:(\d+)', line)
                if channel_match:
                    current_network['channel'] = int(channel_match.group(1))
        
        if current_network:
            networks.append(current_network)
            
        return networks
    
    def _parse_macos_output(self, output: str) -> list[Dict[str, Any]]:
        """Parse macOS airport output."""
        networks = []
        lines = output.strip().split('\n')[1:]  # Skip header
        
        for line in lines:
            parts = line.split()
            if len(parts) >= 6:
                network = {
                    'ssid': parts[0],
                    'bssid': parts[1],
                    'rssi_dbm': int(parts[2]),
                    'channel': int(parts[3]) if parts[3].isdigit() else None
                }
                networks.append(network)
                
        return networks
    
    def _create_observation(self, network_data: Dict[str, Any]) -> Observation:
        """Create an Observation from network scan data."""
        # Calculate frequency from channel (rough approximation)
        freq_mhz = None
        if 'channel' in network_data and network_data['channel']:
            channel = network_data['channel']
            if 1 <= channel <= 14:  # 2.4 GHz
                freq_mhz = 2412 + (channel - 1) * 5
            elif 36 <= channel <= 165:  # 5 GHz
                freq_mhz = 5000 + channel * 5
        
        return Observation(
            observer_id=self.observer_id,
            radio="wifi",
            signal_id=network_data.get('bssid', 'unknown'),
            ssid=network_data.get('ssid'),
            bssid=network_data.get('bssid'),
            freq_mhz=freq_mhz,
            channel=network_data.get('channel'),
            rssi_dbm=network_data.get('rssi_dbm', -100),
            observer_location=self.observer_location
        )
