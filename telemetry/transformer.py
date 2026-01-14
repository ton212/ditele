"""Transform raw telemetry data into structured format."""
from typing import Dict, Optional, Any
from datetime import datetime

from telemetry.interpreter import (
    clean_value,
    map_gear_position,
    map_wind_mode,
    map_cycle_mode,
    to_boolean,
    convert_temperature_to_celsius,
    convert_power_to_kw,
    is_error_value,
)


def get_nested_value(data: Dict, *keys: str, default: Any = None) -> Any:
    """Safely get nested dictionary value."""
    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def transform_telemetry_data(raw_data: Dict) -> Dict[str, Any]:
    """Transform raw telemetry data into structured format matching database schema.
    
    Args:
        raw_data: Raw telemetry data from the agent
    
    Returns:
        Dictionary with transformed data matching database model fields
    """
    devices = raw_data.get("devices", {})
    location = raw_data.get("location") or {}  # Handle None case
    
    # Extract basic vehicle metrics
    speed_device = devices.get("BYDAutoSpeedDevice", {})
    statistic_device = devices.get("BYDAutoStatisticDevice", {})
    gearbox_device = devices.get("BYDAutoGearboxDevice", {})
    instrument_device = devices.get("BYDAutoInstrumentDevice", {})
    bodywork_device = devices.get("BYDAutoBodyworkDevice", {})
    
    # Extract AC data
    ac_device = devices.get("BYDAutoAcDevice", {})
    
    # Extract charging data
    charging_device = devices.get("BYDAutoChargingDevice", {})
    
    # Extract tire data
    tire_device = devices.get("BYDAutoTyreDevice", {})
    
    # Extract PM2.5 data
    pm25_device = devices.get("BYDAutoPM2p5Device", {})
    
    # Extract unit information from instrument device
    # getUnit(int) structure:
    # 0 - not used
    # 1 - temperature_unit (1 = C, 2 = F)
    # 2 - pressure_unit (1 = bar, 2 = psi, 3 = kPa)
    # 3 - not used
    # 4 - power_unit (1 = kW, 2 = HP)
    unit_info = instrument_device.get("getUnit(int)", {})
    if isinstance(unit_info, dict):
        temp_unit = clean_value(unit_info.get("1"))
        pressure_unit = clean_value(unit_info.get("2"))
        power_unit = clean_value(unit_info.get("4"))
    else:
        temp_unit = None
        pressure_unit = None
        power_unit = None
    
    # Build transformed data
    transformed = {
        # GPS fields (from location object, nullable)
        "latitude": clean_value(location.get("latitude")),
        "longitude": clean_value(location.get("longitude")),
        "heading": clean_value(location.get("heading")),
        "gps_accuracy": clean_value(location.get("accuracy")),
        
        # Basic vehicle metrics
        "speed": clean_value(speed_device.get("getCurrentSpeed")),
        "odometer": clean_value(statistic_device.get("getTotalMileageValue")),
        "battery_level": clean_value(statistic_device.get("getSOCBatteryPercentage")),
        "battery_range_km": clean_value(statistic_device.get("getElecDrivingRangeValue")),
        "outside_temp": convert_temperature_to_celsius(
            instrument_device.get("getOutCarTemperature"),
            temp_unit
        ),
        "inside_temp": convert_temperature_to_celsius(
            instrument_device.get("getInCarTemperature"),
            temp_unit
        ),
        "power": None,  # Not directly available in sample, may need to calculate
        
        # Gear position
        "gear_position": map_gear_position(gearbox_device.get("getGearboxAutoModeType")),
        
        # AC fields
        "is_climate_on": to_boolean(ac_device.get("getAcStartState")),
        "driver_temp_setting": convert_temperature_to_celsius(
            get_nested_value(ac_device, "getTemprature(int)", "1"),
            temp_unit
        ),
        # Passenger temp: use driver temp as fallback if passenger temp is not available
        "passenger_temp_setting": None,  # Will be set below
        "fan_level": clean_value(ac_device.get("getAcWindLevel")),
        "wind_mode": map_wind_mode(ac_device.get("getAcWindMode")),
        "cycle_mode": map_cycle_mode(ac_device.get("getAcCycleMode")),
        "is_rear_defroster_on": to_boolean(
            get_nested_value(ac_device, "getAcDefrostState(int)", "2")
        ),
        "is_front_defroster_on": None,  # Not in sample data
    }
    
    # Set passenger temp: use driver temp as fallback if passenger temp is not available or is error
    passenger_temp_raw = get_nested_value(ac_device, "getTemprature(int)", "4")
    if passenger_temp_raw is not None and not is_error_value(passenger_temp_raw):
        transformed["passenger_temp_setting"] = convert_temperature_to_celsius(passenger_temp_raw, temp_unit)
    else:
        # Fallback to driver temp if passenger temp is not available
        transformed["passenger_temp_setting"] = transformed["driver_temp_setting"]
    
    # Tire pressures (store in original unit, no conversion needed)
    # Note: Values are stored as integers where actual value = raw_value / 10
    # e.g., 394 = 39.4 (in whatever unit is set: bar/kPa/psi)
    # The unit is determined by getUnit[2] (1=bar, 2=psi, 3=kPa)
    raw_pressure_fl = get_nested_value(instrument_device, "getWheelPressure(int)", "1")
    raw_pressure_fr = get_nested_value(instrument_device, "getWheelPressure(int)", "2")
    raw_pressure_rl = get_nested_value(instrument_device, "getWheelPressure(int)", "3")
    raw_pressure_rr = get_nested_value(instrument_device, "getWheelPressure(int)", "4")
    
    # Convert from integer representation (divide by 10) - store in original unit
    transformed["tire_pressure_fl"] = float(raw_pressure_fl) / 10.0 if raw_pressure_fl is not None and not is_error_value(raw_pressure_fl) else None
    transformed["tire_pressure_fr"] = float(raw_pressure_fr) / 10.0 if raw_pressure_fr is not None and not is_error_value(raw_pressure_fr) else None
    transformed["tire_pressure_rl"] = float(raw_pressure_rl) / 10.0 if raw_pressure_rl is not None and not is_error_value(raw_pressure_rl) else None
    transformed["tire_pressure_rr"] = float(raw_pressure_rr) / 10.0 if raw_pressure_rr is not None and not is_error_value(raw_pressure_rr) else None
    
    # Tire temperatures (convert from integer representation, then to Celsius)
    # Note: Values may be stored in two formats:
    # - Direct format: 29 = 29°C (when value < 100, already in correct units)
    # - Scaled format: 840 = 84.0°F (when value >= 100, needs division by 10)
    raw_temp_fl = get_nested_value(instrument_device, "getWheelTemperature(int)", "1")
    raw_temp_fr = get_nested_value(instrument_device, "getWheelTemperature(int)", "2")
    raw_temp_rl = get_nested_value(instrument_device, "getWheelTemperature(int)", "3")
    raw_temp_rr = get_nested_value(instrument_device, "getWheelTemperature(int)", "4")
    
    # Convert from integer representation: divide by 10 if value >= 100, otherwise use as-is
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
    
    transformed["tire_temp_fl"] = convert_temperature_to_celsius(temp_fl, temp_unit)
    transformed["tire_temp_fr"] = convert_temperature_to_celsius(temp_fr, temp_unit)
    transformed["tire_temp_rl"] = convert_temperature_to_celsius(temp_rl, temp_unit)
    transformed["tire_temp_rr"] = convert_temperature_to_celsius(temp_rr, temp_unit)
    
    # PM2.5 air quality
    transformed["pm25_inside"] = clean_value(
        get_nested_value(pm25_device, "getPM2p5Value", 0) if isinstance(
            pm25_device.get("getPM2p5Value"), list
        ) else None
    )
    transformed["pm25_outside"] = clean_value(
        get_nested_value(pm25_device, "getPM2p5Value", 1) if isinstance(
            pm25_device.get("getPM2p5Value"), list
        ) else None
    )
    
    # Charging state (for drive/charging session detection)
    transformed["is_charging"] = to_boolean(charging_device.get("getChargingState"))
    transformed["charging_gun_connected"] = to_boolean(
        charging_device.get("getChargingGunState"), 
        true_values={2}  # 2 = connected, 1 = not connected
    )
    transformed["charger_power"] = convert_power_to_kw(
        charging_device.get("getChargingPower"),
        power_unit
    )
    transformed["charge_energy_added"] = None  # Cumulative, will be calculated
    
    # Handle PM2.5 array properly
    pm25_value = pm25_device.get("getPM2p5Value")
    if isinstance(pm25_value, list) and len(pm25_value) >= 2:
        transformed["pm25_inside"] = clean_value(pm25_value[0])
        transformed["pm25_outside"] = clean_value(pm25_value[1])
    
    return transformed

