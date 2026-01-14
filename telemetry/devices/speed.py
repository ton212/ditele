"""BYDAutoSpeedDevice transformer."""
from typing import Dict, Any
from telemetry.devices.common import clean_value


def transform_speed(device_data: Dict) -> Dict[str, Any]:
    """Transform speed device data.
    
    Args:
        device_data: BYDAutoSpeedDevice data
    
    Returns:
        Dictionary with transformed speed fields
    """
    return {
        "speed": clean_value(device_data.get("getCurrentSpeed")),
    }

