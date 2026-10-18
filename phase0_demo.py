"""
Phase 0 demonstration of the RF mapping system.
Integrates all components: scanners, storage, localization, and visualization.
"""
import asyncio
import logging
import time
from typing import List
from datetime import datetime, timedelta

from libs.core import Observation, GeoPoint
from scanners import WiFiScanner, BLEScannerSync, ScannerNotAvailableError
from storage import LocalStorage
from libs.localize import WalkMapperLocalizer
from apps.desktop_py.visualizer import RFVisualizer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RFMapperDemo:
    """Phase 0 demonstration of the RF mapping system."""
    
    def __init__(self):
        self.storage = LocalStorage()
        self.visualizer = RFVisualizer(self.storage)
        self.localizer = WalkMapperLocalizer()
        
        # Demo location (NYC area)
        self.demo_location = GeoPoint(lat=40.7128, lon=-74.0060, accuracy_m=5.0)
        
        # Initialize scanners
        self.scanners = []
        self._init_scanners()
    
    def _init_scanners(self):
        """Initialize available scanners."""
        observer_id = f"demo_scanner_{int(time.time())}"
        
        # Try to initialize WiFi scanner
        try:
            wifi_scanner = WiFiScanner(observer_id, self.demo_location)
            self.scanners.append(wifi_scanner)
            logger.info("WiFi scanner initialized")
        except ScannerNotAvailableError as e:
            logger.warning(f"WiFi scanner not available: {e}")
        
        # Try to initialize BLE scanner
        try:
            ble_scanner = BLEScannerSync(observer_id, self.demo_location)
            self.scanners.append(ble_scanner)
            logger.info("BLE scanner initialized")
        except ScannerNotAvailableError as e:
            logger.warning(f"BLE scanner not available: {e}")
        
        if not self.scanners:
            logger.warning("No scanners available - will generate demo data")
    
    def generate_demo_data(self) -> List[Observation]:
        """Generate synthetic demo data for testing."""
        import random
        import uuid
        
        observations = []
        base_time = datetime.utcnow()
        
        # Generate WiFi observations
        wifi_networks = [
            {"ssid": "CoffeeShop_WiFi", "bssid": "aa:bb:cc:dd:ee:01"},
            {"ssid": "Office_Network", "bssid": "aa:bb:cc:dd:ee:02"},
            {"ssid": "Home_Router", "bssid": "aa:bb:cc:dd:ee:03"},
        ]
        
        # Generate BLE observations
        ble_devices = [
            {"name": "iPhone_12", "address": "11:22:33:44:55:01"},
            {"name": "Samsung_Watch", "address": "11:22:33:44:55:02"},
            {"name": "AirPods_Pro", "address": "11:22:33:44:55:03"},
        ]
        
        # Simulate walking around and detecting signals
        for i in range(50):
            # Simulate movement
            lat_offset = random.uniform(-0.001, 0.001)  # ~100m radius
            lon_offset = random.uniform(-0.001, 0.001)
            
            observer_location = GeoPoint(
                lat=self.demo_location.lat + lat_offset,
                lon=self.demo_location.lon + lon_offset,
                accuracy_m=random.uniform(3, 10)
            )
            
            # Generate WiFi observations
            for network in wifi_networks:
                if random.random() < 0.7:  # 70% chance to detect
                    # Distance-based RSSI simulation
                    distance = abs(lat_offset) + abs(lon_offset)
                    base_rssi = -40
                    rssi = base_rssi - int(distance * 50000) + random.randint(-10, 10)
                    
                    obs = Observation(
                        observer_id="demo_scanner",
                        radio="wifi",
                        signal_id=network["bssid"],
                        ssid=network["ssid"],
                        bssid=network["bssid"],
                        rssi_dbm=max(rssi, -90),
                        channel=random.choice([1, 6, 11]),
                        freq_mhz=2412 + (random.choice([1, 6, 11]) - 1) * 5,
                        observer_location=observer_location,
                        ts=(base_time + timedelta(seconds=i*10)).isoformat()
                    )
                    observations.append(obs)
            
            # Generate BLE observations
            for device in ble_devices:
                if random.random() < 0.5:  # 50% chance to detect
                    distance = abs(lat_offset) + abs(lon_offset)
                    base_rssi = -50
                    rssi = base_rssi - int(distance * 60000) + random.randint(-15, 5)
                    
                    obs = Observation(
                        observer_id="demo_scanner",
                        radio="ble",
                        signal_id=device["address"],
                        device_name=device["name"],
                        rssi_dbm=max(rssi, -100),
                        observer_location=observer_location,
                        ts=(base_time + timedelta(seconds=i*10)).isoformat()
                    )
                    observations.append(obs)
        
        logger.info(f"Generated {len(observations)} demo observations")
        return observations
    
    def run_scan_session(self, duration_seconds: int = 30) -> List[Observation]:
        """Run a scanning session with available scanners."""
        if not self.scanners:
            logger.info("No real scanners available, using demo data")
            return self.generate_demo_data()
        
        observations = []
        
        # Start all scanners
        for scanner in self.scanners:
            try:
                scanner.start()
                logger.info(f"Started {scanner.__class__.__name__}")
            except Exception as e:
                logger.error(f"Failed to start {scanner.__class__.__name__}: {e}")
        
        # Collect observations
        start_time = time.time()
        while time.time() - start_time < duration_seconds:
            for scanner in self.scanners:
                try:
                    for obs in scanner.observations():
                        observations.append(obs)
                        logger.debug(f"Collected observation: {obs.radio} {obs.signal_id} {obs.rssi_dbm}dBm")
                except Exception as e:
                    logger.error(f"Scanner error: {e}")
            
            time.sleep(2)  # Scan every 2 seconds
        
        # Stop all scanners
        for scanner in self.scanners:
            try:
                scanner.stop()
            except Exception as e:
                logger.error(f"Failed to stop scanner: {e}")
        
        logger.info(f"Collected {len(observations)} observations in {duration_seconds}s")
        return observations
    
    def process_and_visualize(self, observations: List[Observation]):
        """Process observations and create visualizations."""
        if not observations:
            logger.warning("No observations to process")
            return
        
        # Store observations
        self.storage.store_observations(observations)
        
        # Group observations by signal for localization
        signal_groups = {}
        for obs in observations:
            if obs.signal_id not in signal_groups:
                signal_groups[obs.signal_id] = []
            signal_groups[obs.signal_id].append(obs)
        
        # Estimate locations for signals with enough observations
        estimates_created = 0
        for signal_id, signal_obs in signal_groups.items():
            if len(signal_obs) >= 3:  # Minimum for clustering
                estimate = self.localizer.estimate_location(signal_obs)
                if estimate:
                    self.storage.store_location_estimate(estimate)
                    estimates_created += 1
                    logger.info(f"Created location estimate for {signal_id}: "
                              f"({estimate.estimated_location.lat:.6f}, {estimate.estimated_location.lon:.6f}) "
                              f"confidence={estimate.confidence:.2f}")
        
        logger.info(f"Created {estimates_created} location estimates")
        
        # Create visualizations
        self._create_visualizations()
    
    def _create_visualizations(self):
        """Create and export various visualizations."""
        logger.info("Creating visualizations...")
        
        # 1. Observation scatter plot
        obs_map = self.visualizer.create_observation_map()
        obs_path = self.visualizer.export_html(obs_map, "output/observations_map.html")
        logger.info(f"Observations map: {obs_path}")
        
        # 2. Signal heatmap
        heatmap = self.visualizer.create_heatmap()
        heatmap_path = self.visualizer.export_html(heatmap, "output/signal_heatmap.html")
        logger.info(f"Signal heatmap: {heatmap_path}")
        
        # 3. Transmitter locations
        transmitter_map = self.visualizer.create_transmitter_map()
        transmitter_path = self.visualizer.export_html(transmitter_map, "output/transmitter_locations.html")
        logger.info(f"Transmitter locations: {transmitter_path}")
        
        # 4. 3D signal visualization
        signal_3d = self.visualizer.create_3d_signal_map()
        signal_3d_path = self.visualizer.export_html(signal_3d, "output/signal_3d_map.html")
        logger.info(f"3D signal map: {signal_3d_path}")
        
        # Print statistics
        stats = self.storage.get_stats()
        logger.info("=== System Statistics ===")
        for key, value in stats.items():
            logger.info(f"{key}: {value}")

def main():
    """Main demonstration function."""
    print("🚀 RF Mapper Phase 0 Demo")
    print("=" * 50)
    
    demo = RFMapperDemo()
    
    # Option 1: Run real scanning session (if scanners available)
    print("\n1. Running scanning session...")
    observations = demo.run_scan_session(duration_seconds=10)  # Short demo
    
    # Option 2: Use demo data if no real observations
    if not observations:
        print("No real observations collected, using demo data...")
        observations = demo.generate_demo_data()
    
    # Process and visualize
    print(f"\n2. Processing {len(observations)} observations...")
    demo.process_and_visualize(observations)
    
    print("\n✅ Demo complete! Check the 'output/' directory for visualizations.")
    print("\nGenerated files:")
    print("- observations_map.html: Scatter plot of all observations")
    print("- signal_heatmap.html: Heatmap showing signal density")
    print("- transmitter_locations.html: Estimated transmitter locations")
    print("- signal_3d_map.html: 3D visualization with signal strength as height")
    
    # Show how to start the FastAPI gateway
    print("\n🌐 To start the web gateway:")
    print("python -m uvicorn services.gateway:app --reload --host 0.0.0.0 --port 8000")

if __name__ == "__main__":
    main()
