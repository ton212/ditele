"""Data validation utilities."""
from typing import Optional
from datetime import datetime


def validate_timestamp(timestamp_ms: int, max_age_hours: int = 24) -> bool:
    """Validate timestamp is recent.
    
    Args:
        timestamp_ms: Unix timestamp in milliseconds
        max_age_hours: Maximum age in hours (default: 24)
    
    Returns:
        True if timestamp is valid, False otherwise
    """
    now_ms = int(datetime.now().timestamp() * 1000)
    age_ms = now_ms - timestamp_ms
    max_age_ms = max_age_hours * 60 * 60 * 1000
    
    # Check if timestamp is too old
    if age_ms > max_age_ms:
        return False
    
    # Check if timestamp is too far in future (more than 1 hour)
    if timestamp_ms > now_ms + (60 * 60 * 1000):
        return False
    
    return True


def validate_gps_coordinates(latitude: Optional[float], longitude: Optional[float]) -> bool:
    """Validate GPS coordinates are within reasonable bounds.
    
    Args:
        latitude: Latitude in degrees
        longitude: Longitude in degrees
    
    Returns:
        True if coordinates are valid, False otherwise
    """
    if latitude is None or longitude is None:
        return True  # GPS is optional, so None is valid
    
    return -90 <= latitude <= 90 and -180 <= longitude <= 180


def validate_heading(heading: Optional[float]) -> bool:
    """Validate heading is within 0-360 degrees.
    
    Args:
        heading: Heading in degrees
    
    Returns:
        True if heading is valid, False otherwise
    """
    if heading is None:
        return True  # Heading is optional
    
    return 0 <= heading <= 360


def validate_gps_accuracy(accuracy: Optional[float]) -> bool:
    """Validate GPS accuracy is reasonable.
    
    Args:
        accuracy: GPS accuracy in meters
    
    Returns:
        True if accuracy is valid, False otherwise
    """
    if accuracy is None:
        return True  # Accuracy is optional
    
    # Reasonable range: 0 to 1000 meters
    return 0 <= accuracy <= 1000


def validate_battery_level(level: Optional[int]) -> bool:
    """Validate battery level is within 0-100.
    
    Args:
        level: Battery level percentage
    
    Returns:
        True if level is valid, False otherwise
    """
    if level is None:
        return True  # Battery level is optional
    
    return 0 <= level <= 100

