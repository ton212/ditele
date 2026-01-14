"""BYDAutoGearboxDevice transformer."""
from typing import Dict, Any, Optional, Union
from telemetry.devices.common import is_error_value


def map_gear_position(value: Union[int, None]) -> Optional[str]:
    """Map gear position integer to string.
    
    Maps:
        1 → "P" (Park)
        2 → "R" (Reverse)
        3 → "N" (Neutral)
        4 → "D" (Drive)
        5 → "S" (Sport)
        6 → "M" (Manual)
    """
    if value is None or is_error_value(value):
        return None
    
    gear_map = {
        1: "P",
        2: "R",
        3: "N",
        4: "D",
        5: "S",
        6: "M",
    }
    return gear_map.get(value, "Unknown")


def transform_gearbox(device_data: Dict) -> Dict[str, Any]:
    """Transform gearbox device data.
    
    Args:
        device_data: BYDAutoGearboxDevice data
    
    Returns:
        Dictionary with transformed gearbox fields
    """
    return {
        "gear_position": map_gear_position(device_data.get("getGearboxAutoModeType")),
    }

