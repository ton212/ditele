"""Location/GPS data transformer."""
from typing import Dict, Any, Optional
from telemetry.devices.common import clean_value


def transform_location(location_data: Optional[Dict]) -> Dict[str, Any]:
    """Transform location/GPS data.
    
    Args:
        location_data: Location data from the telemetry payload
    
    Returns:
        Dictionary with transformed location fields
    """
    if not location_data:
        return {
            "latitude": None,
            "longitude": None,
            "heading": None,
            "gps_accuracy": None,
        }
    
    return {
        "latitude": clean_value(location_data.get("latitude")),
        "longitude": clean_value(location_data.get("longitude")),
        "heading": clean_value(location_data.get("heading")),
        "gps_accuracy": clean_value(location_data.get("accuracy")),
    }

