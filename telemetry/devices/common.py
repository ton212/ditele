"""Common utilities for BYD device transformers."""
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


def get_nested_value(data: dict, *keys: str, default=None):
    """Safely get nested dictionary value."""
    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


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

