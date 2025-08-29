#!/usr/bin/env python3
"""
RF Radio Mapper - Desktop Tkinter Visualizer
Cross-platform WiFi and BLE scanner with radial signal strength visualization.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import platform
import re
import json
import math
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
import asyncio
import random

# Optional BLE support
try:
    from bleak import BleakScanner
    BLE_AVAILABLE = True
except ImportError:
    BLE_AVAILABLE = False

class RadioMapper:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("RF Radio Mapper")
        self.root.geometry("1200x800")
        
        # Data storage
        self.devices = {}  # signal_id -> device_info
        self.cache_file = Path("radio_cache.json")
        self.scanning = False
        self.simulation_mode = False
        
        # Load cached data
        self.load_cache()
        
        # Setup UI
        self.setup_ui()
        
        # Start background scanning
        self.start_scanning()
    
    def setup_ui(self):
        """Create the main UI layout."""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top controls
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Scan controls
        ttk.Button(controls_frame, text="Scan Now", command=self.manual_scan).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(controls_frame, text="Clear Stale", command=self.clear_stale).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(controls_frame, text="Clear All", command=self.clear_all).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(controls_frame, text="WiFi Networks", command=self.open_wifi_list).pack(side=tk.LEFT, padx=(20, 5))
        
        # Simulation mode toggle
        self.sim_var = tk.BooleanVar(value=self.simulation_mode)
        ttk.Checkbutton(controls_frame, text="Simulation Mode", variable=self.sim_var, 
                       command=self.toggle_simulation).pack(side=tk.LEFT, padx=(20, 5))
        
        # Status label
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(controls_frame, textvariable=self.status_var).pack(side=tk.RIGHT)
        
        # Main content area
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left pane - Device list
        left_frame = ttk.LabelFrame(content_frame, text="Detected Devices", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Device list with scrollbar
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("Type", "Signal ID", "Name", "RSSI", "Channel", "Last Seen")
        self.device_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=20)
        
        # Configure columns
        self.device_tree.heading("Type", text="Type")
        self.device_tree.heading("Signal ID", text="Signal ID")
        self.device_tree.heading("Name", text="Name/SSID")
        self.device_tree.heading("RSSI", text="RSSI (dBm)")
        self.device_tree.heading("Channel", text="Channel")
        self.device_tree.heading("Last Seen", text="Last Seen")
        
        self.device_tree.column("Type", width=60)
        self.device_tree.column("Signal ID", width=120)
        self.device_tree.column("Name", width=150)
        self.device_tree.column("RSSI", width=80)
        self.device_tree.column("Channel", width=70)
        self.device_tree.column("Last Seen", width=100)
        
        # Scrollbar for tree
        tree_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.device_tree.yview)
        self.device_tree.configure(yscrollcommand=tree_scroll.set)
        
        self.device_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Sort by RSSI by default
        self.device_tree.heading("RSSI", command=lambda: self.sort_tree("RSSI", True))
        
        # Right pane - Radial map
        right_frame = ttk.LabelFrame(content_frame, text="Signal Strength Map", padding=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Canvas for radial visualization
        self.canvas = tk.Canvas(right_frame, bg="black", width=400, height=400)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Stats frame
        stats_frame = ttk.Frame(main_frame)
        stats_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.stats_var = tk.StringVar(value="WiFi: 0 | BLE: 0 | Total: 0")
        ttk.Label(stats_frame, textvariable=self.stats_var).pack(side=tk.LEFT)
        
        # Platform info
        platform_info = f"Platform: {platform.system()} | BLE: {'Available' if BLE_AVAILABLE else 'Not Available'}"
        ttk.Label(stats_frame, text=platform_info).pack(side=tk.RIGHT)
    
    def load_cache(self):
        """Load cached device data from JSON file."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    self.devices = json.load(f)
                print(f"Loaded {len(self.devices)} cached devices")
            except Exception as e:
                print(f"Error loading cache: {e}")
                self.devices = {}
    
    def save_cache(self):
        """Save device data to JSON cache."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.devices, f, indent=2)
        except Exception as e:
            print(f"Error saving cache: {e}")
    
    def scan_wifi(self):
        """Scan for WiFi networks using platform-specific commands."""
        system = platform.system().lower()
        devices = []
        
        try:
            if "windows" in system:
                devices = self.scan_wifi_windows()
            elif "darwin" in system:  # macOS
                devices = self.scan_wifi_macos()
            else:  # Linux
                devices = self.scan_wifi_linux()
        except Exception as e:
            print(f"WiFi scan error: {e}")
            
        return devices
    
    def scan_wifi_windows(self):
        """Scan WiFi on Windows using netsh."""
        try:
            result = subprocess.run(
                ["netsh", "wlan", "show", "networks", "mode=bssid"],
                capture_output=True, text=True, check=True, timeout=30
            )
            raw = result.stdout.replace("\r\n", "\n")  # normalize newlines

            devices = []

            # Find each SSID block
            ssid_pattern = re.compile(r"^\s*SSID\s+\d+\s*:\s*(.*)$", re.MULTILINE)
            bssid_block_pattern = re.compile(r"^\s*BSSID\s+\d+\s*:\s*([0-9A-Fa-f:]{17})(.*?)(?=^\s*BSSID\s+\d+\s*:|^\s*SSID\s+\d+\s*:|\Z)", re.MULTILINE | re.DOTALL)
            signal_pattern = re.compile(r"^\s*Signal\s*:\s*(\d+)%", re.MULTILINE)
            channel_pattern = re.compile(r"^\s*Channel\s*:\s*(\d+)", re.MULTILINE)

            # Iterate over SSID sections by locating their spans
            ssid_iter = list(ssid_pattern.finditer(raw))
            for i, m in enumerate(ssid_iter):
                ssid = m.group(1).strip()
                start = m.end()
                end = ssid_iter[i + 1].start() if i + 1 < len(ssid_iter) else len(raw)
                ssid_block = raw[start:end]

                for bssid_match in bssid_block_pattern.finditer(ssid_block):
                    bssid = bssid_match.group(1).lower()
                    bssid_detail = bssid_match.group(2)

                    sig_m = signal_pattern.search(bssid_detail)
                    ch_m = channel_pattern.search(bssid_detail)
                    if not sig_m:
                        continue
                    percentage = int(sig_m.group(1))
                    rssi = int(percentage / 2 - 100)  # approx conversion
                    channel = int(ch_m.group(1)) if ch_m else None

                    devices.append({
                        "type": "WiFi",
                        "signal_id": bssid,
                        "name": ssid,
                        "rssi": rssi,
                        "channel": channel
                    })

            return devices

        except Exception as e:
            print(f"Windows WiFi scan failed: {e}")
            return []
    
    def scan_wifi_macos(self):
        """Scan WiFi on macOS using airport."""
        try:
            airport_path = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
            result = subprocess.run([airport_path, "-s"], capture_output=True, text=True, check=True, timeout=30)
            
            devices = []
            for line in result.stdout.splitlines()[1:]:  # Skip header
                if not line.strip():
                    continue
                    
                parts = re.split(r"\s{2,}", line.strip())
                if len(parts) >= 3:
                    ssid, bssid = parts[0], parts[1]
                    try:
                        rssi = int(parts[2])
                    except:
                        continue
                    
                    channel = None
                    if len(parts) >= 4:
                        ch = parts[3].split(",")[0]
                        try:
                            channel = int(ch)
                        except:
                            pass
                    
                    devices.append({
                        "type": "WiFi",
                        "signal_id": bssid,
                        "name": ssid,
                        "rssi": rssi,
                        "channel": channel
                    })
            
            return devices
            
        except Exception as e:
            print(f"macOS WiFi scan failed: {e}")
            return []
    
    def scan_wifi_linux(self):
        """Scan WiFi on Linux using nmcli or iwlist."""
        # Try nmcli first
        try:
            result = subprocess.run(
                ["nmcli", "-f", "SSID,BSSID,CHAN,FREQ,SIGNAL", "dev", "wifi"],
                capture_output=True, text=True, check=True, timeout=30
            )
            
            devices = []
            for line in result.stdout.splitlines()[1:]:  # Skip header
                if not line.strip():
                    continue
                    
                m = re.match(r"(.+?)\s+([0-9A-Fa-f:]{17})\s+(\d+)\s+(\d+)\s+(\d+)", line.strip())
                if m:
                    ssid, bssid, chan, freq, signal = m.groups()
                    # Convert signal percentage to dBm
                    rssi = int(int(signal) / 2 - 100)
                    
                    devices.append({
                        "type": "WiFi",
                        "signal_id": bssid,
                        "name": ssid,
                        "rssi": rssi,
                        "channel": int(chan)
                    })
            
            return devices
            
        except Exception:
            # Fall back to iwlist (may require sudo)
            try:
                # Try to find wireless interface
                interfaces_result = subprocess.run(["iwconfig"], capture_output=True, text=True, timeout=10)
                interface_match = re.search(r'(\w+)\s+IEEE 802.11', interfaces_result.stdout)
                
                if interface_match:
                    interface = interface_match.group(1)
                    result = subprocess.run(
                        ["iwlist", interface, "scan"],
                        capture_output=True, text=True, check=True, timeout=30
                    )
                    
                    # Parse iwlist output (simplified)
                    devices = []
                    current_device = {}
                    
                    for line in result.stdout.split('\n'):
                        line = line.strip()
                        
                        if 'Address:' in line:
                            if current_device:
                                devices.append(current_device)
                            current_device = {
                                "type": "WiFi",
                                "signal_id": line.split('Address: ')[1],
                                "name": "",
                                "rssi": -100,
                                "channel": None
                            }
                        elif 'ESSID:' in line:
                            essid_match = re.search(r'ESSID:"([^"]*)"', line)
                            if essid_match:
                                current_device["name"] = essid_match.group(1)
                        elif 'Signal level=' in line:
                            signal_match = re.search(r'Signal level=(-?\d+)', line)
                            if signal_match:
                                current_device["rssi"] = int(signal_match.group(1))
                        elif 'Channel:' in line:
                            channel_match = re.search(r'Channel:(\d+)', line)
                            if channel_match:
                                current_device["channel"] = int(channel_match.group(1))
                    
                    if current_device:
                        devices.append(current_device)
                    
                    return devices
                    
            except Exception as e:
                print(f"Linux WiFi scan failed: {e}")
                
        return []
    
    def scan_ble(self):
        """Scan for BLE devices using bleak."""
        if not BLE_AVAILABLE:
            return []
        
        devices = []
        try:
            # Run async BLE scan in thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def async_scan():
                discovered = await BleakScanner.discover(timeout=5.0)
                for device in discovered:
                    devices.append({
                        "type": "BLE",
                        "signal_id": device.address,
                        "name": device.name or "Unknown",
                        "rssi": getattr(device, 'rssi', -100),
                        "channel": None
                    })
            
            loop.run_until_complete(async_scan())
            loop.close()
            
        except Exception as e:
            print(f"BLE scan error: {e}")
        
        return devices
    
    def generate_simulation_data(self):
        """Generate simulated device data for testing."""
        devices = []
        
        # Simulated WiFi networks
        wifi_networks = [
            ("Linksys_Guest", "aa:bb:cc:dd:ee:01"),
            ("NETGEAR_5G", "aa:bb:cc:dd:ee:02"),
            ("CoffeeShop_WiFi", "aa:bb:cc:dd:ee:03"),
            ("iPhone_Hotspot", "aa:bb:cc:dd:ee:04"),
            ("Office_Network", "aa:bb:cc:dd:ee:05"),
        ]
        
        for ssid, bssid in wifi_networks:
            devices.append({
                "type": "WiFi",
                "signal_id": bssid,
                "name": ssid,
                "rssi": random.randint(-90, -30),
                "channel": random.choice([1, 6, 11, 36, 44, 149])
            })
        
        # Simulated BLE devices
        ble_devices = [
            ("iPhone_12", "11:22:33:44:55:01"),
            ("Samsung_Watch", "11:22:33:44:55:02"),
            ("AirPods_Pro", "11:22:33:44:55:03"),
            ("Fitbit_Sense", "11:22:33:44:55:04"),
            ("Smart_Speaker", "11:22:33:44:55:05"),
        ]
        
        for name, address in ble_devices:
            devices.append({
                "type": "BLE",
                "signal_id": address,
                "name": name,
                "rssi": random.randint(-100, -40),
                "channel": None
            })
        
        return devices
    
    def perform_scan(self):
        """Perform a complete scan of WiFi and BLE devices."""
        self.status_var.set("Scanning...")
        devices = []
        
        if self.simulation_mode:
            devices = self.generate_simulation_data()
        else:
            # Scan WiFi
            wifi_devices = self.scan_wifi()
            devices.extend(wifi_devices)
            
            # Scan BLE
            ble_devices = self.scan_ble()
            devices.extend(ble_devices)
        
        # Update device database
        current_time = datetime.now().isoformat()
        
        for device in devices:
            signal_id = device["signal_id"]
            self.devices[signal_id] = {
                **device,
                "last_seen": current_time,
                "first_seen": self.devices.get(signal_id, {}).get("first_seen", current_time)
            }
        
        # Update UI
        self.root.after(0, self.update_display)
        self.save_cache()
        
        scan_count = len(devices)
        self.status_var.set(f"Scan complete: {scan_count} devices found")
    
    def update_display(self):
        """Update the device list and radial map."""
        # Clear existing items
        for item in self.device_tree.get_children():
            self.device_tree.delete(item)
        
        # Add devices to tree
        wifi_count = 0
        ble_count = 0
        
        # Sort devices by RSSI (strongest first)
        sorted_devices = sorted(self.devices.items(), 
                              key=lambda x: x[1].get("rssi", -100), reverse=True)
        
        for signal_id, device in sorted_devices:
            device_type = device.get("type", "Unknown")
            name = device.get("name", "Unknown")
            rssi = device.get("rssi", -100)
            channel = device.get("channel", "")
            last_seen = device.get("last_seen", "")
            
            # Format last seen time
            try:
                dt = datetime.fromisoformat(last_seen)
                time_str = dt.strftime("%H:%M:%S")
            except:
                time_str = "Unknown"
            
            # Add to tree
            self.device_tree.insert("", tk.END, values=(
                device_type, signal_id, name, rssi, channel, time_str
            ))
            
            # Count by type
            if device_type == "WiFi":
                wifi_count += 1
            elif device_type == "BLE":
                ble_count += 1
        
        # Update stats
        total_count = len(self.devices)
        self.stats_var.set(f"WiFi: {wifi_count} | BLE: {ble_count} | Total: {total_count}")
        
        # Update radial map
        self.draw_radial_map()
    
    def draw_radial_map(self):
        """Draw the radial signal strength visualization."""
        self.canvas.delete("all")
        
        # Get canvas dimensions
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        if width <= 1 or height <= 1:
            # Canvas not ready yet
            self.root.after(100, self.draw_radial_map)
            return
        
        center_x = width // 2
        center_y = height // 2
        max_radius = min(center_x, center_y) - 20
        
        # Draw concentric circles for signal strength reference
        for i, (radius_pct, label) in enumerate([(0.25, "-30dBm"), (0.5, "-50dBm"), (0.75, "-70dBm"), (1.0, "-90dBm")]):
            radius = max_radius * radius_pct
            self.canvas.create_oval(
                center_x - radius, center_y - radius,
                center_x + radius, center_y + radius,
                outline="gray", width=1, fill=""
            )
            # Add label
            self.canvas.create_text(
                center_x + radius * 0.7, center_y - radius * 0.7,
                text=label, fill="white", font=("Arial", 8)
            )
        
        # Draw center point (you)
        self.canvas.create_oval(
            center_x - 5, center_y - 5,
            center_x + 5, center_y + 5,
            fill="yellow", outline="orange", width=2
        )
        self.canvas.create_text(center_x, center_y - 15, text="YOU", fill="yellow", font=("Arial", 8, "bold"))
        
        # Plot devices
        angle_step = 360 / max(len(self.devices), 1)
        current_angle = 0
        
        for signal_id, device in self.devices.items():
            rssi = device.get("rssi", -100)
            device_type = device.get("type", "Unknown")
            name = device.get("name", "Unknown")[:10]  # Truncate long names
            
            # Convert RSSI to radius (closer = stronger signal)
            # RSSI range: -30 (very strong) to -100 (very weak)
            normalized_rssi = max(0, min(1, (rssi + 100) / 70))  # 0 = weak, 1 = strong
            radius = max_radius * (1 - normalized_rssi)  # Invert: strong signals closer to center
            
            # Calculate position
            angle_rad = math.radians(current_angle)
            x = center_x + radius * math.cos(angle_rad)
            y = center_y + radius * math.sin(angle_rad)
            
            # Choose color based on type
            if device_type == "WiFi":
                color = "red"
                symbol = "□"
            elif device_type == "BLE":
                color = "cyan"
                symbol = "○"
            else:
                color = "white"
                symbol = "◊"
            
            # Draw device
            point_size = max(3, min(8, int(normalized_rssi * 8)))
            self.canvas.create_oval(
                x - point_size, y - point_size,
                x + point_size, y + point_size,
                fill=color, outline="white", width=1
            )
            
            # Add label
            self.canvas.create_text(
                x, y + 12, text=f"{symbol} {name}\n{rssi}dBm",
                fill=color, font=("Arial", 7), justify=tk.CENTER
            )
            
            current_angle += angle_step
        
        # Add legend
        legend_y = 20
        self.canvas.create_text(20, legend_y, text="WiFi □", fill="red", font=("Arial", 10), anchor="w")
        self.canvas.create_text(80, legend_y, text="BLE ○", fill="cyan", font=("Arial", 10), anchor="w")
        self.canvas.create_text(20, legend_y + 15, text="Closer = Stronger Signal", fill="white", font=("Arial", 8), anchor="w")

    def open_wifi_list(self):
        """Open a window listing available WiFi networks (SSIDs)."""
        # Create or focus existing window
        if hasattr(self, "wifi_window") and self.wifi_window.winfo_exists():
            self.wifi_window.lift()
            return
        
        self.wifi_window = tk.Toplevel(self.root)
        self.wifi_window.title("WiFi Networks")
        self.wifi_window.geometry("700x400")
        
        top_frame = ttk.Frame(self.wifi_window)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(top_frame, text="Available WiFi Networks (from latest scan)").pack(side=tk.LEFT)
        ttk.Button(top_frame, text="Refresh", command=lambda: self.populate_wifi_list()).pack(side=tk.RIGHT)
        
        # Treeview
        columns = ("SSID", "BSSID", "RSSI", "Channel", "Last Seen")
        self.wifi_tree = ttk.Treeview(self.wifi_window, columns=columns, show="headings", height=15)
        for col in columns:
            self.wifi_tree.heading(col, text=col)
        self.wifi_tree.column("SSID", width=180)
        self.wifi_tree.column("BSSID", width=160)
        self.wifi_tree.column("RSSI", width=80)
        self.wifi_tree.column("Channel", width=80)
        self.wifi_tree.column("Last Seen", width=120)
        
        yscroll = ttk.Scrollbar(self.wifi_window, orient=tk.VERTICAL, command=self.wifi_tree.yview)
        self.wifi_tree.configure(yscrollcommand=yscroll.set)
        
        self.wifi_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10,0), pady=(0,10))
        yscroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0,10), pady=(0,10))
        
        self.populate_wifi_list()

    def populate_wifi_list(self):
        """Populate the WiFi networks table from current device data."""
        if not hasattr(self, "wifi_tree") or not self.wifi_tree.winfo_exists():
            return
        # Clear
        for item in self.wifi_tree.get_children():
            self.wifi_tree.delete(item)
        
        # Filter WiFi devices
        wifi_devices = [d for d in self.devices.values() if d.get("type") == "WiFi"]
        # Sort by RSSI desc
        wifi_devices.sort(key=lambda d: d.get("rssi", -100), reverse=True)
        
        for d in wifi_devices:
            ssid = d.get("name", "")
            bssid = d.get("signal_id", "")
            rssi = d.get("rssi", "")
            ch = d.get("channel", "")
            last_seen = d.get("last_seen", "")
            try:
                if last_seen:
                    dt = datetime.fromisoformat(last_seen)
                    last_seen = dt.strftime("%H:%M:%S")
            except:
                pass
            self.wifi_tree.insert("", tk.END, values=(ssid, bssid, rssi, ch, last_seen))
    
    def sort_tree(self, column, reverse=False):
        """Sort the device tree by column."""
        items = [(self.device_tree.set(child, column), child) for child in self.device_tree.get_children()]
        
        # Sort numerically for RSSI, alphabetically for others
        if column == "RSSI":
            items.sort(key=lambda x: int(x[0]) if x[0].lstrip('-').isdigit() else -999, reverse=reverse)
        else:
            items.sort(reverse=reverse)
        
        for index, (val, child) in enumerate(items):
            self.device_tree.move(child, '', index)
    
    def manual_scan(self):
        """Trigger a manual scan."""
        if not self.scanning:
            threading.Thread(target=self.perform_scan, daemon=True).start()
    
    def clear_stale(self):
        """Remove devices not seen in the last 24 hours."""
        cutoff_time = datetime.now() - timedelta(hours=24)
        stale_devices = []
        
        for signal_id, device in self.devices.items():
            try:
                last_seen = datetime.fromisoformat(device.get("last_seen", ""))
                if last_seen < cutoff_time:
                    stale_devices.append(signal_id)
            except:
                stale_devices.append(signal_id)  # Remove devices with invalid timestamps
        
        for signal_id in stale_devices:
            del self.devices[signal_id]
        
        self.update_display()
        self.save_cache()
        self.status_var.set(f"Removed {len(stale_devices)} stale devices")
    
    def clear_all(self):
        """Clear all devices."""
        if messagebox.askyesno("Clear All", "Remove all detected devices?"):
            self.devices.clear()
            self.update_display()
            self.save_cache()
            self.status_var.set("All devices cleared")
    
    def toggle_simulation(self):
        """Toggle simulation mode."""
        self.simulation_mode = self.sim_var.get()
        mode_text = "Simulation" if self.simulation_mode else "Real"
        self.status_var.set(f"Mode: {mode_text}")
    
    def start_scanning(self):
        """Start background scanning thread."""
        def scan_loop():
            self.scanning = True
            while self.scanning:
                self.perform_scan()
                time.sleep(10)  # Scan every 10 seconds
        
        threading.Thread(target=scan_loop, daemon=True).start()
        
        # Initial display update
        self.update_display()
    
    def run(self):
        """Start the main application loop."""
        # Bind canvas resize to redraw
        self.canvas.bind("<Configure>", lambda e: self.draw_radial_map())
        
        # Handle window close
        def on_closing():
            self.scanning = False
            self.save_cache()
            self.root.destroy()
        
        self.root.protocol("WM_DELETE_WINDOW", on_closing)
        self.root.mainloop()

def main():
    """Main entry point."""
    print("RF Radio Mapper - Desktop Visualizer")
    print("=====================================")
    print(f"Platform: {platform.system()}")
    print(f"BLE Support: {'Available' if BLE_AVAILABLE else 'Not Available (install bleak)'}")
    print()
    
    app = RadioMapper()
    app.run()

if __name__ == "__main__":
    main()
