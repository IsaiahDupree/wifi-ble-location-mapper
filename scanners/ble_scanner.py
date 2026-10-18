"""
Bluetooth Low Energy scanner implementation using bleak.
"""
import asyncio
import logging
from typing import Iterator, Optional, Dict, Any
from datetime import datetime

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from .base import Scanner, ScannerError, ScannerNotAvailableError
from libs.core import Observation, GeoPoint

logger = logging.getLogger(__name__)

class BLEScanner(Scanner):
    """Bluetooth Low Energy scanner using bleak library."""
    
    def __init__(self, observer_id: str, observer_location: Optional[GeoPoint] = None):
        super().__init__(observer_id, observer_location)
        self._scanner = None
        self._scan_task = None
        self._observations_queue = asyncio.Queue()
        
    def start(self) -> None:
        """Start BLE scanning."""
        self._running = True
        logger.info("Started BLE scanner")
    
    def stop(self) -> None:
        """Stop BLE scanning."""
        self._running = False
        if self._scan_task and not self._scan_task.done():
            self._scan_task.cancel()
        logger.info("Stopped BLE scanner")
    
    def observations(self) -> Iterator[Observation]:
        """Scan for BLE devices and yield observations."""
        if not self._running or not self.observer_location:
            return
            
        try:
            # Run async scan in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._async_scan())
                
                # Yield all queued observations
                while not self._observations_queue.empty():
                    try:
                        observation = self._observations_queue.get_nowait()
                        yield observation
                    except asyncio.QueueEmpty:
                        break
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"BLE scan failed: {e}")
            raise ScannerError(f"BLE scan failed: {e}")
    
    async def _async_scan(self) -> None:
        """Perform async BLE scan."""
        try:
            # Scan for 5 seconds
            devices = await BleakScanner.discover(timeout=5.0, return_adv=True)
            
            for device, adv_data in devices.items():
                if not self._running:
                    break
                    
                observation = self._create_observation(device, adv_data)
                await self._observations_queue.put(observation)
                
        except Exception as e:
            logger.error(f"Async BLE scan failed: {e}")
            raise
    
    def _create_observation(self, device: BLEDevice, adv_data: AdvertisementData) -> Observation:
        """Create an Observation from BLE device data."""
        # Extract service UUIDs
        service_uuids = []
        if adv_data.service_uuids:
            service_uuids = [str(uuid) for uuid in adv_data.service_uuids]
        
        # Get device name
        device_name = device.name or adv_data.local_name
        
        return Observation(
            observer_id=self.observer_id,
            radio="ble",
            signal_id=device.address,
            device_name=device_name,
            service_uuids=service_uuids if service_uuids else None,
            rssi_dbm=adv_data.rssi if adv_data.rssi else -100,
            tx_power_dbm=adv_data.tx_power,
            observer_location=self.observer_location,
            raw={
                "manufacturer_data": dict(adv_data.manufacturer_data) if adv_data.manufacturer_data else None,
                "service_data": dict(adv_data.service_data) if adv_data.service_data else None,
                "platform_data": adv_data.platform_data
            }
        )

class BLEScannerSync(Scanner):
    """Synchronous wrapper for BLE scanner for easier integration."""
    
    def __init__(self, observer_id: str, observer_location: Optional[GeoPoint] = None):
        super().__init__(observer_id, observer_location)
        self._ble_scanner = BLEScanner(observer_id, observer_location)
    
    def start(self) -> None:
        """Start BLE scanning."""
        self._ble_scanner.start()
        self._running = True
    
    def stop(self) -> None:
        """Stop BLE scanning."""
        self._ble_scanner.stop()
        self._running = False
    
    def observations(self) -> Iterator[Observation]:
        """Get BLE observations."""
        if not self._running:
            return
            
        yield from self._ble_scanner.observations()
    
    def update_location(self, location: GeoPoint) -> None:
        """Update observer location."""
        super().update_location(location)
        self._ble_scanner.update_location(location)
