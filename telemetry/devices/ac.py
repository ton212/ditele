"""BYDAutoAcDevice transformer."""
from typing import Dict, Any, Optional, Union
from telemetry.devices.common import (
    get_nested_value,
    is_error_value,
    to_boolean,
    convert_temperature_to_celsius,
)


def map_wind_mode(value: Union[int, None]) -> Optional[str]:
    """Map AC wind mode integer to string.
    
    Maps:
        0 → "Auto"
        1 → "Face"
        2 → "Face+Feet"
        3 → "Feet"
        4 → "Defrost+Feet"
        5 → "Defrost"
        6 → "Defrost+Face+Feet"
        7 → "Defrost+Face"
    """
    if value is None or is_error_value(value):
        return None
    
    wind_mode_map = {
        0: "Auto",
        1: "Face",
        2: "Face+Feet",
        3: "Feet",
        4: "Defrost+Feet",
        5: "Defrost",
        6: "Defrost+Face+Feet",
        7: "Defrost+Face",
    }
    return wind_mode_map.get(value, "Unknown")


def map_cycle_mode(value: Union[int, None]) -> Optional[str]:
    """Map AC cycle mode integer to string.
    
    Maps:
        0 → "Fresh" (Fresh air from outside)
        1 → "Recirc" (Recirculation - internal air)
    """
    if value is None or is_error_value(value):
        return None
    
    cycle_mode_map = {
        0: "Fresh",
        1: "Recirc",
    }
    return cycle_mode_map.get(value, "Unknown")


def transform_ac(device_data: Dict, temp_unit: Optional[int]) -> Dict[str, Any]:
    """Transform AC device data.
    
    Args:
        device_data: BYDAutoAcDevice data
        temp_unit: Temperature unit from instrument device (1 = C, 2 = F)
    
    Returns:
        Dictionary with transformed AC fields
    """
    driver_temp = convert_temperature_to_celsius(
        get_nested_value(device_data, "getTemprature(int)", "1"),
        temp_unit
    )
    
    # Passenger temp: use driver temp as fallback if passenger temp is not available
    passenger_temp_raw = get_nested_value(device_data, "getTemprature(int)", "4")
    if passenger_temp_raw is not None and not is_error_value(passenger_temp_raw):
        passenger_temp = convert_temperature_to_celsius(passenger_temp_raw, temp_unit)
    else:
        passenger_temp = driver_temp  # Fallback to driver temp
    
    return {
        "is_climate_on": to_boolean(device_data.get("getAcStartState")),
        "driver_temp_setting": driver_temp,
        "passenger_temp_setting": passenger_temp,
        "fan_level": device_data.get("getAcWindLevel") if not is_error_value(device_data.get("getAcWindLevel")) else None,
        "wind_mode": map_wind_mode(device_data.get("getAcWindMode")),
        "cycle_mode": map_cycle_mode(device_data.get("getAcCycleMode")),
        "is_rear_defroster_on": to_boolean(
            get_nested_value(device_data, "getAcDefrostState(int)", "2")
        ),
        "is_front_defroster_on": None,  # Not in sample data
    }

