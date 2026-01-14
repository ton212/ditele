"""BYDAutoStatisticDevice transformer."""
from typing import Dict, Any
from telemetry.devices.common import clean_value


def transform_statistic(device_data: Dict) -> Dict[str, Any]:
    """Transform statistic device data.
    
    Args:
        device_data: BYDAutoStatisticDevice data
    
    Returns:
        Dictionary with transformed statistic fields
    """
    return {
        "odometer": clean_value(device_data.get("getTotalMileageValue")),
        "battery_level": clean_value(device_data.get("getSOCBatteryPercentage")),
        "battery_range_km": clean_value(device_data.get("getElecDrivingRangeValue")),
    }

