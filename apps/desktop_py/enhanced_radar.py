#!/usr/bin/env python3
"""
Enhanced RF Radar - Combining the best features from both projects
A comprehensive radar-style visualization for WiFi and BLE signals with advanced features.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import math
import threading
import time
import asyncio
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import re
import platform
import traceback
from typing import Optional, Dict, List, Any

# Import from the wifi-ble-location-mapper libs
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from libs.core.schema import Observation, GeoPoint, WifiInfo, BleInfo
except ImportError:
    # Fallback: create minimal schemas if import fails
    from pydantic import BaseModel
    from typing import Optional, List
    from uuid import uuid4
    from datetime import datetime, timezone
    
    class GeoPoint(BaseModel):
        lat: float
        lon: float
        alt: Optional[float] = None
        accuracy_m: Optional[float] = None
    
    class WifiInfo(BaseModel):
        band: Optional[str] = None
        security: Optional[str] = None
        std: Optional[str] = None
    
    class BleInfo(BaseModel):
        local_name: Optional[str] = None
        is_connectable: Optional[bool] = None
    
    class Observation(BaseModel):
        id: str = str(uuid4())
        ts: str = datetime.now(timezone.utc).isoformat()
        observer_id: str
        radio: str
        signal_id: str
        ssid: Optional[str] = None
        service_uuids: Optional[List[str]] = None
        freq_mhz: Optional[int] = None
        channel: Optional[int] = None
        rssi_dbm: int
        tx_power_dbm: Optional[int] = None
        observer_location: GeoPoint
        wifi_info: Optional[WifiInfo] = None
        ble_info: Optional[BleInfo] = None
        raw: Optional[dict] = None

# Optional dependencies
try:
    from bleak import BleakClient, BleakScanner
    BLEAK_AVAILABLE = True
except ImportError:
    BLEAK_AVAILABLE = False

# Constants
DEFAULT_PATH_LOSS_EXPONENT = 2.5
DEFAULT_WIFI_REF_RSSI = -45
DEFAULT_BLE_REF_RSSI = -59
SCAN_INTERVAL = 10.0
MAX_DISTANCE = 50
BG_COLOR = "#000000"
WIFI_COLOR = "#00FF00"
BLE_COLOR = "#00AAFF"
SELECTED_COLOR = "#FFFF00"

class EnhancedRadarDisplay(tk.Canvas):
    """Enhanced radar display combining features from both projects"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(background=BG_COLOR)
        
        self.observations = []
        self.selected = None
        self.circles = {}
        self.labels = {}
        
        self.sweep_angle = 0
        self.path_loss = DEFAULT_PATH_LOSS_EXPONENT
        self.wifi_ref = DEFAULT_WIFI_REF_RSSI
        self.ble_ref = DEFAULT_BLE_REF_RSSI
        self.selection_callback = None
        
        self.bind("<Button-1>", self.on_click)
        
    def start_sweep(self):
        """Start radar sweep animation"""
        self.update_sweep()
        
    def update_sweep(self):
        """Update radar sweep animation"""
        self.sweep_angle = (self.sweep_angle + 3) % 360
        self.draw_radar()
        self.after(50, self.update_sweep)
        
    def draw_radar(self):
        """Draw the radar background and sweep line"""
        width = self.winfo_width()
        height = self.winfo_height()
        
        if width <= 1 or height <= 1:
            width = 600
            height = 600
            
        cx = width / 2
        cy = height / 2
        radius = min(width, height) / 2 - 10
        
        self.delete("radar_bg")
        
        # Draw radar circles
        for i in range(1, 6):
            r = radius * i / 5
            self.create_oval(cx - r, cy - r, cx + r, cy + r, 
                          outline="#003300", width=1, tags="radar_bg")
            
        # Draw range labels
        for i in range(1, 6):
            dist = MAX_DISTANCE * i / 5
            x = cx + 5
            y = cy - radius * i / 5
            self.create_text(x, y, text=f"{int(dist)}m", fill="#004400",
                          anchor=tk.W, tags="radar_bg")
        
        # Draw axes
        self.create_line(cx - radius, cy, cx + radius, cy, 
                      fill="#004400", width=1, tags="radar_bg")
        self.create_line(cx, cy - radius, cx, cy + radius, 
                      fill="#004400", width=1, tags="radar_bg")
        
        # Draw sweep line
        angle_rad = math.radians(self.sweep_angle)
        x = cx + radius * math.cos(angle_rad)
        y = cy - radius * math.sin(angle_rad)
        self.create_line(cx, cy, x, y, fill="#00AA00", width=2, tags="radar_bg")
        
    def draw_dots(self, observations, min_ts=None, min_rssi=None, show_wifi=True, show_ble=True, query=None):
        """Draw device dots on the radar"""
        filtered = self.filter_observations(observations, min_ts, min_rssi, show_wifi, show_ble, query)
        
        width = self.winfo_width()
        height = self.winfo_height()
        if width <= 1 or height <= 1:
            width = 600
            height = 600
            
        cx = width / 2
        cy = height / 2
        radius = min(width, height) / 2 - 10
        
        self.delete("device")
        self.circles = {}
        self.labels = {}
        
        now = datetime.now()
        
        for obs in filtered:
            # Calculate distance from RSSI
            ref_rssi = self.wifi_ref if obs.radio == "wifi" else self.ble_ref
            distance = 10**((ref_rssi - obs.rssi_dbm)/(10 * self.path_loss))
            
            if distance > MAX_DISTANCE:
                continue
                
            # Calculate position
            norm_distance = distance / MAX_DISTANCE
            dot_radius = radius * norm_distance
            
            # Calculate angle from signal ID hash
            signal_hash = int(hashlib.md5(obs.signal_id.encode()).hexdigest(), 16)
            angle = signal_hash % 360
            angle_rad = math.radians(angle)
            
            x = cx + dot_radius * math.cos(angle_rad)
            y = cy - dot_radius * math.sin(angle_rad)
            
            # Determine color
            dot_color = WIFI_COLOR if obs.radio == "wifi" else BLE_COLOR
            dot_size = min(max(abs(obs.rssi_dbm) / 10, 3), 10)
            
            # Highlight selected device
            outline = ""
            width_val = 1
            if self.selected and obs.signal_id == self.selected.signal_id:
                outline = SELECTED_COLOR
                width_val = 2
            
            # Draw the dot
            circle = self.create_oval(x - dot_size, y - dot_size, x + dot_size, y + dot_size,
                                fill=dot_color, outline=outline, width=width_val,
                                tags=("device", obs.signal_id))
            self.circles[obs.signal_id] = circle
            
            # Draw label for selected item
            if self.selected and obs.signal_id == self.selected.signal_id:
                label_text = obs.signal_id
                if obs.radio == "wifi" and obs.ssid:
                    label_text = obs.ssid
                elif obs.radio == "ble" and obs.ble_info and obs.ble_info.local_name:
                    label_text = obs.ble_info.local_name
                        
                label = self.create_text(x, y - dot_size - 5, text=label_text,
                                      fill=SELECTED_COLOR, tags=("device", "label"))
                self.labels[obs.signal_id] = label
                
    def filter_observations(self, observations, min_ts=None, min_rssi=None, wifi=True, ble=True, query=None):
        """Filter observations based on criteria"""
        result = observations.copy()
        
        if min_ts is not None:
            result = [o for o in result if datetime.fromisoformat(o.ts.replace('Z', '+00:00')).replace(tzinfo=None) >= min_ts]
            
        if min_rssi is not None:
            result = [o for o in result if o.rssi_dbm >= min_rssi]
            
        radio_filter = []
        if wifi:
            radio_filter.append("wifi")
        if ble:
            radio_filter.append("ble")
            
        result = [o for o in result if o.radio in radio_filter]
        
        if query and query.strip():
            query = query.lower()
            filtered = []
            for o in result:
                if o.radio == "wifi" and o.ssid and o.ssid.lower().find(query) >= 0:
                    filtered.append(o)
                    continue
                    
                if o.radio == "ble" and o.ble_info and o.ble_info.local_name and o.ble_info.local_name.lower().find(query) >= 0:
                    filtered.append(o)
                    continue
                        
                if o.signal_id.lower().find(query) >= 0:
                    filtered.append(o)
                    
            result = filtered
            
        return result
                
    def on_click(self, event):
        """Handle click event to select a device"""
        x, y = event.x, event.y
        
        clicked = self.find_closest(x, y)
        if not clicked:
            return
            
        tags = self.gettags(clicked[0])
        for tag in tags:
            if tag != "device":
                if self.selection_callback:
                    self.selection_callback(tag)
                return

class ObservationStore:
    """Enhanced observation store with better data management"""
    
    def __init__(self, max_points=2000):
        self.max = max_points
        self.items = []
        self.lock = threading.Lock()
        
    def add(self, obs: Observation):
        """Add a single observation"""
        with self.lock:
            # Check if duplicate exists
            for i, existing in enumerate(self.items):
                if existing.signal_id == obs.signal_id and existing.radio == obs.radio:
                    self.items[i] = obs
                    return
                    
            self.items.append(obs)
            
            if len(self.items) > self.max:
                self.items = sorted(self.items, key=lambda x: x.ts, reverse=True)[:self.max]
                
    def extend(self, observations: List[Observation]):
        """Add multiple observations"""
        for obs in observations:
            self.add(obs)
            
    def get_all(self):
        """Get all observations"""
        with self.lock:
            return self.items.copy()
            
    def clear(self):
        """Clear all observations"""
        with self.lock:
            self.items = []
            
    def __len__(self):
        return len(self.items)

class EnhancedRFRadarApp:
    """Enhanced RF Radar application combining best features"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Enhanced RF Radar")
        self.root.geometry("1400x1000")
        self.root.configure(background=BG_COLOR)
        
        self.observations = ObservationStore()
        self.scanning = False
        self.scan_thread = None
        self.observer_id = f"desktop-{platform.node()}"
        
        self.create_ui()
        self.init_app()
        
    def create_ui(self):
        """Create the enhanced user interface"""
        # Left panel for radar display
        self.left_frame = ttk.Frame(self.root, padding=10)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Radar canvas
        self.radar = EnhancedRadarDisplay(self.left_frame,
                                        width=800, height=800, highlightthickness=0)
        self.radar.pack(fill=tk.BOTH, expand=True)
        self.radar.selection_callback = self.select_device
        
        # Right panel for controls and device info
        self.right_frame = ttk.Frame(self.root, padding=10)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Controls section
        self.controls_frame = ttk.LabelFrame(self.right_frame, text="Controls", padding=10)
        self.controls_frame.pack(fill=tk.X, pady=5)
        
        # Radio type toggles
        self.radio_frame = ttk.Frame(self.controls_frame)
        self.radio_frame.pack(fill=tk.X, pady=5)
        
        self.show_wifi_var = tk.BooleanVar(value=True)
        self.show_wifi_check = ttk.Checkbutton(self.radio_frame, text="WiFi", 
                                          variable=self.show_wifi_var,
                                          command=self.update_display)
        self.show_wifi_check.pack(side=tk.LEFT, padx=5)
        
        self.show_ble_var = tk.BooleanVar(value=True)
        self.show_ble_check = ttk.Checkbutton(self.radio_frame, text="BLE",
                                         variable=self.show_ble_var,
                                         command=self.update_display)
        self.show_ble_check.pack(side=tk.LEFT, padx=5)
        
        # RSSI filter
        self.rssi_frame = ttk.Frame(self.controls_frame)
        self.rssi_frame.pack(fill=tk.X, pady=5)
        ttk.Label(self.rssi_frame, text="Min RSSI:").pack(side=tk.LEFT)
        
        self.rssi_var = tk.IntVar(value=-80)
        self.rssi_scale = ttk.Scale(self.rssi_frame, from_=-100, to=-20,
                                orient=tk.HORIZONTAL, variable=self.rssi_var,
                                command=lambda _: self.update_display())
        self.rssi_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.rssi_label = ttk.Label(self.rssi_frame, text="-80 dBm")
        self.rssi_label.pack(side=tk.LEFT, padx=5)
        self.rssi_var.trace_add("write", lambda *args: self.rssi_label.config(
            text=f"{self.rssi_var.get()} dBm"))
        
        # Time window filter
        self.time_frame = ttk.Frame(self.controls_frame)
        self.time_frame.pack(fill=tk.X, pady=5)
        ttk.Label(self.time_frame, text="Time window:").pack(side=tk.LEFT)
        
        self.time_var = tk.IntVar(value=300)
        time_options = [("1 minute", 60), ("5 minutes", 300), 
                      ("15 minutes", 900), ("1 hour", 3600)]
        
        self.time_combo = ttk.Combobox(self.time_frame, state="readonly",
                                   values=[t[0] for t in time_options])
        self.time_combo.current(1)
        self.time_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.time_combo.bind("<<ComboboxSelected>>", 
                          lambda e: self.time_var.set(time_options[self.time_combo.current()][1]))
        self.time_combo.bind("<<ComboboxSelected>>", lambda e: self.update_display(), add="+")
        
        # Search filter
        self.search_frame = ttk.Frame(self.controls_frame)
        self.search_frame.pack(fill=tk.X, pady=5)
        ttk.Label(self.search_frame, text="Search:").pack(side=tk.LEFT)
        
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self.search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.search_var.trace_add("write", lambda *args: self.update_display())
        
        # Status section
        self.status_frame = ttk.LabelFrame(self.right_frame, text="Status", padding=10)
        self.status_frame.pack(fill=tk.X, pady=5)
        
        self.status_label = ttk.Label(self.status_frame, text="Initializing...")
        self.status_label.pack(fill=tk.X)
        
        self.count_label = ttk.Label(self.status_frame, text="Devices: 0 WiFi, 0 BLE")
        self.count_label.pack(fill=tk.X)
        
        # Scan control
        self.scan_frame = ttk.Frame(self.status_frame)
        self.scan_frame.pack(fill=tk.X, pady=5)
        
        self.scan_button = ttk.Button(self.scan_frame, text="Start Scanning", 
                                   command=self.toggle_scanning)
        self.scan_button.pack(side=tk.LEFT, padx=5)
        
        # Device info section
        self.device_frame = ttk.LabelFrame(self.right_frame, text="Device Info", padding=10)
        self.device_frame.pack(fill=tk.BOTH, pady=5, expand=True)
        
        self.info_text = tk.Text(self.device_frame, height=25, width=45, wrap=tk.WORD,
                              bg="#111111", fg="#FFFFFF", font=("Courier", 10))
        self.info_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Export button
        self.export_button = ttk.Button(self.device_frame, text="Export Data",
                                     command=self.export_data)
        self.export_button.pack(pady=5)
        
    def init_app(self):
        """Initialize the application"""
        self.radar.start_sweep()
        self.update_display()
        self.status_label.config(text="Ready")
        
    def select_device(self, signal_id):
        """Handle device selection"""
        found = None
        for obs in self.observations.get_all():
            if obs.signal_id == signal_id:
                found = obs
                break
                
        self.radar.selected = found
        self.update_device_info(found)
        
    def update_device_info(self, obs: Optional[Observation]):
        """Update device info panel"""
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete(1.0, tk.END)
        
        if not obs:
            self.info_text.insert(tk.END, "No device selected")
            self.info_text.config(state=tk.DISABLED)
            return
            
        # Basic info
        self.info_text.insert(tk.END, f"Device: {obs.signal_id}\n", "heading")
        self.info_text.insert(tk.END, f"Type: {obs.radio.upper()}\n")
        self.info_text.insert(tk.END, f"RSSI: {obs.rssi_dbm} dBm\n")
        
        obs_time = datetime.fromisoformat(obs.ts.replace('Z', '+00:00')).replace(tzinfo=None)
        self.info_text.insert(tk.END, f"Last seen: {obs_time.strftime('%H:%M:%S')}\n")
        
        # Distance estimation
        ref_rssi = self.radar.wifi_ref if obs.radio == "wifi" else self.radar.ble_ref
        distance = 10**((ref_rssi - obs.rssi_dbm)/(10 * self.radar.path_loss))
        self.info_text.insert(tk.END, f"Est. distance: {distance:.1f}m\n")
        
        # Radio-specific info
        if obs.radio == "wifi":
            self.info_text.insert(tk.END, "\nWiFi Details:\n", "heading")
            if obs.ssid:
                self.info_text.insert(tk.END, f"SSID: {obs.ssid}\n")
            if obs.channel:
                self.info_text.insert(tk.END, f"Channel: {obs.channel}\n")
            if obs.freq_mhz:
                self.info_text.insert(tk.END, f"Frequency: {obs.freq_mhz} MHz\n")
                
            if obs.wifi_info:
                if obs.wifi_info.band:
                    self.info_text.insert(tk.END, f"Band: {obs.wifi_info.band} GHz\n")
                if obs.wifi_info.security:
                    self.info_text.insert(tk.END, f"Security: {obs.wifi_info.security}\n")
                if obs.wifi_info.std:
                    self.info_text.insert(tk.END, f"Standard: 802.11{obs.wifi_info.std}\n")
                    
        elif obs.radio == "ble":
            self.info_text.insert(tk.END, "\nBLE Details:\n", "heading")
            if obs.ble_info:
                if obs.ble_info.local_name:
                    self.info_text.insert(tk.END, f"Name: {obs.ble_info.local_name}\n")
                if obs.ble_info.is_connectable is not None:
                    self.info_text.insert(tk.END, f"Connectable: {obs.ble_info.is_connectable}\n")
                    
            if obs.service_uuids:
                self.info_text.insert(tk.END, "\nService UUIDs:\n", "heading")
                for uuid in obs.service_uuids:
                    self.info_text.insert(tk.END, f"- {uuid}\n")
        
        self.info_text.config(state=tk.DISABLED)
        self.info_text.tag_configure("heading", foreground="#00FFFF")
        
    def update_display(self):
        """Update the radar display"""
        now = datetime.now()
        filter_ts = now - timedelta(seconds=self.time_var.get())
        min_rssi = self.rssi_var.get()
        show_wifi = self.show_wifi_var.get()
        show_ble = self.show_ble_var.get()
        query = self.search_var.get()
        
        observations = self.observations.get_all()
        self.radar.draw_dots(observations, filter_ts, min_rssi, show_wifi, show_ble, query)
        
        # Update counters
        filtered = self.radar.filter_observations(observations, filter_ts, min_rssi, show_wifi, show_ble, query)
        wifi_count = sum(1 for o in filtered if o.radio == "wifi")
        ble_count = sum(1 for o in filtered if o.radio == "ble")
        self.count_label.config(text=f"Devices: {wifi_count} WiFi, {ble_count} BLE")
        
        self.root.after(1000, self.update_display)
        
    def toggle_scanning(self):
        """Start or stop scanning"""
        if self.scanning:
            self.scanning = False
            self.scan_button.config(text="Start Scanning")
            self.status_label.config(text="Scanning stopped")
        else:
            self.scanning = True
            self.scan_button.config(text="Stop Scanning")
            self.status_label.config(text="Scanning...")
            
            if not self.scan_thread or not self.scan_thread.is_alive():
                self.scan_thread = threading.Thread(target=self.scan_loop)
                self.scan_thread.daemon = True
                self.scan_thread.start()
                
    def scan_loop(self):
        """Background scanning loop"""
        while self.scanning:
            try:
                # Scan WiFi
                wifi_results = self.scan_wifi()
                for result in wifi_results:
                    obs = self.create_wifi_observation(result)
                    self.observations.add(obs)
                
                # Scan BLE
                if BLEAK_AVAILABLE:
                    ble_results = asyncio.run(self.scan_ble())
                    for result in ble_results:
                        obs = self.create_ble_observation(result)
                        self.observations.add(obs)
                        
            except Exception as e:
                print(f"Error during scan: {e}")
                traceback.print_exc()
            
            time.sleep(SCAN_INTERVAL)
            
    def scan_wifi(self):
        """Scan for WiFi networks"""
        try:
            if platform.system() == "Windows":
                return self.scan_wifi_windows()
            else:
                return []
        except Exception as e:
            print(f"WiFi scan error: {e}")
            return []
            
    def scan_wifi_windows(self):
        """Windows WiFi scanning"""
        try:
            out = subprocess.check_output(["netsh", "wlan", "show", "networks", "mode=bssid"], 
                                         text=True, errors="ignore")
            blocks = re.split(r"\n\s*SSID \d+ :", out)
            results = []
            
            for block in blocks[1:]:
                lines = block.strip().splitlines()
                if not lines:
                    continue
                
                ssid = lines[0].strip()
                
                for b in re.split(r"\n\s*BSSID \d+ :", block)[1:]:
                    lines = b.splitlines()
                    if not lines:
                        continue
                        
                    bssid = lines[0].strip()
                    signal = None
                    channel = None
                    
                    for ln in lines[1:]:
                        if "Signal" in ln:
                            m = re.search(r"(\d+)%", ln)
                            signal = int(m.group(1)) if m else None
                        if "Channel" in ln:
                            m = re.search(r"(\d+)", ln)
                            channel = int(m.group(1)) if m else None
                    
                    if bssid and signal is not None:
                        results.append({
                            "ssid": ssid,
                            "bssid": bssid,
                            "rssi_dbm": int(round(signal/2 - 100)),
                            "channel": channel
                        })
            
            return results
        except Exception as e:
            print(f"Windows WiFi scan failed: {e}")
            return []
            
    async def scan_ble(self):
        """Scan for BLE devices"""
        try:
            devices = await BleakScanner.discover(timeout=5.0)
            results = []
            
            for device in devices:
                results.append({
                    "address": device.address,
                    "rssi_dbm": device.rssi,
                    "name": device.name,
                    "service_uuids": getattr(device, "metadata", {}).get("uuids", []) if hasattr(device, "metadata") else []
                })
                
            return results
        except Exception as e:
            print(f"BLE scan error: {e}")
            return []
            
    def create_wifi_observation(self, result):
        """Create WiFi observation from scan result"""
        wifi_info = WifiInfo()
        if result.get("channel"):
            if result["channel"] <= 14:
                wifi_info.band = "2.4"
            elif result["channel"] <= 165:
                wifi_info.band = "5"
            else:
                wifi_info.band = "6"
        
        return Observation(
            observer_id=self.observer_id,
            radio="wifi",
            signal_id=result["bssid"],
            ssid=result.get("ssid"),
            channel=result.get("channel"),
            rssi_dbm=result["rssi_dbm"],
            observer_location=GeoPoint(lat=0.0, lon=0.0),
            wifi_info=wifi_info
        )
        
    def create_ble_observation(self, result):
        """Create BLE observation from scan result"""
        ble_info = BleInfo(
            local_name=result.get("name"),
            is_connectable=True
        )
        
        return Observation(
            observer_id=self.observer_id,
            radio="ble",
            signal_id=result["address"],
            service_uuids=result.get("service_uuids"),
            rssi_dbm=result["rssi_dbm"],
            observer_location=GeoPoint(lat=0.0, lon=0.0),
            ble_info=ble_info
        )
        
    def export_data(self):
        """Export observation data to JSON file"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Export Observation Data"
            )
            
            if filename:
                observations = self.observations.get_all()
                data = [obs.model_dump() for obs in observations]
                
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                    
                messagebox.showinfo("Export Complete", f"Exported {len(observations)} observations to {filename}")
                
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export data: {e}")

def main():
    """Main function to run the enhanced radar app"""
    root = tk.Tk()
    app = EnhancedRFRadarApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
