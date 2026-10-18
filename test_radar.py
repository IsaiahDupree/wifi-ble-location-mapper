#!/usr/bin/env python3
"""
Simple test version of the Enhanced RF Radar
"""

import tkinter as tk
from tkinter import ttk
import math
import threading
import time
from datetime import datetime
import platform

# Simple test data
class TestDevice:
    def __init__(self, signal_id, radio, rssi_dbm, name=None):
        self.signal_id = signal_id
        self.radio = radio
        self.rssi_dbm = rssi_dbm
        self.name = name
        self.ts = datetime.now()

class SimpleRadarDisplay(tk.Canvas):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(background="#000000")
        
        self.devices = []
        self.sweep_angle = 0
        self.selected = None
        
        self.bind("<Button-1>", self.on_click)
        
    def start_sweep(self):
        self.update_sweep()
        
    def update_sweep(self):
        self.sweep_angle = (self.sweep_angle + 3) % 360
        self.draw_radar()
        self.after(50, self.update_sweep)
        
    def draw_radar(self):
        width = self.winfo_width()
        height = self.winfo_height()
        
        if width <= 1 or height <= 1:
            width = 600
            height = 600
            
        cx = width / 2
        cy = height / 2
        radius = min(width, height) / 2 - 10
        
        self.delete("radar_bg")
        self.delete("device")
        
        # Draw radar circles
        for i in range(1, 6):
            r = radius * i / 5
            self.create_oval(cx - r, cy - r, cx + r, cy + r, 
                          outline="#003300", width=1, tags="radar_bg")
            
        # Draw range labels
        for i in range(1, 6):
            dist = 50 * i / 5
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
        
        # Draw devices
        for device in self.devices:
            # Simple distance calculation
            distance = abs(device.rssi_dbm + 30) * 2  # Simple conversion
            if distance > 50:
                distance = 50
                
            norm_distance = distance / 50
            dot_radius = radius * norm_distance
            
            # Simple angle from hash
            angle = hash(device.signal_id) % 360
            angle_rad = math.radians(angle)
            
            x = cx + dot_radius * math.cos(angle_rad)
            y = cy - dot_radius * math.sin(angle_rad)
            
            color = "#00FF00" if device.radio == "wifi" else "#00AAFF"
            dot_size = 5
            
            self.create_oval(x - dot_size, y - dot_size, x + dot_size, y + dot_size,
                           fill=color, tags=("device", device.signal_id))
                           
    def add_device(self, device):
        # Remove existing device with same ID
        self.devices = [d for d in self.devices if d.signal_id != device.signal_id]
        self.devices.append(device)
        
    def on_click(self, event):
        print(f"Clicked at {event.x}, {event.y}")

class SimpleRFRadarApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Simple RF Radar Test")
        self.root.geometry("800x600")
        self.root.configure(background="#000000")
        
        self.scanning = False
        
        self.create_ui()
        self.init_app()
        
    def create_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Radar display
        self.radar = SimpleRadarDisplay(main_frame, width=600, height=500, highlightthickness=0)
        self.radar.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Control panel
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        
        ttk.Label(control_frame, text="RF Radar Test").pack(pady=10)
        
        self.scan_button = ttk.Button(control_frame, text="Start Scan", command=self.toggle_scan)
        self.scan_button.pack(pady=5)
        
        ttk.Button(control_frame, text="Add Test Device", command=self.add_test_device).pack(pady=5)
        
        self.status_label = ttk.Label(control_frame, text="Ready")
        self.status_label.pack(pady=10)
        
        self.device_count_label = ttk.Label(control_frame, text="Devices: 0")
        self.device_count_label.pack()
        
    def init_app(self):
        self.radar.start_sweep()
        self.add_test_device()  # Add initial test device
        
    def toggle_scan(self):
        if self.scanning:
            self.scanning = False
            self.scan_button.config(text="Start Scan")
            self.status_label.config(text="Stopped")
        else:
            self.scanning = True
            self.scan_button.config(text="Stop Scan")
            self.status_label.config(text="Scanning...")
            threading.Thread(target=self.scan_loop, daemon=True).start()
            
    def scan_loop(self):
        count = 0
        while self.scanning:
            # Simulate finding devices
            if count % 3 == 0:
                device = TestDevice(f"wifi-{count}", "wifi", -45 - (count % 30))
                self.radar.add_device(device)
            else:
                device = TestDevice(f"ble-{count}", "ble", -60 - (count % 25))
                self.radar.add_device(device)
                
            self.device_count_label.config(text=f"Devices: {len(self.radar.devices)}")
            count += 1
            time.sleep(2)
            
    def add_test_device(self):
        import random
        device_type = random.choice(["wifi", "ble"])
        rssi = random.randint(-80, -30)
        device = TestDevice(f"test-{len(self.radar.devices)}", device_type, rssi)
        self.radar.add_device(device)
        self.device_count_label.config(text=f"Devices: {len(self.radar.devices)}")

def main():
    root = tk.Tk()
    app = SimpleRFRadarApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
