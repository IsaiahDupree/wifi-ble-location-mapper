"""
Base scanner interface and common utilities.
"""
from abc import ABC, abstractmethod
from typing import Iterator, Optional
import logging
from libs.core import Observation, GeoPoint

logger = logging.getLogger(__name__)

class Scanner(ABC):
    """Base interface for RF scanners."""
    
    def __init__(self, observer_id: str, observer_location: Optional[GeoPoint] = None):
        self.observer_id = observer_id
        self.observer_location = observer_location
        self._running = False
        
    @abstractmethod
    def start(self) -> None:
        """Start the scanner."""
        pass
        
    @abstractmethod
    def stop(self) -> None:
        """Stop the scanner."""
        pass
        
    @abstractmethod
    def observations(self) -> Iterator[Observation]:
        """Yield observations as they are detected."""
        pass
        
    @property
    def is_running(self) -> bool:
        """Check if scanner is currently running."""
        return self._running
        
    def update_location(self, location: GeoPoint) -> None:
        """Update the observer's current location."""
        self.observer_location = location
        logger.debug(f"Updated location for {self.observer_id}: {location.lat}, {location.lon}")

class ScannerError(Exception):
    """Base exception for scanner-related errors."""
    pass

class ScannerNotAvailableError(ScannerError):
    """Raised when scanner hardware/software is not available."""
    pass
