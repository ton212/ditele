"""Transform raw telemetry data into structured format."""
from typing import Dict, Any

from telemetry.devices.location import transform_location
from telemetry.devices.speed import transform_speed
from telemetry.devices.statistic import transform_statistic
from telemetry.devices.gearbox import transform_gearbox
from telemetry.devices.instrument import transform_instrument
from telemetry.devices.ac import transform_ac
from telemetry.devices.charging import transform_charging
from telemetry.devices.pm25 import transform_pm25


def transform_telemetry_data(raw_data: Dict) -> Dict[str, Any]:
    """Transform raw telemetry data into structured format matching database schema.
    
    Args:
        raw_data: Raw telemetry data from the agent
    
    Returns:
        Dictionary with transformed data matching database model fields
    """
    devices = raw_data.get("devices", {})
    location_data = raw_data.get("location")
    
    # Transform each device
    location_result = transform_location(location_data)
    speed_result = transform_speed(devices.get("BYDAutoSpeedDevice", {}))
    statistic_result = transform_statistic(devices.get("BYDAutoStatisticDevice", {}))
    gearbox_result = transform_gearbox(devices.get("BYDAutoGearboxDevice", {}))
    instrument_result = transform_instrument(devices.get("BYDAutoInstrumentDevice", {}))
    
    # AC and charging need unit info from instrument device
    ac_result = transform_ac(
        devices.get("BYDAutoAcDevice", {}),
        instrument_result.get("temp_unit")
    )
    charging_result = transform_charging(
        devices.get("BYDAutoChargingDevice", {}),
        instrument_result.get("power_unit")
    )
    
    pm25_result = transform_pm25(devices.get("BYDAutoPM2p5Device", {}))
    
    # Combine all results
    transformed = {
        **location_result,
        **speed_result,
        **statistic_result,
        **gearbox_result,
        "outside_temp": instrument_result.get("outside_temp"),
        "inside_temp": instrument_result.get("inside_temp"),
        "power": None,  # Not directly available in sample, may need to calculate
        **ac_result,
        "tire_pressure_fl": instrument_result.get("tire_pressure_fl"),
        "tire_pressure_fr": instrument_result.get("tire_pressure_fr"),
        "tire_pressure_rl": instrument_result.get("tire_pressure_rl"),
        "tire_pressure_rr": instrument_result.get("tire_pressure_rr"),
        "tire_temp_fl": instrument_result.get("tire_temp_fl"),
        "tire_temp_fr": instrument_result.get("tire_temp_fr"),
        "tire_temp_rl": instrument_result.get("tire_temp_rl"),
        "tire_temp_rr": instrument_result.get("tire_temp_rr"),
        **pm25_result,
        **charging_result,
    }
    
    return transformed
