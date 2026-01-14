"""Value interpreter for telemetry data - handles error values, enums, and conversions."""
from typing import Optional, Union


# Error values that indicate invalid/unavailable data
ERROR_VALUES = {
    -2147482645,  # Method parameter invalid or sensor unavailable
    -2147482648,  # Value unavailable or invalid
    65535,        # 0xFFFF - Value not available/invalid
    255,          # Value unavailable (for arrays)
    -10011,       # Feature not available or error
    -1,           # Invalid or not available
}


def is_error_value(value: Union[int, float, None]) -> bool:
    """Check if a value is an error/invalid value."""
    if value is None:
        return True
    return value in ERROR_VALUES


def clean_value(value: Union[int, float, None]) -> Optional[Union[int, float]]:
    """Clean a value by returning None if it's an error value."""
    if is_error_value(value):
        return None
    return value


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


def to_boolean(value: Union[int, None], true_values: set = {1}, false_value: Optional[int] = None) -> Optional[bool]:
    """Convert integer to boolean.
    
    Args:
        value: Integer value to convert
        true_values: Set of values that represent True (default: {1})
        false_value: Specific value that represents False (if None, any value not in true_values is False)
    
    Returns:
        True, False, or None if value is an error
    """
    if value is None or is_error_value(value):
        return None
    
    if value in true_values:
        return True
    
    if false_value is not None:
        return value == false_value
    
    return False


def convert_tire_pressure_kpa_to_bar(kpa: Union[int, float, None]) -> Optional[float]:
    """Convert tire pressure from kPa to bar.
    
    Args:
        kpa: Pressure in kilopascals
    
    Returns:
        Pressure in bar, or None if value is invalid
    """
    if kpa is None or is_error_value(kpa):
        return None
    
    # Convert kPa to bar (1 bar = 100 kPa)
    return float(kpa) / 100.0


def convert_temperature_to_celsius(value: Union[int, float, None], unit: Optional[int]) -> Optional[float]:
    """Convert temperature to Celsius.
    
    Args:
        value: Temperature value
        unit: Temperature unit (1 = Celsius, 2 = Fahrenheit)
    
    Returns:
        Temperature in Celsius, or None if value is invalid
    """
    if value is None or is_error_value(value):
        return None
    
    if unit == 2:  # Fahrenheit
        # Convert F to C: C = (F - 32) * 5/9
        return (float(value) - 32.0) * 5.0 / 9.0
    elif unit == 1:  # Celsius
        return float(value)
    else:
        # Default to Celsius if unit is unknown
        return float(value)


def convert_pressure_to_bar(value: Union[int, float, None], unit: Optional[int]) -> Optional[float]:
    """Convert pressure to bar.
    
    Args:
        value: Pressure value
        unit: Pressure unit (1 = bar, 2 = psi, 3 = kPa)
    
    Returns:
        Pressure in bar, or None if value is invalid
    """
    if value is None or is_error_value(value):
        return None
    
    if unit == 1:  # bar
        return float(value)
    elif unit == 2:  # psi
        # Convert psi to bar: 1 bar = 14.5038 psi
        return float(value) / 14.5038
    elif unit == 3:  # kPa
        # Convert kPa to bar: 1 bar = 100 kPa
        return float(value) / 100.0
    else:
        # Default to bar if unit is unknown
        return float(value)


def convert_power_to_kw(value: Union[int, float, None], unit: Optional[int]) -> Optional[float]:
    """Convert power to kilowatts.
    
    Args:
        value: Power value
        unit: Power unit (1 = kW, 2 = HP)
    
    Returns:
        Power in kW, or None if value is invalid
    """
    if value is None or is_error_value(value):
        return None
    
    if unit == 1:  # kW
        return float(value)
    elif unit == 2:  # HP (Horse Power)
        # Convert HP to kW: 1 HP = 0.7457 kW
        return float(value) * 0.7457
    else:
        # Default to kW if unit is unknown
        return float(value)

