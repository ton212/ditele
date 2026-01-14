"""BYDAutoPM2p5Device transformer."""
from typing import Dict, Any
from telemetry.devices.common import clean_value


def transform_pm25(device_data: Dict) -> Dict[str, Any]:
    """Transform PM2.5 device data.
    
    Args:
        device_data: BYDAutoPM2p5Device data
    
    Returns:
        Dictionary with transformed PM2.5 fields
    """
    pm25_value = device_data.get("getPM2p5Value")
    if isinstance(pm25_value, list) and len(pm25_value) >= 2:
        return {
            "pm25_inside": clean_value(pm25_value[0]),
            "pm25_outside": clean_value(pm25_value[1]),
        }
    
    return {
        "pm25_inside": None,
        "pm25_outside": None,
    }

