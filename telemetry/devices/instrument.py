"""BYDAutoInstrumentDevice transformer."""
from typing import Dict, Any, Optional
from telemetry.devices.common import (
    clean_value,
    get_nested_value,
    is_error_value,
    convert_temperature_to_celsius,
)


def extract_unit_info(device_data: Dict) -> Dict[str, Optional[int]]:
    """Extract unit information from instrument device.
    
    getUnit(int) structure:
    0 - not used
    1 - temperature_unit (1 = C, 2 = F)
    2 - pressure_unit (1 = bar, 2 = psi, 3 = kPa)
    3 - not used
    4 - power_unit (1 = kW, 2 = HP)
    
    Args:
        device_data: BYDAutoInstrumentDevice data
    
    Returns:
        Dictionary with temp_unit, pressure_unit, power_unit
    """
    unit_info = device_data.get("getUnit(int)", {})
    if isinstance(unit_info, dict):
        return {
            "temp_unit": clean_value(unit_info.get("1")),
            "pressure_unit": clean_value(unit_info.get("2")),
            "power_unit": clean_value(unit_info.get("4")),
        }
    return {
        "temp_unit": None,
        "pressure_unit": None,
        "power_unit": None,
    }


def transform_instrument(device_data: Dict) -> Dict[str, Any]:
    """Transform instrument device data.
    
    Args:
        device_data: BYDAutoInstrumentDevice data
    
    Returns:
        Dictionary with transformed instrument fields
    """
    units = extract_unit_info(device_data)
    temp_unit = units["temp_unit"]
    
    # Tire pressures (store in original unit, no conversion needed)
    # Note: Values are stored as integers where actual value = raw_value / 10
    # e.g., 394 = 39.4 (in whatever unit is set: bar/kPa/psi)
    raw_pressure_fl = get_nested_value(device_data, "getWheelPressure(int)", "1")
    raw_pressure_fr = get_nested_value(device_data, "getWheelPressure(int)", "2")
    raw_pressure_rl = get_nested_value(device_data, "getWheelPressure(int)", "3")
    raw_pressure_rr = get_nested_value(device_data, "getWheelPressure(int)", "4")
    
    # Convert from integer representation (divide by 10) - store in original unit
    def normalize_pressure(value):
        if value is None or is_error_value(value):
            return None
        return float(value) / 10.0
    
    # Tire temperatures (convert from integer representation, then to Celsius)
    # Note: Values may be stored in two formats:
    # - Direct format: 29 = 29°C (when value < 100, already in correct units)
    # - Scaled format: 840 = 84.0°F (when value >= 100, needs division by 10)
    raw_temp_fl = get_nested_value(device_data, "getWheelTemperature(int)", "1")
    raw_temp_fr = get_nested_value(device_data, "getWheelTemperature(int)", "2")
    raw_temp_rl = get_nested_value(device_data, "getWheelTemperature(int)", "3")
    raw_temp_rr = get_nested_value(device_data, "getWheelTemperature(int)", "4")
    
    def normalize_tire_temp(value):
        if value is None or is_error_value(value):
            return None
        val = float(value)
        # If value >= 100, it's in scaled format (e.g., 840 = 84.0)
        # If value < 100, it's already in correct format (e.g., 29 = 29.0)
        return val / 10.0 if val >= 100 else val
    
    temp_fl = normalize_tire_temp(raw_temp_fl)
    temp_fr = normalize_tire_temp(raw_temp_fr)
    temp_rl = normalize_tire_temp(raw_temp_rl)
    temp_rr = normalize_tire_temp(raw_temp_rr)
    
    return {
        "outside_temp": convert_temperature_to_celsius(
            device_data.get("getOutCarTemperature"),
            temp_unit
        ),
        "inside_temp": convert_temperature_to_celsius(
            device_data.get("getInCarTemperature"),
            temp_unit
        ),
        "tire_pressure_fl": normalize_pressure(raw_pressure_fl),
        "tire_pressure_fr": normalize_pressure(raw_pressure_fr),
        "tire_pressure_rl": normalize_pressure(raw_pressure_rl),
        "tire_pressure_rr": normalize_pressure(raw_pressure_rr),
        "tire_temp_fl": convert_temperature_to_celsius(temp_fl, temp_unit),
        "tire_temp_fr": convert_temperature_to_celsius(temp_fr, temp_unit),
        "tire_temp_rl": convert_temperature_to_celsius(temp_rl, temp_unit),
        "tire_temp_rr": convert_temperature_to_celsius(temp_rr, temp_unit),
        **units,  # Include unit info for use by other devices
    }

